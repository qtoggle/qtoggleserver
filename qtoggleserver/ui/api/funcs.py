
from qtoggleserver import persist
from qtoggleserver.core import api as core_api


@core_api.api_call(core_api.ACCESS_LEVEL_VIEWONLY)
def get_panels(request):
    return persist.get_value('dashboard_panels', default=[])


@core_api.api_call(core_api.ACCESS_LEVEL_ADMIN)
def put_panels(request, params):
    # core_api.validate(panels, PANELS_SCHEMA)  TODO validate panels against schema

    persist.set_value('dashboard_panels', params)


@core_api.api_call(core_api.ACCESS_LEVEL_VIEWONLY)
def get_prefs(request):
    # TODO add user id

    return persist.get_value('ui_prefs', {})


@core_api.api_call(core_api.ACCESS_LEVEL_VIEWONLY)
def put_prefs(request, params):
    # TODO add user id

    persist.set_value('ui_prefs', params)
