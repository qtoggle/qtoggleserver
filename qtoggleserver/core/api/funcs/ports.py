
import asyncio
import inspect

from typing import Any, Callable, List

from qtoggleserver import slaves
from qtoggleserver.conf import settings
from qtoggleserver.core import api as core_api
from qtoggleserver.core import events as core_events
from qtoggleserver.core import ports as core_ports
from qtoggleserver.core import vports as core_vports
from qtoggleserver.core.api import schema as core_api_schema
from qtoggleserver.core.typing import Attribute, Attributes, GenericJSONDict, GenericJSONList, NullablePortValue
from qtoggleserver.core.typing import PortValue
from qtoggleserver.slaves import ports as slaves_ports
from qtoggleserver.utils import json as json_utils


async def add_virtual_port(attrs: GenericJSONDict) -> core_ports.BasePort:
    id_ = attrs['id']
    type_ = attrs['type']
    min_ = attrs.get('min')
    max_ = attrs.get('max')
    integer = attrs.get('integer')
    step = attrs.get('step')
    choices = attrs.get('choices')

    core_api.logger.debug('adding port "%s"', id_)

    if core_ports.get(id_):
        raise core_api.APIError(400, 'duplicate-port')

    if len(core_vports.all_port_args()) >= settings.core.virtual_ports:
        raise core_api.APIError(400, 'too-many-ports')

    core_vports.add(id_, type_, min_, max_, integer, step, choices)
    port = await core_ports.load_one(
        'qtoggleserver.core.vports.VirtualPort',
        {
            'id_': id_,
            'type_': type_,
            'min_': min_,
            'max_': max_,
            'integer': integer,
            'step': step,
            'choices': choices
        }
    )

    # A virtual port is enabled by default
    await port.enable()
    await port.save()

    return port


async def set_port_attrs(port: core_ports.BasePort, attrs: GenericJSONDict, ignore_extra_attrs: bool) -> None:
    non_modifiable_attrs = await port.get_non_modifiable_attrs()

    def unexpected_field_code(field: str) -> str:
        if field in non_modifiable_attrs:
            return 'attribute-not-modifiable'

        else:
            return 'no-such-attribute'

    schema = await port.get_schema()
    if ignore_extra_attrs:
        schema = dict(schema)
        schema['additionalProperties'] = True  # Ignore non-existent and non-modifiable attributes

    core_api_schema.validate(
        attrs,
        schema,
        unexpected_field_code=unexpected_field_code,
        unexpected_field_name='attribute'
    )

    # Step validation
    attrdefs = await port.get_attrdefs()
    for name, value in attrs.items():
        attrdef = attrdefs.get(name)
        if attrdef is None:
            continue

        step = attrdef.get('step')
        min_ = attrdef.get('min')
        if None not in (step, min_) and step != 0 and (value - min_) % step:
            raise core_api.APIError(400, 'invalid-field', field=name)

    errors_by_name = {}

    async def set_attr(attr_name: str, attr_value: Attribute) -> None:
        core_api.logger.debug('setting attribute %s = %s on %s', attr_name, json_utils.dumps(attr_value), port)

        try:
            await port.set_attr(attr_name, attr_value)

        except Exception as e:
            errors_by_name[attr_name] = e

    if attrs:
        await asyncio.wait([set_attr(name, value) for name, value in attrs.items()])

    if errors_by_name:
        name, error = next(iter(errors_by_name.items()))

        if isinstance(error, core_api.APIError):
            raise error

        elif isinstance(error, core_ports.InvalidAttributeValue):
            raise core_api.APIError(400, 'invalid-field', field=name, details=error.details)

        elif isinstance(error, core_ports.PortTimeout):
            raise core_api.APIError(504, 'port-timeout')

        elif isinstance(error, core_ports.PortError):
            raise core_api.APIError(502, 'port-error', code=str(error))

        else:
            # Transform any unhandled exception into APIError(500)
            raise core_api.APIError(500, 'unexpected-error', message=str(error)) from error

    # If value is supplied among attrs, use it to update port value, but ignore any errors;
    value = attrs.get('value')
    if value is not None and port.is_enabled():
        try:
            await port.write_transformed_value(value, reason=core_ports.CHANGE_REASON_API)

        except Exception as e:
            core_api.logger.error('failed to set %s value: %s', port, e, exc_info=True)

    await port.save()


