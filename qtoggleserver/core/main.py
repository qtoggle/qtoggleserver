import asyncio
import logging
import time

from datetime import datetime

from qtoggleserver.conf import settings
from qtoggleserver.core import ports as core_ports
from qtoggleserver.core.expressions import (
    DEP_ASAP,
    DEP_DAY,
    DEP_HOUR,
    DEP_MINUTE,
    DEP_MONTH,
    DEP_SECOND,
    DEP_YEAR,
    EvalContext,
)
from qtoggleserver.core.typing import NullablePortValue
from qtoggleserver.utils import expressions as expressions_utils
from qtoggleserver.utils import json as json_utils
from qtoggleserver.utils import logging as logging_utils
from qtoggleserver.utils import timedset


# After how much time to retry reading a port whose read_value() method raised an error
_PORT_READ_ERROR_RETRY_INTERVAL = 10

logger = logging.getLogger(__name__)
memory_logs: logging_utils.FifoMemoryHandler | None = None

loop: asyncio.AbstractEventLoop | None = None

_update_loop_task: asyncio.Task | None = None
_ready: bool = False
_paused: bool = False
_start_time: float = time.time()
_last_time: int = 0
_last_minute: int = 0
_last_hour: int = 0
_last_day: int = 0
_last_week: int = 0
_last_month: int = 0
_last_year: int = 0
_force_eval_expression_ports: set[core_ports.BasePort] = set()
_force_eval_all_expressions: bool = False
_ports_with_read_error = timedset.TimedSet(_PORT_READ_ERROR_RETRY_INTERVAL)
_update_lock: asyncio.Lock | None = None


def _get_changed_time_deps(now_int: int) -> tuple[bool, set[str]]:
    """Determine which time-unit deps have changed since the last call and update the relevant module-level tracking
    variables. Returns ``(second_changed, changed_time_deps)``."""

    global _last_time
    global _last_minute
    global _last_hour
    global _last_day
    global _last_week
    global _last_month
    global _last_year

    changed_time_deps: set[str] = {DEP_ASAP}
    second_changed = False

    if now_int != _last_time:
        _last_time = now_int
        second_changed = True
        changed_time_deps.add(DEP_SECOND)

        now_minute = now_int // 60
        if now_minute != _last_minute:
            _last_minute = now_minute
            changed_time_deps.add(DEP_MINUTE)

            now_hour = now_minute // 60
            if now_hour != _last_hour:
                _last_hour = now_hour
                changed_time_deps.add(DEP_HOUR)

                now_dt = datetime.fromtimestamp(now_int)
                if now_dt.day != _last_day:
                    _last_day = now_dt.day
                    changed_time_deps.add(DEP_DAY)

                    if now_dt.month != _last_month:
                        _last_month = now_dt.month
                        changed_time_deps.add(DEP_MONTH)

                        if now_dt.year != _last_year:
                            _last_year = now_dt.year
                            changed_time_deps.add(DEP_YEAR)

    return second_changed, changed_time_deps


