
from collections import OrderedDict

from qtoggleserver.conf import settings
from qtoggleserver.core import api as core_api
from qtoggleserver.core.typing import GenericJSONDict
from qtoggleserver.system import conf as system_conf
from qtoggleserver.utils import conf as conf_utils


@core_api.api_call(core_api.ACCESS_LEVEL_ADMIN)
async def get_system(request: core_api.APIRequest) -> GenericJSONDict:
    return conf_utils.config_from_file(settings.source)


@core_api.api_call(core_api.ACCESS_LEVEL_ADMIN)
async def put_system(request: core_api.APIRequest, params: GenericJSONDict) -> None:
    # Update in-memory settings (no effect guaranteed without a restart, though)
    conf_utils.update_obj_from_dict(settings, OrderedDict(params))

    # Update config file
    system_conf.conf_file_from_dict(params)