async def wrap_error_with_port_id(port_id: str, func: Callable, *args, **kwargs) -> Any:
    try:
        result = func(*args, **kwargs)
        if inspect.isawaitable(result):
            result = await result

    except core_api.APIError as e:
        raise core_api.APIError(
            status=e.status,
            code=e.code,
            id=port_id,
            **e.params
        )

    except Exception as e:
        raise core_api.APIError(
            status=500,
            code='unexpected-error',
            message=str(e),
            id=port_id
        )

    return result


@core_api.api_call(core_api.ACCESS_LEVEL_VIEWONLY)
async def get_ports(request: core_api.APIRequest) -> List[Attributes]:
    return [await port.to_json() for port in sorted(core_ports.get_all(), key=lambda p: p.get_id())]


@core_api.api_call(core_api.ACCESS_LEVEL_ADMIN)
async def put_ports(request: core_api.APIRequest, params: GenericJSONList) -> None:
    if not settings.core.backup_support:
        raise core_api.APIError(404, 'no-such-function')

    core_api_schema.validate(
        params,
        core_api_schema.PUT_PORTS
    )

    core_api.logger.debug('restoring ports')

    # Disable event handling during the processing of this request, as we're going to trigger a full-update at the end
    core_events.disable()

    try:
        # Remove all (local) virtual ports
        for port in list(core_ports.get_all()):
            if not isinstance(port, core_vports.VirtualPort):
                continue

            await port.remove()
            core_vports.remove(port.get_id())

        # Reset ports
        core_ports.reset()
        if settings.slaves.enabled:
            slaves.reset_ports()
        for port in core_ports.get_all():
            await port.reset()

        add_port_schema = dict(core_api_schema.POST_PORTS)
        add_port_schema['additionalProperties'] = True

        # Restore supplied attributes
        for attrs in params:
            id_ = attrs.get('id')
            if id_ is None:
                core_api.logger.warning('ignoring entry without id')
                continue

            port = core_ports.get(id_)

            # Virtual ports must be added first (unless they belong to a slave)
            virtual = attrs.get('virtual')
            if virtual and port is None:
                await wrap_error_with_port_id(
                    id_,
                    core_api_schema.validate,
                    attrs,
                    add_port_schema
                )
                port = await wrap_error_with_port_id(
                    id_,
                    add_virtual_port,
                    attrs
                )

            if port is None:
                core_api.logger.warning('ignoring unknown port id "%s"', id_)
                continue

            if isinstance(port, slaves_ports.SlavePort):
                core_api.logger.debug('restoring slave port "%s"', id_)

                # For slave ports, ignore any attributes that are not kept on master
                attrs = {n: v for n, v in attrs.items() if n in ('tag', 'expression', 'expires')}

            else:
                core_api.logger.debug('restoring local port "%s"', id_)

            await wrap_error_with_port_id(
                id_,
                set_port_attrs,
                port,
                attrs,
                ignore_extra_attrs=True
            )

    finally:
        core_events.enable()

    await core_events.trigger_full_update()

    core_api.logger.debug('ports restore done')


@core_api.api_call(core_api.ACCESS_LEVEL_ADMIN)
async def patch_port(request: core_api.APIRequest, port_id: str, params: Attributes) -> None:
    port = core_ports.get(port_id)
    if port is None:
        raise core_api.APIError(404, 'no-such-port')

    await set_port_attrs(port, params, ignore_extra_attrs=False)


@core_api.api_call(core_api.ACCESS_LEVEL_ADMIN)
async def post_ports(request: core_api.APIRequest, params: GenericJSONDict) -> Attributes:
    core_api_schema.validate(params, core_api_schema.POST_PORTS)
    port = await add_virtual_port(params)

    return await port.to_json()


