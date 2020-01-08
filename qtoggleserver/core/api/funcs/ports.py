
import asyncio

from typing import List

from qtoggleserver.conf import settings
from qtoggleserver.core import api as core_api
from qtoggleserver.core import main
from qtoggleserver.core import ports as core_ports
from qtoggleserver.core import vports as core_vports
from qtoggleserver.core.api import schema as core_api_schema
from qtoggleserver.core.typing import GenericJSONDict, Attributes, NullablePortValue, PortValue
from qtoggleserver.utils import json as json_utils


@core_api.api_call(core_api.ACCESS_LEVEL_VIEWONLY)
async def get_ports(request: core_api.APIRequest) -> List[Attributes]:
    return [await port.to_json() for port in sorted(core_ports.all_ports(), key=lambda p: p.get_id())]


@core_api.api_call(core_api.ACCESS_LEVEL_ADMIN)
async def patch_port(request: core_api.APIRequest, port_id: str, params: Attributes) -> None:
    port = core_ports.get(port_id)
    if port is None:
        raise core_api.APIError(404, 'no such port')

    def unexpected_field_msg(field):
        if field in port.get_non_modifiable_attrs():
            return 'attribute not modifiable: {field}'

        else:
            return 'no such attribute: {field}'

    core_api_schema.validate(params, await port.get_schema(), unexpected_field_msg=unexpected_field_msg)

    # step validation
    for name, value in params.items():
        attrdef = port.ATTRDEFS[name]
        step = attrdef.get('step')
        _min = attrdef.get('min')
        if None not in (step, _min) and step != 0 and (value - _min) % step:
            raise core_api.APIError(400, f'invalid field: {name}')

    errors_by_name = {}

    async def set_attr(attr_name, attr_value):
        core_api.logger.debug('setting attribute %s = %s on %s', attr_name, json_utils.dumps(attr_value), port)

        try:
            await port.set_attr(attr_name, attr_value)

        except Exception as e:
            errors_by_name[attr_name] = e

    if params:
        await asyncio.wait([set_attr(name, value) for name, value in params.items()])

    if errors_by_name:
        name, error = next(iter(errors_by_name.items()))

        if isinstance(error, core_api.APIError):
            raise error

        elif isinstance(error, core_ports.InvalidAttributeValue):
            raise core_api.APIError(400, f'invalid field: {name}')

        elif isinstance(error, core_ports.PortTimeout):
            raise core_api.APIError(504, 'port timeout')

        elif isinstance(error, core_ports.PortError):
            raise core_api.APIError(502, f'port error: {error}')

        else:
            # transform any unhandled exception into APIError(500)
            raise core_api.APIError(500, str(error))

    await port.save()


@core_api.api_call(core_api.ACCESS_LEVEL_ADMIN)
async def post_ports(request: core_api.APIRequest, params: GenericJSONDict) -> Attributes:
    core_api_schema.validate(params, core_api_schema.POST_PORTS)

    port_id = params['id']
    port_type = params['type']
    mi = params.get('min')
    ma = params.get('max')
    integer = params.get('integer')
    step = params.get('step')
    choices = params.get('choices')

    if core_ports.get(port_id):
        raise core_api.APIError(400, 'duplicate port')

    if len(core_vports.all_settings()) >= settings.core.virtual_ports:
        raise core_api.APIError(400, 'too many ports')

    core_vports.add(port_id, port_type, mi, ma, integer, step, choices)
    port = await core_ports.load_one('qtoggleserver.core.vports.VirtualPort',
                                     {'port_id': port_id, '_type': port_type, '_min': min, '_max': max,
                                      'integer': integer, 'step': step, 'choices': choices})

    # A virtual port is enabled by default
    await port.enable()
    await port.save()

    return await port.to_json()


@core_api.api_call(core_api.ACCESS_LEVEL_ADMIN)
async def delete_port(request: core_api.APIRequest, port_id: str) -> None:
    port = core_ports.get(port_id)
    if not port:
        raise core_api.APIError(404, 'no such port')

    if not isinstance(port, core_vports.VirtualPort):
        raise core_api.APIError(400, 'port not removable')

    await port.remove()
    core_vports.remove(port_id)


@core_api.api_call(core_api.ACCESS_LEVEL_VIEWONLY)
async def get_port_value(request: core_api.APIRequest, port_id: str) -> NullablePortValue:
    port = core_ports.get(port_id)
    if port is None:
        raise core_api.APIError(404, 'no such port')

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
        raise core_api.APIError(404, 'no such port')

    core_api_schema.validate(params, await port.get_value_schema(), invalid_request_msg='invalid value')

    value = params

    # step validation
    step = await port.get_attr('step')
    _min = await port.get_attr('min')
    if None not in (step, _min) and step != 0 and (value - _min) % step:
        raise core_api.APIError(400, 'invalid field: value')

    if not port.is_enabled():
        raise core_api.APIError(400, 'port disabled')

    if not await port.is_writable():
        raise core_api.APIError(400, 'read-only port')

    try:
        await port.set_value(value, reason=core_ports.CHANGE_REASON_API)

    except core_ports.PortTimeout as e:
        raise core_api.APIError(504, 'port timeout') from e

    except core_ports.PortError as e:
        raise core_api.APIError(502, f'port error: {e}') from e

    except core_api.APIError:
        raise

    except Exception as e:
        # Transform any unhandled exception into APIError(500)
        raise core_api.APIError(500, str(e)) from e

    await main.update()


@core_api.api_call(core_api.ACCESS_LEVEL_NORMAL)
async def post_port_sequence(request: core_api.APIRequest, port_id: str, params: GenericJSONDict) -> None:
    port = core_ports.get(port_id)
    if port is None:
        raise core_api.APIError(404, 'no such port')

    core_api_schema.validate(params, core_api_schema.POST_PORT_SEQUENCE)

    values = params['values']
    delays = params['delays']
    repeat = params['repeat']

    if len(values) != len(delays):
        raise core_api.APIError(400, 'invalid field: delays')

    value_schema = await port.get_value_schema()
    step = await port.get_attr('step')
    _min = await port.get_attr('min')
    for value in values:
        core_api_schema.validate(value, value_schema, invalid_request_msg='invalid field: values')

        # Step validation
        if None not in (step, _min) and step != 0 and (value - _min) % step:
            raise core_api.APIError(400, 'invalid field: values')

    if not port.is_enabled():
        raise core_api.APIError(400, 'port disabled')

    if not await port.is_writable():
        raise core_api.APIError(400, 'read-only port')

    if await port.get_attr('expression'):
        raise core_api.APIError(400, 'port with expression')

    try:
        await port.set_sequence(values, delays, repeat)

    except Exception as e:
        # Transform any unhandled exception into APIError(500)
        raise core_api.APIError(500, str(e)) from e
