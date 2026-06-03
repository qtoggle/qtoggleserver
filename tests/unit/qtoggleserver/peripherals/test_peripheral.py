from qtoggleserver.peripherals import events as peripherals_events
from tests.unit.qtoggleserver.mock.peripherals import MockPeripheral, MockPeripheralPort


class TestSetOnline:
    def make_peripheral(self, mocker) -> MockPeripheral:
        p = MockPeripheral(name="test", dummy_param="v")
        mocker.patch.object(p, "handle_online")
        mocker.patch.object(p, "handle_offline")
        mocker.patch.object(p, "trigger_update_fire_and_forget")
        return p

    def test_handle_online_called_when_transitioning_to_online(self, mocker):
        """Should call handle_online() exactly once when transitioning from offline to online."""

        p = self.make_peripheral(mocker)
        assert not p._online

        p.set_online(True)

        p.handle_online.assert_called_once()
        p.handle_offline.assert_not_called()
        p.trigger_update_fire_and_forget.assert_called_once_with()

    def test_handle_offline_called_when_transitioning_to_offline(self, mocker):
        """Should call handle_offline() exactly once when transitioning from online to offline."""

        p = self.make_peripheral(mocker)
        p._online = True

        p.set_online(False)

        p.handle_offline.assert_called_once()
        p.handle_online.assert_not_called()
        p.trigger_update_fire_and_forget.assert_called_once_with()

    def test_handle_online_not_called_when_already_online(self, mocker):
        """Should not call handle_online() when the peripheral is already online."""

        p = self.make_peripheral(mocker)
        p._online = True

        p.set_online(True)

        p.handle_online.assert_not_called()
        p.trigger_update_fire_and_forget.assert_not_called()

    def test_handle_offline_not_called_when_already_offline(self, mocker):
        """Should not call handle_offline() when the peripheral is already offline."""

        p = self.make_peripheral(mocker)
        assert not p._online

        p.set_online(False)

        p.handle_offline.assert_not_called()
        p.trigger_update_fire_and_forget.assert_not_called()

    def test_online_state_updated_when_going_online(self, mocker):
        """Should update _online to True after set_online(True)."""

        p = self.make_peripheral(mocker)
        p.set_online(True)
        assert p._online is True

    def test_to_json_includes_online_flag(self, mocker):
        p = self.make_peripheral(mocker)
        assert p.to_json()["enabled"] is False
        assert p.to_json()["online"] is False
        assert p.to_json()["force_enabled"] is None
        assert p.to_json()["display_name"] == ""

        p._enabled = True
        p._online = True
        assert p.to_json()["enabled"] is True
        assert p.to_json()["online"] is True

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


class TestDisplayName:
    def test_defaults_to_empty_string(self):
        p = MockPeripheral(name="test", dummy_param="v")

        assert p.get_display_name() == ""
        assert p.to_json()["display_name"] == ""

    def test_set_display_name_updates_value(self):
        p = MockPeripheral(name="test", dummy_param="v")

        p.set_display_name("Test Peripheral")
        assert p.get_display_name() == "Test Peripheral"
        assert p.to_json()["display_name"] == "Test Peripheral"

        p.set_display_name("")
        assert p.get_display_name() == ""
        assert p.to_json()["display_name"] == ""


class TestForceEnabled:
    def test_defaults_to_none(self):
        p = MockPeripheral(name="test", dummy_param="v")

        assert p.get_force_enabled() is None
        assert p.to_json()["force_enabled"] is None

    async def test_false_prevents_enable(self):
        p = MockPeripheral(name="test", dummy_param="v", force_enabled=False)

        await p.enable()

        assert p.is_enabled() is False
        assert p.to_json()["force_enabled"] is False

    async def test_true_prevents_disable(self):
        p = MockPeripheral(name="test", dummy_param="v", force_enabled=True)
        p._enabled = True

        await p.disable()

        assert p.is_enabled() is True
        assert p.to_json()["force_enabled"] is True

    def test_set_force_enabled_updates_value(self):
        p = MockPeripheral(name="test", dummy_param="v")

        p.set_force_enabled(False)
        assert p.get_force_enabled() is False

        p.set_force_enabled(True)
        assert p.get_force_enabled() is True

        p.set_force_enabled(None)
        assert p.get_force_enabled() is None

    async def test_true_forces_enable_after_port_initialization(self, mocker):
        p = MockPeripheral(name="test", dummy_param="v", force_enabled=True)
        mocker.patch.object(p, "handle_enable")
        fake_port = mocker.MagicMock()
        fake_port.get_initial_id.return_value = "id1"
        mocker.patch("qtoggleserver.core.ports.load", return_value=[fake_port])

        await p.init_ports()

        assert p.is_enabled() is True

    async def test_false_skips_port_initialization(self, mocker):
        p = MockPeripheral(name="test", dummy_param="v", force_enabled=False)
        p._enabled = True
        mocker.patch.object(p, "handle_disable")
        spy_load = mocker.patch("qtoggleserver.core.ports.load")

        await p.init_ports()

        spy_load.assert_not_called()
        assert p.get_ports() == []
        assert p.is_enabled() is False


