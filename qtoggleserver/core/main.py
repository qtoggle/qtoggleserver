
import asyncio
import logging
import time

from typing import Dict, Optional, Set, Union

from qtoggleserver.conf import settings
from qtoggleserver.core import expressions as core_expressions
from qtoggleserver.core import ports as core_ports
from qtoggleserver.utils import json as json_utils
from qtoggleserver.utils import timedset
from qtoggleserver.utils import logging as logging_utils


# After how much time to retry reading a port whose read_value() method raised an error
_PORT_READ_ERROR_RETRY_INTERVAL = 10

logger = logging.getLogger(__name__)
memory_logs: Optional[logging_utils.FifoMemoryHandler] = None

loop = asyncio.get_event_loop()

_update_loop_task = None
_running = True
_ready = False
_start_time = time.time()
_last_time = 0
_force_eval_expression_ports: Set[Union[core_ports.BasePort, None]] = set()
_ports_with_read_error = timedset.TimedSet(_PORT_READ_ERROR_RETRY_INTERVAL)


async def update() -> None:
    from . import ports
    from . import sessions

    global _last_time

    changed_set = set()
    change_reasons = {}

    now = int(time.time())
    time_changed = False
    if now != _last_time:
        _last_time = now
        time_changed = True
        changed_set.add('time')

    changed_set.add('time_ms')

    for port in list(ports.all_ports()):
        if not port.is_enabled():
            continue

        port.invalidate_attrs()
        old_value = port.get_value()

        try:
            port.heart_beat()

        except Exception as e:
            logger.error('port heart beat exception: %s', e, exc_info=True)

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

            port.set_value(new_value)
            changed_set.add(port)

            # Remember and reset port change reason
            change_reasons[port] = port.get_change_reason()
            port.reset_change_reason()

    if changed_set:
        await handle_value_changes(changed_set, change_reasons)

    sessions.update()


async def update_loop() -> None:
    while _running:
        try:
            await update()

        except Exception as e:
            logger.error('update failed: %s', e, exc_info=True)

        await asyncio.sleep(settings.core.tick_interval / 1000.0)


async def handle_value_changes(
    changed_set: Set[Union[core_ports.BasePort, None]],
    change_reasons: Dict[core_ports.BasePort, str]
) -> None:

    if _force_eval_expression_ports:
        changed_set.update(_force_eval_expression_ports)  # Special "always depends on" value
        _force_eval_expression_ports.clear()

    # Trigger value-change events; save persisted ports
    for port in changed_set:
        if not isinstance(port, core_ports.BasePort):
            continue

        if not await port.is_internal():
            await port.trigger_value_change()

        if await port.is_persisted():
            await port.save()

    # Reevaluate the expressions depending on changed ports
    for port in core_ports.all_ports():
        if not port.is_enabled():
            continue

        if not await port.is_writable():
            continue

        # Leave the port alone while it has pending writes; expression changes could only push more values to its queue
        if port.has_pending_write():
            continue

        expression = await port.get_expression()
        if not expression:
            continue

        deps = set(expression.get_deps())
        deps.add(None)  # Special "always depends on" value

        changed_set_ids = set(f'${c.get_id()}' for c in changed_set if isinstance(c, core_ports.BasePort))

        # Evaluate a port's expression when:
        # * one of its deps changed
        # * its own value changed

        # Join all deps together; deps may contain:
        # * ports
        # * port ids
        # * time dep strings
        # * None
        if not (deps & (changed_set_ids | changed_set)) and (port not in changed_set):
            continue

        # If port expression depends on port itself and the change reason is the evaluation of its expression, prevent
        # evaluating its expression again to avoid evaluation loops
        change_reason = change_reasons.get(port, core_ports.CHANGE_REASON_NATIVE)
        if ((port in changed_set) and
            (f'${port.get_id()}' in deps) and
            (change_reason == core_ports.CHANGE_REASON_EXPRESSION)):

            logger.debug('skipping evaluation of %s expression to prevent loops', port)
            continue

        try:
            value = expression.eval()

        except core_expressions.ExpressionEvalError:
            continue

        except Exception as e:
            logger.error('failed to evaluate expression "%s" of %s: %s', expression, port, e)
            continue

        value = await port.adapt_value_type(value)
        if value is None:
            continue

        logger.debug('expression "%s" of %s evaluated to %s', expression, port, json_utils.dumps(value))
        if value != port.get_value():
            port.push_value(value, reason=core_ports.CHANGE_REASON_EXPRESSION)

        else:
            logger.debug('%s value unchanged after expression evaluation', port)


def force_eval_expressions(port: core_ports.BasePort = None) -> None:
    logger.debug('forcing expression evaluation for %s', port or 'all ports')

    _force_eval_expression_ports.add(port)
    if port:
        port.reset_change_reason()


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

    force_eval_expressions()
    _update_loop_task = loop.create_task(update_loop())


async def cleanup() -> None:
    global _running

    _running = False

    await _update_loop_task