async def read_ports(ports_to_read: list[core_ports.BasePort] | None = None) -> None:
    from . import sessions

    global _update_lock

    if _paused:
        return

    if _update_lock is None:
        _update_lock = asyncio.Lock()

    async with _update_lock:
        port_changed_values: dict[core_ports.BasePort, tuple[NullablePortValue, NullablePortValue]] = {}

        now = time.time()
        now_int = int(now)
        now_ms = int(now * 1000)

        if not ports_to_read:
            second_changed, changes = _get_changed_time_deps(now_int)
        else:
            # When `ports_to_read` are given, this call is made from outside of the main update loop. Don't touch
            # time-related deps unless called from main update loop.
            second_changed = False
            changes = {DEP_ASAP}

        all_ports = list(core_ports.get_all())
        if not ports_to_read:
            ports_to_read = all_ports

        for port in ports_to_read:
            if not port.is_enabled():
                continue

            old_value = port.get_last_read_value()

            if second_changed:
                try:
                    port.heart_beat_second()
                except Exception as e:
                    logger.error("port heart beat second exception: %s", e, exc_info=True)

            # Skip ports with read errors for a while
            if port in _ports_with_read_error:
                continue

            try:
                new_value = await port.read_transformed_value()
            except core_ports.SkipRead:
                continue  # read explicitly skipped
            except Exception as e:
                logger.error("failed to read value from %s: %s", port, e, exc_info=True)
                _ports_with_read_error.add(port)

                continue

            if new_value != old_value:
                old_value_str = json_utils.dumps(old_value) if old_value is not None else "(unavailable)"
                new_value_str = json_utils.dumps(new_value) if new_value is not None else "(unavailable)"

                logger.debug("detected %s value change: %s -> %s", port, old_value_str, new_value_str)

                port.set_last_read_value(new_value)
                port_changed_values[port] = old_value, new_value

        # Trigger value-change events; save persisted ports; add port deps to changes
        for port, (old_value, new_value) in port_changed_values.items():
            changes.add(f"${port.get_id()}")

            if not await port.is_internal():
                await port.trigger_value_change(old_value, new_value)

            if await port.is_persisted():
                port.save_asap()

        await _eval_changed_expressions(changes, now_ms)

        sessions.update()


async def _eval_changed_expressions(changed_set_str: set[str], now_ms: int) -> None:
    global _force_eval_all_expressions

    forced_ports = set(_force_eval_expression_ports)
    _force_eval_expression_ports.clear()

    full_eval = _force_eval_all_expressions
    _force_eval_all_expressions = False

    eval_context: EvalContext | None = None

    # Reevaluate all port expressions depending on changed set
    if full_eval:
        ports_to_eval = list(core_ports.get_all())
    else:
        deps_map = expressions_utils.get_deps_map()
        ports_to_eval: set[core_ports.BasePort] = set(forced_ports)
        for dep in changed_set_str:
            for port in deps_map.get(dep, []):
                ports_to_eval.add(port)

    for port in ports_to_eval:
        if not port.is_enabled():
            continue

        expression = port.get_expression()
        if not expression:
            continue

        if not full_eval and port not in forced_ports:
            deps: set[str] = expression.get_deps()
            changed_deps = deps & changed_set_str
            if changed_deps == {DEP_ASAP} and expression.is_asap_eval_paused(now_ms):
                continue

        # Build context lazily so we skip it entirely when all ports are filtered out above
        if not eval_context:
            eval_context = await expressions_utils.build_context(now_ms)

        await port.eval_and_push_write(eval_context)


async def update_loop() -> None:
    while True:
        try:
            try:
                if _ready:
                    await read_ports()
            except Exception as e:
                logger.error("update failed: %s", e, exc_info=True)
            await asyncio.sleep(settings.core.tick_interval / 1000.0)
        except asyncio.CancelledError:
            logger.debug("update task cancelled")
            break


def force_eval_expressions(port: core_ports.BasePort | None = None) -> None:
    global _force_eval_all_expressions

    logger.debug("forcing expression evaluation for %s", port or "all ports")

    if port:
        _force_eval_expression_ports.add(port)
    else:
        _force_eval_all_expressions = True


def resume() -> None:
    global _paused

    if _paused:
        logger.debug("resuming ports reading loop")
        _paused = False


def pause() -> None:
    global _paused

    if not _paused:
        logger.debug("pausing ports reading loop")
        _paused = True


def is_ready() -> bool:
    return _ready


def set_ready() -> None:
    global _ready

    logger.debug("ready")
    _ready = True


def uptime() -> float:
    return time.time() - _start_time


async def init() -> None:
    global _update_loop_task
    global loop

    loop = asyncio.get_running_loop()

    force_eval_expressions()
    _update_loop_task = loop.create_task(update_loop())


async def cleanup() -> None:
    if _update_loop_task:
        _update_loop_task.cancel()
        try:
            await _update_loop_task
        except asyncio.CancelledError:
            pass
