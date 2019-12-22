
import asyncio
import logging
import time

from qtoggleserver.conf import settings
from qtoggleserver.utils import json as json_utils


logger = logging.getLogger(__name__)
memory_logs = None

loop = asyncio.get_event_loop()

_update_loop_task = None
_running = True
_last_time = 0
_force_eval_expressions = False


async def update():
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

    for port in ports.all_ports():
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

        try:
            new_value = await port.read_transformed_value()

        except Exception as e:
            logger.error('failed to read value from %s: %s', port, e, exc_info=True)

            continue

        if new_value is None:
            continue  # read value not available

        if new_value != old_value:
            old_value_str = json_utils.dumps(old_value) if old_value is not None else '(unavailable)'
            new_value_str = json_utils.dumps(new_value)

            logger.debug('detected %s value change: %s -> %s', port, old_value_str, new_value_str)

            port._value = new_value
            changed_set.add(port)

            # remember and reset port change reason
            change_reasons[port] = port.get_change_reason()
            port.reset_change_reason()

    if changed_set:
        await handle_value_changes(changed_set, change_reasons)

    sessions.respond_non_empty()
    sessions.cleanup()


async def update_loop():
    while _running:
        try:
            await update()

        except Exception as e:
            logger.error('update failed: %s', e, exc_info=True)

        await asyncio.sleep(settings.core.tick_interval / 1000.0)


async def handle_value_changes(changed_set, change_reasons):
    global _force_eval_expressions

    from . import expressions
    from . import ports

    if _force_eval_expressions:
        changed_set.add(None)  # special "always depends on" value
        _force_eval_expressions = False

    # trigger value-change events; save persisted ports
    for port in changed_set:
        if not isinstance(port, ports.BasePort):
            continue

        port.trigger_value_change()

        if await port.is_persisted():
            await port.save()

    # reevaluate the expressions depending on changed ports
    for port in ports.all_ports():
        if not port.is_enabled():
            continue

        expression = await port.get_expression()
        if expression:
            deps = expression.get_deps()
            deps.add(None)  # special "always depends on" value

            # if port expression depends on port itself and the change reason is the evaluation of its expression,
            # prevent evaluating its expression again to avoid evaluation loops

            change_reason = change_reasons.get(port, ports.CHANGE_REASON_NATIVE)
            if ((port in changed_set) and
                (('${}'.format(port.get_id())) in deps) and
                (change_reason == ports.CHANGE_REASON_EXPRESSION)):
                continue

            changed_set_ids = set('${}'.format(c.get_id()) for c in changed_set if isinstance(c, ports.BasePort))

            # evaluate a port's expression when:
            # * one of its deps changed
            # * its own value changed

            # join all deps together; deps may contain:
            # * ports
            # * port ids
            # * time dep strings
            # * None
            if not (deps & (changed_set_ids | changed_set)) and (port not in changed_set):
                continue

            try:
                value = expression.eval()

            except expressions.IncompleteExpression:
                continue

            except Exception as e:
                logger.error('failed to evaluate expression "%s" of %s: %s', expression, port, e)
                continue

            value = await port.adapt_value_type(value)
            if value is None:
                continue

            if value != port.get_value():
                logger.debug('expression "%s" of %s evaluated to %s', expression, port, json_utils.dumps(value))
                port.push_value(value, reason=ports.CHANGE_REASON_EXPRESSION)


def force_eval_expressions():
    global _force_eval_expressions

    _force_eval_expressions = True


async def init():
    global _update_loop_task

    force_eval_expressions()
    _update_loop_task = loop.create_task(update_loop())


async def cleanup():
    global _running

    _running = False

    await _update_loop_task
