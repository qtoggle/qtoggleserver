
import asyncio
import logging
import time

from typing import Dict, Optional, Set, Tuple, Union

from qtoggleserver.conf import settings
from qtoggleserver.core import expressions as core_expressions  # noqa: F401; Required to avoid circular imports
from qtoggleserver.core import ports as core_ports
from qtoggleserver.core.typing import NullablePortValue
from qtoggleserver.utils import json as json_utils
from qtoggleserver.utils import timedset
from qtoggleserver.utils import logging as logging_utils


# After how much time to retry reading a port whose read_value() method raised an error
_PORT_READ_ERROR_RETRY_INTERVAL = 10

logger = logging.getLogger(__name__)
memory_logs: Optional[logging_utils.FifoMemoryHandler] = None

loop: Optional[asyncio.AbstractEventLoop] = None

_update_loop_task: Optional[asyncio.Task] = None
_ready: bool = False
_updating_enabled: bool = True
_start_time: float = time.time()
_last_time: float = 0
_force_eval_expression_ports: Set[Union[core_ports.BasePort, None]] = set()
_ports_with_read_error = timedset.TimedSet(_PORT_READ_ERROR_RETRY_INTERVAL)
_update_lock: Optional[asyncio.Lock] = None


async def update() -> None:
    from . import ports
    from . import sessions

    global _last_time
    global _update_lock

    if not _updating_enabled:
        return

    if _update_lock is None:
        _update_lock = asyncio.Lock()

    async with _update_lock:
        changed_set = {'millisecond'}
        change_reasons = {}
        value_pairs = {}

        now = int(time.time())
        time_changed = False
        if now != _last_time:
            _last_time = now
            time_changed = True
            changed_set.add('second')

        for port in ports.get_all():
            if not port.is_enabled():
                continue

            port.invalidate_attrs()
            old_value = port.get_last_read_value()

            if time_changed:
                try:
                    port.heart_beat_second()

                except Exception as e:
                    logger.error('port heart beat second exception: %s', e, exc_info=True)

            # Skip ports with read errors for a while
            if port in _ports_with_read_error:
                continue

            try:
                new_value = await port.read_transformed_value()

            except Exception as e:
                logger.error('failed to read value from %s: %s', port, e, exc_info=True)
                _ports_with_read_error.add(port)

                continue

            if new_value is None:
                continue  # Read value not available

            if new_value != old_value:
                old_value_str = json_utils.dumps(old_value) if old_value is not None else '(unavailable)'
                new_value_str = json_utils.dumps(new_value)

                logger.debug('detected %s value change: %s -> %s', port, old_value_str, new_value_str)

                port.set_last_read_value(new_value)
                changed_set.add(port)
                value_pairs[port] = old_value, new_value

                # Remember and reset port change reason
                change_reasons[port] = port.get_change_reason()
                port.reset_change_reason()

        await handle_value_changes(changed_set, change_reasons, value_pairs)

        sessions.update()


async def update_loop() -> None:
    while True:
        try:
            try:
                if _ready:
                    await update()

            except Exception as e:
                logger.error('update failed: %s', e, exc_info=True)

            await asyncio.sleep(settings.core.tick_interval / 1000.0)

        except asyncio.CancelledError:
            logger.debug('update loop cancelled')
            break


async def handle_value_changes(
    changed_set: Set[Union[core_ports.BasePort, None]],
    change_reasons: Dict[core_ports.BasePort, str],
    value_pairs: Dict[core_ports.BasePort, Tuple[NullablePortValue, NullablePortValue]],
) -> None:

    forced_deps = set()
    if _force_eval_expression_ports:
        changed_set.update(_force_eval_expression_ports)
        forced_deps.update(_force_eval_expression_ports)
        _force_eval_expression_ports.clear()

    # Trigger value-change events; save persisted ports
    for port in changed_set:
        if not isinstance(port, core_ports.BasePort):
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

        deps = set(expression.get_deps()) | forced_deps
        deps.add(None)  # Special "always depends on" value

        changed_set_ids = set(f'${c.get_id()}' for c in changed_set if isinstance(c, core_ports.BasePort))

        # Evaluate a port's expression if one of its deps changed

        # Join all deps together; deps may contain:
        # * ports
        # * port ids
        # * time dep strings
        # * None
        all_changed_set = changed_set_ids | changed_set
        if not bool(deps & all_changed_set):
            continue

        # If port expression depends on port itself and the change reason is the evaluation of its expression, prevent
        # evaluating its expression again to avoid evaluation loops
        change_reason = change_reasons.get(port, core_ports.CHANGE_REASON_NATIVE)
        if ((port in changed_set) and
            (f'${port.get_id()}' in deps) and
            (change_reason == core_ports.CHANGE_REASON_EXPRESSION)):

            logger.debug('skipping evaluation of %s expression to prevent loops', port)
            continue

        port.push_eval()


def force_eval_expressions(port: core_ports.BasePort = None) -> None:
    logger.debug('forcing expression evaluation for %s', port or 'all ports')

    _force_eval_expression_ports.add(port)
    if port:
        port.reset_change_reason()


def enable_updating() -> None:
    global _updating_enabled

    if not _updating_enabled:
        logger.debug('enabling update mechanism')
        _updating_enabled = True


def disable_updating() -> None:
    global _updating_enabled

    if _updating_enabled:
        logger.debug('disabling update mechanism')
        _updating_enabled = False


def is_ready() -> bool:
    return _ready


def set_ready() -> None:
    global _ready

    logger.debug('ready')
    _ready = True


def uptime() -> float:
    return time.time() - _start_time


async def init() -> None:
    global _update_loop_task
    global loop

    loop = asyncio.get_event_loop()

    force_eval_expressions()
    _update_loop_task = loop.create_task(update_loop())


async def cleanup() -> None:
    if _update_loop_task:
        _update_loop_task.cancel()
        await _update_loop_task
