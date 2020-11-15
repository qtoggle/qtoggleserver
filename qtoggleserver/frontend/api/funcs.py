
import logging

from qtoggleserver import persist
from qtoggleserver.core import api as core_api
from qtoggleserver.core import events as core_events
from qtoggleserver.core.typing import GenericJSONDict, GenericJSONList

from ..events import DashboardUpdateEvent


logger = logging.getLogger(__name__)


@core_api.api_call(core_api.ACCESS_LEVEL_VIEWONLY)
async def get_panels(request: core_api.APIRequest) -> GenericJSONList:
    return persist.get_value('dashboard_panels', default=[])


@core_api.api_call(core_api.ACCESS_LEVEL_ADMIN)
async def put_panels(request: core_api.APIRequest, params: GenericJSONList) -> None:
    # core_api.validate(panels, PANELS_SCHEMA)  TODO: validate against schema

    persist.set_value('dashboard_panels', params)

    await core_events.trigger(DashboardUpdateEvent(request=request, panels=params))


@core_api.api_call(core_api.ACCESS_LEVEL_VIEWONLY)
async def get_prefs(request: core_api.APIRequest) -> GenericJSONDict:
    prefs = persist.get('frontend_prefs', id_=request.username) or {}
    prefs.pop('id', None)

    return prefs


@core_api.api_call(core_api.ACCESS_LEVEL_VIEWONLY)
async def put_prefs(request: core_api.APIRequest, params: GenericJSONDict) -> None:
    persist.replace('frontend_prefs', id_=request.username, record=params)


@core_api.api_call(core_api.ACCESS_LEVEL_ADMIN)
async def get_frontend(request: core_api.APIRequest) -> GenericJSONDict:
    return {
        'prefs': sorted(persist.query('frontend_prefs'), key=lambda p: p['id']),
        'dashboard_panels': persist.get_value('dashboard_panels')
    }


@core_api.api_call(core_api.ACCESS_LEVEL_ADMIN)
async def put_frontend(request: core_api.APIRequest, params: GenericJSONDict) -> None:
    # core_api.validate(panels, FRONTEND_SCHEMA)  TODO: validate against schema

    logger.debug('restoring frontend configuration')

    persist.remove('frontend_prefs')

    prefs = params.get('prefs')
    if prefs:
        for p in prefs:
            logger.debug('restoring frontend prefs for username "%s"', p.get('id'))
            persist.insert('frontend_prefs', p)

    dashboard_panels = params.get('dashboard_panels', [])
    logger.debug('restoring dashboard panels')
    persist.set_value('dashboard_panels', dashboard_panels)

    await core_events.trigger(DashboardUpdateEvent(request=request, panels=dashboard_panels))