class TestAutoDisable:
    async def test_check_disabled_triggers_update_when_last_port_disabled(self, mocker):
        p = MockPeripheral(name="test", dummy_param="v")
        p._enabled = True

        port = mocker.MagicMock()
        port.is_enabled.return_value = True
        p._ports_by_id["port1"] = port

        spy_disable = mocker.patch.object(p, "disable")
        spy_trigger_update = mocker.patch.object(p, "trigger_update")

        await p.check_disabled(port)

        spy_disable.assert_called_once_with()
        spy_trigger_update.assert_called_once_with()

    async def test_check_disabled_does_not_disable_when_other_port_enabled(self, mocker):
        """Peripheral should stay enabled if at least one other port is enabled."""
        p = MockPeripheral(name="test", dummy_param="v")
        p._enabled = True

        port1 = mocker.MagicMock()
        port1.is_enabled.return_value = False
        p._ports_by_id["port1"] = port1

        port2 = mocker.MagicMock()
        port2.is_enabled.return_value = True
        p._ports_by_id["port2"] = port2

        spy_disable = mocker.patch.object(p, "disable")

        await p.check_disabled(port1)

        spy_disable.assert_not_called()

    async def test_check_disabled_disables_when_all_ports_disabled(self, mocker):
        """Peripheral should disable when all ports are disabled."""
        p = MockPeripheral(name="test", dummy_param="v")
        p._enabled = True

        port1 = mocker.MagicMock()
        port1.is_enabled.return_value = False
        p._ports_by_id["port1"] = port1

        port2 = mocker.MagicMock()
        port2.is_enabled.return_value = False
        p._ports_by_id["port2"] = port2

        spy_disable = mocker.patch.object(p, "disable")
        spy_trigger_update = mocker.patch.object(p, "trigger_update")

        await p.check_disabled(port1)

        spy_disable.assert_called_once_with()
        spy_trigger_update.assert_called_once_with()

    async def test_check_disabled_does_nothing_when_already_disabled(self, mocker):
        """check_disabled should not disable an already disabled peripheral."""
        p = MockPeripheral(name="test", dummy_param="v")
        assert p.is_enabled() is False

        port = mocker.MagicMock()
        port.is_enabled.return_value = False
        p._ports_by_id["port1"] = port

        spy_disable = mocker.patch.object(p, "disable")

        await p.check_disabled(port)

        spy_disable.assert_not_called()


class TestAutoEnable:
    async def test_handle_enable_triggers_update_when_it_enables_peripheral(self, mocker):
        p = MockPeripheral(name="test", dummy_param="v")
        port = MockPeripheralPort(p, "id1")
        spy_enable = mocker.patch.object(p, "enable")
        spy_trigger_update = mocker.patch.object(p, "trigger_update")
        mocker.patch.object(p, "is_enabled", side_effect=[False, True])

        await port.handle_enable()

        spy_enable.assert_called_once_with()
        spy_trigger_update.assert_called_once_with()

    async def test_handle_enable_does_not_trigger_update_when_already_enabled(self, mocker):
        """handle_enable should not trigger update if peripheral was already enabled."""
        p = MockPeripheral(name="test", dummy_param="v")
        p._enabled = True
        port = MockPeripheralPort(p, "id1")
        spy_trigger_update = mocker.patch.object(p, "trigger_update")

        await port.handle_enable()

        spy_trigger_update.assert_not_called()

    async def test_handle_enable_from_disabled_to_enabled(self, mocker):
        """Peripheral should transition from disabled to enabled when a port is enabled."""
        p = MockPeripheral(name="test", dummy_param="v")
        assert p.is_enabled() is False

        port = MockPeripheralPort(p, "id1")
        spy_trigger_update = mocker.patch.object(p, "trigger_update")

        await port.handle_enable()

        assert p.is_enabled() is True
        spy_trigger_update.assert_called_once_with()

    async def test_multiple_ports_only_first_enables_peripheral(self, mocker):
        """Only the first enabled port should trigger peripheral enable."""
        p = MockPeripheral(name="test", dummy_param="v")
        assert p.is_enabled() is False

        port1 = MockPeripheralPort(p, "id1")
        port2 = MockPeripheralPort(p, "id2")

        spy_trigger_update = mocker.patch.object(p, "trigger_update")

        # Enable first port - should enable peripheral
        await port1.handle_enable()
        assert p.is_enabled() is True
        assert spy_trigger_update.call_count == 1

        # Enable second port - peripheral already enabled, no update trigger
        await port2.handle_enable()
        assert p.is_enabled() is True
        assert spy_trigger_update.call_count == 1  # Still 1, not incremented
