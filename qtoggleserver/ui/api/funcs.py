
from typing import List

from qtoggleserver import persist
from qtoggleserver.core import api as core_api
from qtoggleserver.core.typing import GenericJSONDict


@core_api.api_call(core_api.ACCESS_LEVEL_VIEWONLY)
def get_panels(request: core_api.APIRequest) -> List[GenericJSONDict]:
    return persist.get_value('dashboard_panels', default=[])


@core_api.api_call(core_api.ACCESS_LEVEL_ADMIN)
def put_panels(request: core_api.APIRequest, params: GenericJSONDict) -> None:
    # core_api.validate(panels, PANELS_SCHEMA)  TODO validate panels against schema

    persist.set_value('dashboard_panels', params)


@core_api.api_call(core_api.ACCESS_LEVEL_VIEWONLY)
def get_prefs(request: core_api.APIRequest) -> GenericJSONDict:
    # TODO add user id

    return persist.get_value('ui_prefs', {})


@core_api.api_call(core_api.ACCESS_LEVEL_VIEWONLY)
def put_prefs(request: core_api.APIRequest, params: GenericJSONDict) -> None:
    # TODO add user id

    persist.set_value('ui_prefs', params)
