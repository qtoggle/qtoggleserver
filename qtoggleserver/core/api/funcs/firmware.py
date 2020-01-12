
import logging

from qtoggleserver.core import api as core_api
from qtoggleserver.core.api import schema as core_api_schema
from qtoggleserver.core.typing import GenericJSONDict
from qtoggleserver.system import fwupdate


logger = logging.getLogger(__name__)


@core_api.api_call(core_api.ACCESS_LEVEL_ADMIN)
async def get_firmware(request: core_api.APIRequest) -> GenericJSONDict:
    current_version = await fwupdate.get_current_version()
    status = await fwupdate.get_status()

    if status == fwupdate.STATUS_IDLE:
        try:
            latest_version, latest_date, latest_url = await fwupdate.get_latest()

            return {
                'version': current_version,
                'latest_version': latest_version,
                'latest_date': latest_date,
                'latest_url': latest_url,
                'status': status
            }

        except Exception as e:
            logger.error('get latest firmware failed: %s', e, exc_info=True)

            return {
                'version': current_version,
                'status': status
            }

    else:
        return {
            'version': current_version,
            'status': status
        }


@core_api.api_call(core_api.ACCESS_LEVEL_ADMIN)
async def patch_firmware(request: core_api.APIRequest, params: GenericJSONDict) -> None:
    core_api_schema.validate(params, core_api_schema.PATCH_FIRMWARE)

    status = await fwupdate.get_status()
    if status not in (fwupdate.STATUS_IDLE, fwupdate.STATUS_ERROR):
        raise core_api.APIError(503, 'busy')

    if params.get('url'):
        await fwupdate.update_to_url(params['url'])

    else:  # Assuming params['version']
        await fwupdate.update_to_version(params['version'])
