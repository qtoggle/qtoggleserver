
from qtoggleserver import system
from qtoggleserver.core import api as core_api
from qtoggleserver.core import device as core_device
from qtoggleserver.core import main
from qtoggleserver.core.api import schema as core_api_schema
from qtoggleserver.core.device import attrs as core_device_attrs
from qtoggleserver.core.device import events as core_device_events


@core_api.api_call(core_api.ACCESS_LEVEL_ADMIN)
async def get_device(request):
    return core_device_attrs.to_json()


@core_api.api_call(core_api.ACCESS_LEVEL_ADMIN)
async def patch_device(request, params):
    def unexpected_field_msg(field):
        if field in core_device_attrs.ATTRDEFS:
            return 'attribute not modifiable: {field}'

        else:
            return 'no such attribute: {field}'

    core_api_schema.validate(params, core_device_attrs.get_schema(), unexpected_field_msg=unexpected_field_msg)

    try:
        result = core_device_attrs.set_attrs(params)

    except Exception as e:
        raise core_api.APIError(500, str(e)) from e

    # noinspection PyTypeChecker
    if isinstance(result, str):  # API error
        raise core_api.APIError(400, result)

    core_device.save()
    core_device_events.trigger_update()

    if result:  # reboot required
        main.loop.call_later(2, system.reboot)