@core_api.api_call(core_api.ACCESS_LEVEL_ADMIN)
async def delete_port(request: core_api.APIRequest, port_id: str) -> None:
    port = core_ports.get(port_id)
    if not port:
        raise core_api.APIError(404, 'no-such-port')

    if not isinstance(port, core_vports.VirtualPort):
        raise core_api.APIError(400, 'port-not-removable')

    await port.remove()
    core_vports.remove(port_id)


@core_api.api_call(core_api.ACCESS_LEVEL_VIEWONLY)
async def get_port_value(request: core_api.APIRequest, port_id: str) -> NullablePortValue:
    port = core_ports.get(port_id)
    if port is None:
        raise core_api.APIError(404, 'no-such-port')

    if not port.is_enabled():
        return

    # TODO
    # Given the fact that get_value() simply returns last cached read value, and the fact that API specs indicate that
    # 502/504 be returned by GET /port/[id]/value in case of errors, we should remember the last error generated by
    # read_value() and return it here, if any.

    return port.get_value()


@core_api.api_call(core_api.ACCESS_LEVEL_NORMAL)
async def patch_port_value(request: core_api.APIRequest, port_id: str, params: PortValue) -> None:
    port = core_ports.get(port_id)
    if port is None:
        raise core_api.APIError(404, 'no-such-port')

    try:
        core_api_schema.validate(params, await port.get_value_schema())

    except core_api.APIError:
        # Transform any validation error into an invalid-field APIError for value
        raise core_api.APIError(400, 'invalid-value') from None

    value = params

    # Step validation
    step = await port.get_attr('step')
    min_ = await port.get_attr('min')
    if None not in (step, min_) and step != 0 and (value - min_) % step:
        raise core_api.APIError(400, 'invalid-value')

    if not port.is_enabled():
        raise core_api.APIError(400, 'port-disabled')

    if not await port.is_writable():
        raise core_api.APIError(400, 'read-only-port')

    old_value = port.get_value()

    try:
        await port.write_transformed_value(value, reason=core_ports.CHANGE_REASON_API)

    except core_ports.PortTimeout as e:
        raise core_api.APIError(504, 'port-timeout') from e

    except core_ports.PortError as e:
        raise core_api.APIError(502, 'port-error', code=str(e)) from e

    except core_api.APIError:
        raise

    except Exception as e:
        # Transform any unhandled exception into APIError(500)
        raise core_api.APIError(500, 'unexpected-error', message=str(e)) from e

    # If port value hasn't really changed, trigger a value-change to inform consumer that new value has been ignored
    current_value = port.get_value()
    if (old_value == current_value) and (old_value != value):
        port.debug('API supplied value was ignored')
        await port.trigger_value_change()


@core_api.api_call(core_api.ACCESS_LEVEL_NORMAL)
async def patch_port_sequence(request: core_api.APIRequest, port_id: str, params: GenericJSONDict) -> None:
    port = core_ports.get(port_id)
    if port is None:
        raise core_api.APIError(404, 'no-such-port')

    core_api_schema.validate(params, core_api_schema.PATCH_PORT_SEQUENCE)

    values = params['values']
    delays = params['delays']
    repeat = params['repeat']

    if len(values) != len(delays):
        raise core_api.APIError(400, 'invalid-field', field='delays')

    value_schema = await port.get_value_schema()
    step = await port.get_attr('step')
    min_ = await port.get_attr('min')
    for value in values:
        # Translate any APIError generated when validating value schema into an invalid-field APIError on value
        try:
            core_api_schema.validate(value, value_schema)

        except core_api.APIError:
            raise core_api.APIError(400, 'invalid-field', field='values') from None

        # Step validation
        if None not in (step, min_) and step != 0 and (value - min_) % step:
            raise core_api.APIError(400, 'invalid-field', field='values')

    if not port.is_enabled():
        raise core_api.APIError(400, 'port-disabled')

    if not await port.is_writable():
        raise core_api.APIError(400, 'read-only-port')

    if await port.get_attr('expression'):
        raise core_api.APIError(400, 'port-with-expression')

    try:
        await port.set_sequence(values, delays, repeat)

    except Exception as e:
        # Transform any unhandled exception into APIError(500)
        raise core_api.APIError(500, 'unexpected-error', message=str(e)) from e
