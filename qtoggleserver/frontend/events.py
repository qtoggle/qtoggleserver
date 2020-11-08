
from qtoggleserver.core import api as core_api
from qtoggleserver.core import events as core_events
from qtoggleserver.core.typing import GenericJSONDict, GenericJSONList


class FrontendEvent(core_events.Event):
    def __init__(self, request: core_api.APIRequest) -> None:
        self.request: core_api.APIRequest = request

        super().__init__()

    async def to_json(self) -> GenericJSONDict:
        result = await super().to_json()
        result['session_id'] = self.request.session_id

        return result

    def is_duplicate(self, event: core_events.Event) -> bool:
        return isinstance(event, self.__class__) and self.request.session_id == event.request.session_id


class DashboardUpdateEvent(FrontendEvent):
    REQUIRED_ACCESS = core_api.ACCESS_LEVEL_ADMIN
    TYPE = 'dashboard-update'

    def __init__(self, panels: GenericJSONList, **kwargs) -> None:
        self.panels: GenericJSONList = panels

        super().__init__(**kwargs)

    async def get_params(self) -> GenericJSONDict:
        return {
            'panels': self.panels
        }
