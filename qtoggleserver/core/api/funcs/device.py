from qtoggleserver import system
from qtoggleserver.core import api as core_api
from qtoggleserver.core import device as core_device
from qtoggleserver.core import main
from qtoggleserver.core.api import schema as core_api_schema
from qtoggleserver.core.device import attrs as core_device_attrs
from qtoggleserver.core.device import events as core_device_events
from qtoggleserver.core.typing import Attributes


@core_api.api_call(core_api.ACCESS_LEVEL_ADMIN)
async def get_device(request: core_api.APIRequest) -> Attributes:
    return core_device_attrs.to_json()


@core_api.api_call(core_api.ACCESS_LEVEL_ADMIN)
async def put_device(request: core_api.APIRequest, params: Attributes) -> None:
    core_api_schema.validate(
        params,
        core_device_attrs.get_schema(loose=True)
    )

    # Password fields must explicitly be ignored, so we pop them from supplied data
    for f in ('admin', 'normal', 'viewonly'):
        params.pop(f'{f}_password', None)

    # Ignore the date attribute
    params.pop('date', None)

    # Reset device attributes
    await core_device.reset(preserve_attrs=['admin_password_hash', 'normal_password_hash', 'viewonly_password_hash'])
    await core_device.load()

    try:
        core_device_attrs.set_attrs(params, ignore_extra=True)
    except core_device_attrs.DeviceAttributeError as e:
        raise core_api.APIError(400, e.error, attribute=e.attribute)
    except Exception as e:
        raise core_api.APIError(500, 'unexpected-error', message=str(e)) from e

    await core_device.save()
    await core_device_events.trigger_update()


@core_api.api_call(core_api.ACCESS_LEVEL_ADMIN)
async def patch_device(request: core_api.APIRequest, params: Attributes) -> None:
    def unexpected_field_code(field: str) -> str:
        if field in core_device_attrs.get_attrdefs():
            return 'attribute-not-modifiable'
        else:
            return 'no-such-attribute'

    core_api_schema.validate(
        params,
        core_device_attrs.get_schema(),
        unexpected_field_code=unexpected_field_code,
        unexpected_field_name='attribute'
    )

    try:
        reboot_required = core_device_attrs.set_attrs(params)
    except core_device_attrs.DeviceAttributeError as e:
        raise core_api.APIError(400, e.error, attribute=e.attribute)
    except Exception as e:
        raise core_api.APIError(500, 'unexpected-error', message=str(e)) from e

    await core_device.save()
    await core_device_events.trigger_update()

    if reboot_required:
        main.loop.call_later(2, system.reboot)
