from qtoggleserver.core import events as core_events
from qtoggleserver.drivers.events import DummyEventHandler


class TestDummyEventHandler:
    async def test_port_events(self, mock_num_port1, mocker):
        """Should handle port add, update, remove and value change events without errors."""

        mocker.patch.object(mock_num_port1, "get_attrs", new=mocker.AsyncMock(return_value={}))
        mocker.patch("qtoggleserver.core.ports.get_all", return_value=[mock_num_port1])
        handler = DummyEventHandler()
        mocker.patch.object(handler, "error")

        for event in (
            core_events.PortAdd(mock_num_port1),
            core_events.PortUpdate(mock_num_port1),
            core_events.ValueChange(9, 10, mock_num_port1),
            core_events.PortRemove(mock_num_port1),
        ):
            await event.init_params()
            await handler.handle_event(event)

        handler.error.assert_not_called()
