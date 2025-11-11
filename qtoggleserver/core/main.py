import asyncio
import logging
import time

from qtoggleserver.conf import settings
from qtoggleserver.core import ports as core_ports
from qtoggleserver.core.typing import NullablePortValue
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
_updating_enabled: bool = True
_start_time: float = time.time()
_last_time: int = 0
_force_eval_expression_ports: set[core_ports.BasePort] = set()
_force_eval_all_expressions: bool = False
_ports_with_read_error = timedset.TimedSet(_PORT_READ_ERROR_RETRY_INTERVAL)
_update_lock: asyncio.Lock | None = None


async def update() -> None:
    from . import ports, sessions

    global _last_time
    global _update_lock

    if not _updating_enabled:
        return

    if _update_lock is None:
        _update_lock = asyncio.Lock()

    async with _update_lock:
        changed_set: set[core_ports.BasePort | str] = {"asap"}
        value_pairs = {}

        now = time.time()
        now_int = int(now)
        second_changed = False
        if now_int != _last_time:
            _last_time = now_int
            second_changed = True
            changed_set.add("second")

        for port in ports.get_all():
            if not port.is_enabled():
                continue

            port.invalidate_attrs()
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
                new_value_str = json_utils.dumps(new_value)

                logger.debug("detected %s value change: %s -> %s", port, old_value_str, new_value_str)

                port.set_last_read_value(new_value)
                changed_set.add(port)
                value_pairs[port] = old_value, new_value

        await handle_value_changes(changed_set, value_pairs, now)

        sessions.update()


async def update_loop() -> None:
    while True:
        try:
            try:
                if _ready:
                    await update()
            except Exception as e:
                logger.error("update failed: %s", e, exc_info=True)
            await asyncio.sleep(settings.core.tick_interval / 1000.0)
        except asyncio.CancelledError:
            logger.debug("update task cancelled")
            break


async def handle_value_changes(
    changed_set: set[core_ports.BasePort | str],
    value_pairs: dict[core_ports.BasePort, tuple[NullablePortValue, NullablePortValue]],
    now: float,
) -> None:
    global _force_eval_all_expressions

    # changed_set contains:
    #  * ports
    #  * time strings

    # deps contain:
    #  * `$`-prefixed port ids
    #  * time strings

    forced_ports = set(_force_eval_expression_ports)
    _force_eval_expression_ports.clear()

    full_eval = _force_eval_all_expressions
    _force_eval_all_expressions = False

    now_ms = int(now * 1000)

    # Transform `changed_set` into a set of strings so that we can compare it with deps
    changed_set_str = set()

    # Trigger value-change events; save persisted ports; build changed_set_str
    for port in changed_set:
        if isinstance(port, core_ports.BasePort):
            changed_set_str.add(f"${port.get_id()}")
        else:
            changed_set_str.add(port)
            continue

        if not await port.is_internal():
            value_pair = value_pairs.get(port)
            if not value_pair:
                continue
            await port.trigger_value_change(*value_pair)

        if await port.is_persisted():
            port.save_asap()

    # Reevaluate the expressions depending on changed ports
    for port in core_ports.get_all():
        if not port.is_enabled():
            continue

        expression = port.get_expression()
        if not expression:
            continue

        if full_eval or (port in forced_ports):
            port.push_eval(now_ms)
            continue

        deps: set[str] = expression.get_deps()

        # Evaluate a port's expression only if one of its deps changed
        changed_deps = deps & changed_set_str
        if not changed_deps:
            continue

        if ("asap" in deps) and (len(changed_deps) == 1):
            # Skip asap evaling if explicitly paused
            if expression.is_asap_eval_paused(now_ms):
                continue

            # Don't flood port with evals
            if port.has_pending_eval():
                continue

        port.push_eval(now_ms)


def force_eval_expressions(port: core_ports.BasePort | None = None) -> None:
    global _force_eval_all_expressions

    logger.debug("forcing expression evaluation for %s", port or "all ports")

    if port:
        _force_eval_expression_ports.add(port)
    else:
        _force_eval_all_expressions = True


def enable_updating() -> None:
    global _updating_enabled

    if not _updating_enabled:
        logger.debug("enabling update mechanism")
        _updating_enabled = True


def disable_updating() -> None:
    global _updating_enabled

    if _updating_enabled:
        logger.debug("disabling update mechanism")
        _updating_enabled = False


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
        await _update_loop_task
