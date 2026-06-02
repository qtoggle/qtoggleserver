from qtoggleserver.peripherals import events as peripherals_events
from tests.unit.qtoggleserver.mock.peripherals import MockPeripheral


class TestSetOnline:
    def make_peripheral(self, mocker) -> MockPeripheral:
        p = MockPeripheral(name="test", dummy_param="v")
        mocker.patch.object(p, "handle_online")
        mocker.patch.object(p, "handle_offline")
        return p

    def test_handle_online_called_when_transitioning_to_online(self, mocker):
        """Should call handle_online() exactly once when transitioning from offline to online."""

        p = self.make_peripheral(mocker)
        assert not p._online

        p.set_online(True)

        p.handle_online.assert_called_once()
        p.handle_offline.assert_not_called()

    def test_handle_offline_called_when_transitioning_to_offline(self, mocker):
        """Should call handle_offline() exactly once when transitioning from online to offline."""

        p = self.make_peripheral(mocker)
        p._online = True

        p.set_online(False)

        p.handle_offline.assert_called_once()
        p.handle_online.assert_not_called()

    def test_handle_online_not_called_when_already_online(self, mocker):
        """Should not call handle_online() when the peripheral is already online."""

        p = self.make_peripheral(mocker)
        p._online = True

        p.set_online(True)

        p.handle_online.assert_not_called()

    def test_handle_offline_not_called_when_already_offline(self, mocker):
        """Should not call handle_offline() when the peripheral is already offline."""

        p = self.make_peripheral(mocker)
        assert not p._online

        p.set_online(False)

        p.handle_offline.assert_not_called()

    def test_online_state_updated_when_going_online(self, mocker):
        """Should update _online to True after set_online(True)."""

        p = self.make_peripheral(mocker)
        p.set_online(True)
        assert p._online is True

    def test_online_state_updated_when_going_offline(self, mocker):
        """Should update _online to False after set_online(False)."""

        p = self.make_peripheral(mocker)
        p._online = True
        p.set_online(False)
        assert p._online is False


class TestTriggerEvents:
    async def test_trigger_add(self, mocker):
        p = MockPeripheral(name="test", dummy_param="v")
        spy_trigger = mocker.patch("qtoggleserver.core.events.trigger")

        await p.trigger_add()

        spy_trigger.assert_called_once()
        event = spy_trigger.call_args.args[0]
        assert isinstance(event, peripherals_events.PeripheralAdd)
        assert event.get_peripheral() is p

    async def test_trigger_remove(self, mocker):
        p = MockPeripheral(name="test", dummy_param="v")
        spy_trigger = mocker.patch("qtoggleserver.core.events.trigger")

        await p.trigger_remove()

        spy_trigger.assert_called_once()
        event = spy_trigger.call_args.args[0]
        assert isinstance(event, peripherals_events.PeripheralRemove)
        assert event.get_peripheral() is p

    async def test_trigger_update(self, mocker):
        p = MockPeripheral(name="test", dummy_param="v")
        spy_trigger = mocker.patch("qtoggleserver.core.events.trigger")

        await p.trigger_update()

        spy_trigger.assert_called_once()
        event = spy_trigger.call_args.args[0]
        assert isinstance(event, peripherals_events.PeripheralUpdate)
        assert event.get_peripheral() is p
