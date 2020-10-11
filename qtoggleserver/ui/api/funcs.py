
import logging

from typing import List

from qtoggleserver import persist
from qtoggleserver.core import api as core_api
from qtoggleserver.core.typing import GenericJSONDict


logger = logging.getLogger(__name__)


@core_api.api_call(core_api.ACCESS_LEVEL_VIEWONLY)
def get_panels(request: core_api.APIRequest) -> List[GenericJSONDict]:
    return persist.get_value('dashboard_panels', default=[])


@core_api.api_call(core_api.ACCESS_LEVEL_ADMIN)
def put_panels(request: core_api.APIRequest, params: GenericJSONDict) -> None:
    # core_api.validate(panels, PANELS_SCHEMA)  TODO: validate against schema

    persist.set_value('dashboard_panels', params)


@core_api.api_call(core_api.ACCESS_LEVEL_VIEWONLY)
def get_prefs(request: core_api.APIRequest) -> GenericJSONDict:
    prefs = persist.get('ui_prefs', id_=request.username) or {}
    prefs.pop('id', None)

    return prefs


@core_api.api_call(core_api.ACCESS_LEVEL_VIEWONLY)
def put_prefs(request: core_api.APIRequest, params: GenericJSONDict) -> None:
    persist.replace('ui_prefs', id_=request.username, record=params)


@core_api.api_call(core_api.ACCESS_LEVEL_ADMIN)
def get_frontend(request: core_api.APIRequest) -> GenericJSONDict:
    return {
        'ui_prefs': sorted(persist.query('ui_prefs'), key=lambda p: p['id']),
        'dashboard_panels': persist.get_value('dashboard_panels')
    }


@core_api.api_call(core_api.ACCESS_LEVEL_ADMIN)
def put_frontend(request: core_api.APIRequest, params: GenericJSONDict) -> None:
    # core_api.validate(panels, FRONTEND_SCHEMA)  TODO: validate against schema

    logger.debug('restoring frontend configuration')

    persist.remove('ui_prefs')

    ui_prefs = params.get('ui_prefs')
    if ui_prefs:
        for p in ui_prefs:
            logger.debug('restoring ui prefs for username "%s"', p.get('id'))
            persist.insert('ui_prefs', p)

    dashboard_panels = params.get('dashboard_panels', [])
    logger.debug('restoring dashboard panels')
    persist.set_value('dashboard_panels', dashboard_panels)
