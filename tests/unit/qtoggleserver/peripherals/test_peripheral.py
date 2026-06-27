import asyncio

from typing import Any

from qtoggleserver.peripherals import events as peripherals_events
from qtoggleserver.peripherals.exceptions import NotOurPort
from tests.unit.qtoggleserver.mock.peripherals import MockPeripheral, MockPeripheralPort


class _CustomParamsMockPeripheral(MockPeripheral):
    """Mock peripheral that accepts custom params dict for testing."""

    def __init__(self, *, params: dict[str, Any], **kwargs: Any) -> None:
        kwargs.setdefault("params", params)
        super().__init__(**kwargs)


class TestPeripheralID:
    """Tests for Peripheral _id field generation."""

    def test_id_uses_name_when_provided(self):
        """When name is provided, _id should be set to that name."""
        p = MockPeripheral(name="my_device", dummy_param="v")

        assert p.get_id() == "my_device"
        assert p.get_name() == "my_device"
        assert p.to_json()["id"] == "my_device"

    def test_id_generated_from_params_when_no_name(self):
        """When no name is provided, _id should be auto-generated from params hash."""
        p = MockPeripheral(dummy_param="value1")

        assert p.get_id().startswith("peripheral_")
        assert len(p.get_id()) == len("peripheral_") + 8
        assert p.get_name() is None

    def test_same_params_generate_same_id(self):
        """Two peripherals with same params (no name) should have same auto-generated ID."""
        p1 = MockPeripheral(dummy_param="value1")
        p2 = MockPeripheral(dummy_param="value1")

        assert p1.get_id() == p2.get_id()

    def test_different_params_generate_different_ids(self):
        """Two peripherals with different params (no name) should have different auto-generated IDs."""
        p1 = MockPeripheral(dummy_param="value1")
        p2 = MockPeripheral(dummy_param="value2")

        assert p1.get_id() != p2.get_id()

    def test_name_takes_precedence_over_params(self):
        """Name should be used as ID even if params differ."""
        p1 = MockPeripheral(name="device", dummy_param="value1")
        p2 = MockPeripheral(name="device", dummy_param="value2")

        assert p1.get_id() == p2.get_id()
        assert p1.get_id() == "device"

    def test_different_names_generate_different_ids(self):
        """Two peripherals with different names should have different IDs."""
        p1 = MockPeripheral(name="device1", dummy_param="value")
        p2 = MockPeripheral(name="device2", dummy_param="value")

        assert p1.get_id() != p2.get_id()
        assert p1.get_id() == "device1"
        assert p2.get_id() == "device2"

    def test_sorted_params_generate_consistent_id(self):
        """Peripherals with params in different order should have same auto-generated ID."""
        params_order1 = {"z": 3, "a": 1, "m": 2}
        params_order2 = {"a": 1, "m": 2, "z": 3}

        p1 = _CustomParamsMockPeripheral(params=params_order1, dummy_param="v")
        p2 = _CustomParamsMockPeripheral(params=params_order2, dummy_param="v")

        assert p1.get_id() == p2.get_id()

    def test_nested_dict_params_sorted_consistently(self):
        """Nested dicts in params should be sorted consistently."""
        nested1 = {"config": {"z": 3, "a": 1}, "name": "test"}
        nested2 = {"name": "test", "config": {"a": 1, "z": 3}}

        p1 = _CustomParamsMockPeripheral(params=nested1, dummy_param="v")
        p2 = _CustomParamsMockPeripheral(params=nested2, dummy_param="v")

        assert p1.get_id() == p2.get_id()

    def test_auto_generated_id_includes_class_info(self):
        """Auto-generated ID should be based on class module and name."""
        p1 = MockPeripheral(dummy_param="value")
        p2 = MockPeripheral(dummy_param="value")

        assert p1.get_id() == p2.get_id()
        assert p1.get_id().startswith("peripheral_")

    def test_id_in_json_representation(self):
        """ID should be included in to_json() output."""
        p_with_name = MockPeripheral(name="device", dummy_param="v")
        p_auto_id = MockPeripheral(dummy_param="v")

        assert p_with_name.to_json()["id"] == "device"
        assert p_auto_id.to_json()["id"].startswith("peripheral_")

    def test_empty_name_triggers_auto_id(self):
        """Empty string name should trigger auto-ID generation."""
        p_empty = MockPeripheral(name="", dummy_param="value")
        p_no_name = MockPeripheral(dummy_param="value")

        # Both should use auto-generated IDs (not empty string)
        assert p_empty.get_id().startswith("peripheral_")
        assert p_no_name.get_id().startswith("peripheral_")
        # Auto-generated IDs should be deterministic and reproducible
        assert p_empty.get_id() == MockPeripheral(name="", dummy_param="value").get_id()
        assert p_no_name.get_id() == MockPeripheral(dummy_param="value").get_id()
        # Name field should be preserved as provided
        assert p_empty.get_name() == ""
        assert p_no_name.get_name() is None

    def test_complex_params_hash_consistency(self):
        """Complex params structures should produce consistent hashes."""
        complex_params = {
            "host": "192.168.1.1",
            "port": 8080,
            "config": {"nested": {"value": 42}, "enabled": True},
            "list_like": [1, 2, 3],
        }

        p = _CustomParamsMockPeripheral(params=complex_params, dummy_param="v")

        # Creating the same peripheral should produce the same ID
        p_again = _CustomParamsMockPeripheral(params=complex_params, dummy_param="v")
        assert p.get_id() == p_again.get_id()


class TestSetOnline:
    def make_peripheral(self, mocker) -> MockPeripheral:
        p = MockPeripheral(name="test", dummy_param="v")
        mocker.patch.object(p, "handle_online")
        mocker.patch.object(p, "handle_offline")
        mocker.patch.object(p, "trigger_update_fire_and_forget")
        mocker.patch.object(p, "trigger_port_update_fire_and_forget")
        return p

    def test_handle_online_called_when_transitioning_to_online(self, mocker):
        """Should call handle_online() exactly once when transitioning from offline to online."""

        p = self.make_peripheral(mocker)
        assert not p.is_online()

        p.set_online(True)

        p.handle_online.assert_called_once()
        p.handle_offline.assert_not_called()
        p.trigger_update_fire_and_forget.assert_called_once_with()
        p.trigger_port_update_fire_and_forget.assert_called_once_with()
        assert p._online is True

    def test_handle_offline_called_when_transitioning_to_offline(self, mocker):
        """Should call handle_offline() exactly once when transitioning from online to offline."""

        p = self.make_peripheral(mocker)
        p._online = True
        p._enabled = True
        assert p.is_online()

        p.set_online(False)

        p.handle_offline.assert_called_once()
        p.handle_online.assert_not_called()
        p.trigger_update_fire_and_forget.assert_called_once_with()
        p.trigger_port_update_fire_and_forget.assert_called_once_with()
        assert p._online is False
        assert not p.is_online()

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
        """Should update _online and is_online() to True after set_online(True)."""

        p = self.make_peripheral(mocker)
        p._enabled = True
        assert not p.is_online()

        p.set_online(True)

        assert p._online is True
        assert p.is_online()

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

    def test_is_online_requires_both_enabled_and_online(self, mocker):
        """is_online() should return True only when both enabled and online."""
        p = self.make_peripheral(mocker)

        # Neither enabled nor online
        assert not p.is_enabled()
        assert not p.is_online()

        # Online but not enabled
        p._online = True
        assert not p.is_online()

        # Both enabled and online
        p._enabled = True
        assert p.is_online()

        # Enabled but not online
        p._online = False
        assert not p.is_online()

    def test_online_state_updated_when_going_offline(self, mocker):
        """Should update _online and is_online() to False after set_online(False)."""

        p = self.make_peripheral(mocker)
        p._online = True
        p._enabled = True
        assert p.is_online()

        p.set_online(False)

        assert p._online is False
        assert not p.is_online()

    def test_set_online_triggers_port_update_when_going_online(self, mocker):
        """set_online(True) should trigger port update."""
        p = MockPeripheral(name="test", dummy_param="v")
        mocker.patch.object(p, "trigger_update_fire_and_forget")
        spy_trigger = mocker.patch.object(p, "trigger_port_update_fire_and_forget")

        p.set_online(True)

        spy_trigger.assert_called_once()

    def test_set_online_triggers_port_update_when_going_offline(self, mocker):
        """set_online(False) should trigger port update."""
        p = MockPeripheral(name="test", dummy_param="v")
        p._online = True
        mocker.patch.object(p, "trigger_update_fire_and_forget")
        spy_trigger = mocker.patch.object(p, "trigger_port_update_fire_and_forget")

        p.set_online(False)

        spy_trigger.assert_called_once()


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


class TestPortManagement:
    """Tests for port management methods (Priority 1)."""

    async def test_init_ports_loads_and_stores_ports(self, mocker):
        """init_ports should call make_port_args, load ports, and store them."""
        p = MockPeripheral(name="test", dummy_param="v")
        fake_port1 = mocker.MagicMock()
        fake_port1.get_initial_id.return_value = "id1"
        fake_port2 = mocker.MagicMock()
        fake_port2.get_initial_id.return_value = "id2"

        async def fake_load_iter(port_args, trigger_add=True):
            yield fake_port1
            yield fake_port2

        spy_load_iter = mocker.patch("qtoggleserver.core.ports.load_iter", side_effect=fake_load_iter)

        await p.init_ports()

        spy_load_iter.assert_called_once()
        assert len(p._ports_by_id) == 2
        assert p._ports_by_id["id1"] is fake_port1
        assert p._ports_by_id["id2"] is fake_port2

    async def test_init_ports_auto_enables_when_no_ports_loaded(self, mocker):
        """Peripheral should auto-enable when no ports are loaded."""
        p = MockPeripheral(name="test", dummy_param="v")

        async def fake_load_iter_empty(port_args, trigger_add=True):
            return
            yield  # Make it a generator

        mocker.patch("qtoggleserver.core.ports.load_iter", side_effect=fake_load_iter_empty)
        spy_enable = mocker.patch.object(p, "enable")

        await p.init_ports()

        spy_enable.assert_called_once()
        assert len(p._ports_by_id) == 0

    async def test_cleanup_ports_removes_all_ports(self, mocker):
        """cleanup_ports should remove all ports with correct persisted_data flag."""
        p = MockPeripheral(name="test", dummy_param="v")
        fake_port1 = mocker.MagicMock()
        fake_port1.get_initial_id.return_value = "id1"
        fake_port1.remove = mocker.AsyncMock()
        fake_port2 = mocker.MagicMock()
        fake_port2.get_initial_id.return_value = "id2"
        fake_port2.remove = mocker.AsyncMock()

        p._ports_by_id = {"id1": fake_port1, "id2": fake_port2}

        await p.cleanup_ports(persisted_data=True)

        fake_port1.remove.assert_called_once_with(persisted_data=True)
        fake_port2.remove.assert_called_once_with(persisted_data=True)

    async def test_cleanup_ports_with_empty_ports(self, mocker):
        """cleanup_ports should handle empty port list gracefully."""
        p = MockPeripheral(name="test", dummy_param="v")
        p._ports_by_id = {}

        await p.cleanup_ports(persisted_data=False)

        # Should complete without error

    async def test_add_port_loads_and_stores_port(self, mocker):
        """add_port should load a single port and add to _ports_by_id."""
        p = MockPeripheral(name="test", dummy_param="v")
        fake_port = mocker.MagicMock()
        fake_port.get_initial_id.return_value = "new_port"

        spy_load = mocker.patch("qtoggleserver.core.ports.load", return_value=[fake_port])

        port_args = {"driver": MockPeripheralPort, "id": "new_port"}
        result = await p.add_port(port_args)

        spy_load.assert_called_once()
        assert result is fake_port
        assert p._ports_by_id["new_port"] is fake_port

    async def test_add_port_supplies_peripheral_arg(self, mocker):
        """add_port should inject peripheral reference into port_args."""
        p = MockPeripheral(name="test", dummy_param="v")
        fake_port = mocker.MagicMock()
        fake_port.get_initial_id.return_value = "new_port"

        spy_load = mocker.patch("qtoggleserver.core.ports.load", return_value=[fake_port])

        port_args = {"driver": MockPeripheralPort, "id": "new_port"}
        await p.add_port(port_args)

        call_args = spy_load.call_args[0][0]
        assert len(call_args) == 1
        assert call_args[0]["peripheral"] is p
        assert call_args[0]["driver"] is MockPeripheralPort
        # Original dict should not be modified
        assert "peripheral" not in port_args

    async def test_remove_port_removes_and_cleans_up(self, mocker):
        """remove_port should remove from dict and call port.remove()."""
        p = MockPeripheral(name="test", dummy_param="v")
        fake_port = mocker.MagicMock()
        fake_port.remove = mocker.AsyncMock()
        p._ports_by_id["port1"] = fake_port

        await p.remove_port("port1", persisted_data=True)

        assert "port1" not in p._ports_by_id
        fake_port.remove.assert_called_once_with(persisted_data=True)

    async def test_remove_port_strips_peripheral_name_prefix(self, mocker):
        """remove_port should handle port_id with peripheral name prefix."""
        p = MockPeripheral(name="test", dummy_param="v")
        fake_port = mocker.MagicMock()
        fake_port.remove = mocker.AsyncMock()
        p._ports_by_id["port1"] = fake_port

        # Try to remove with prefixed name
        await p.remove_port("test.port1", persisted_data=False)

        assert "port1" not in p._ports_by_id
        fake_port.remove.assert_called_once_with(persisted_data=False)

    async def test_remove_port_raises_not_our_port(self, mocker):
        """remove_port should raise NotOurPort for unknown port_id."""
        p = MockPeripheral(name="test", dummy_param="v")
        fake_port = mocker.MagicMock()
        p._ports_by_id["port1"] = fake_port

        try:
            await p.remove_port("unknown_port")
            assert False, "Should have raised NotOurPort"
        except NotOurPort as e:
            assert "unknown_port" in str(e)
            assert "port1" in p._ports_by_id  # Port1 should still be there

    def test_get_ports_returns_list_of_all_ports(self, mocker):
        """get_ports should return list of all ports."""
        p = MockPeripheral(name="test", dummy_param="v")
        fake_port1 = mocker.MagicMock()
        fake_port2 = mocker.MagicMock()
        p._ports_by_id = {"id1": fake_port1, "id2": fake_port2}

        ports = p.get_ports()

        assert isinstance(ports, list)
        assert len(ports) == 2
        assert fake_port1 in ports
        assert fake_port2 in ports

    def test_get_port_returns_port_by_id(self, mocker):
        """get_port should return port by id or None."""
        p = MockPeripheral(name="test", dummy_param="v")
        fake_port = mocker.MagicMock()
        p._ports_by_id = {"port1": fake_port}

        assert p.get_port("port1") is fake_port
        assert p.get_port("nonexistent") is None

    async def test_get_port_args_transforms_classes_to_dicts(self, mocker):
        """get_port_args should convert port classes to dicts with driver field."""
        p = MockPeripheral(name="test", dummy_param="v")

        # MockPeripheral.make_port_args returns dicts, so let's create a test peripheral that returns classes
        class ClassReturningPeripheral(MockPeripheral):
            async def make_port_args(self):
                return [MockPeripheralPort, {"driver": MockPeripheralPort, "id": "port2"}]

        p = ClassReturningPeripheral(name="test", dummy_param="v")
        port_args = await p.get_port_args()

        assert len(port_args) == 2
        # First arg should be transformed from class to dict
        assert isinstance(port_args[0], dict)
        assert port_args[0]["driver"] is MockPeripheralPort
        assert port_args[0]["peripheral"] is p
        # Second arg should already be dict
        assert isinstance(port_args[1], dict)
        assert port_args[1]["driver"] is MockPeripheralPort
        assert port_args[1]["peripheral"] is p


class TestThreadedRunner:
    """Tests for threaded runner functionality (Priority 2)."""

    async def test_get_runner_creates_and_caches_runner(self, mocker):
        """get_runner should create runner on first call and cache it."""
        p = MockPeripheral(name="test", dummy_param="v")
        spy_make_runner = mocker.patch.object(p, "make_runner")
        fake_runner = mocker.MagicMock()
        spy_make_runner.return_value = fake_runner

        runner1 = p.get_runner()
        runner2 = p.get_runner()

        assert runner1 is fake_runner
        assert runner2 is fake_runner
        spy_make_runner.assert_called_once()

    async def test_make_runner_starts_threaded_runner(self, mocker):
        """make_runner should instantiate and start a ThreadedRunner."""
        p = MockPeripheral(name="test", dummy_param="v")
        fake_runner = mocker.MagicMock()
        mock_runner_class = mocker.patch.object(p, "RUNNER_CLASS", return_value=fake_runner)

        runner = p.make_runner()

        mock_runner_class.assert_called_once_with(queue_size=p.RUNNER_QUEUE_SIZE)
        fake_runner.start.assert_called_once()
        assert runner is fake_runner

    async def test_run_threaded_executes_func_in_runner(self, mocker):
        """run_threaded should schedule function and await result."""
        p = MockPeripheral(name="test", dummy_param="v")
        fake_runner = mocker.MagicMock()
        p._runner = fake_runner

        def test_func(x, y):
            return x + y

        # Simulate successful execution
        def schedule_func(func_partial, callback):
            result = func_partial()
            callback(result, None)

        fake_runner.schedule_func = schedule_func

        result = await p.run_threaded(test_func, 5, 10)

        assert result == 15

    async def test_run_threaded_propagates_exceptions(self, mocker):
        """run_threaded should raise exceptions from the threaded function."""
        p = MockPeripheral(name="test", dummy_param="v")
        fake_runner = mocker.MagicMock()
        p._runner = fake_runner

        def failing_func():
            raise ValueError("Test error")

        # Simulate exception in execution
        def schedule_func(func_partial, callback):
            try:
                func_partial()
            except Exception as e:
                callback(None, e)

        fake_runner.schedule_func = schedule_func

        try:
            await p.run_threaded(failing_func)
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert str(e) == "Test error"

    async def test_run_threaded_handles_cancelled_future(self, mocker):
        """run_threaded should handle cancelled futures gracefully."""
        p = MockPeripheral(name="test", dummy_param="v")
        fake_runner = mocker.MagicMock()
        p._runner = fake_runner

        # Store the callback for later invocation
        stored_callback = None

        def schedule_func(func_partial, callback):
            nonlocal stored_callback
            stored_callback = callback

        fake_runner.schedule_func = schedule_func

        # Start the run_threaded call
        task = asyncio.create_task(p.run_threaded(lambda: 42))

        # Give it a moment to set up
        await asyncio.sleep(0.01)

        # Cancel the task
        task.cancel()

        try:
            await task
        except asyncio.CancelledError:
            pass

        # Now try to invoke the callback - should not raise
        if stored_callback:
            stored_callback(42, None)

    async def test_run_threaded_passes_args_and_kwargs(self, mocker):
        """run_threaded should pass through args and kwargs correctly."""
        p = MockPeripheral(name="test", dummy_param="v")
        fake_runner = mocker.MagicMock()
        p._runner = fake_runner

        def test_func(a, b, c=None, d=None):
            return f"{a}-{b}-{c}-{d}"

        # Simulate successful execution
        def schedule_func(func_partial, callback):
            result = func_partial()
            callback(result, None)

        fake_runner.schedule_func = schedule_func

        result = await p.run_threaded(test_func, "x", "y", c="z", d="w")

        assert result == "x-y-z-w"


class TestPortUpdate:
    """Tests for port update mechanisms (Priority 3)."""

    async def test_trigger_port_update_invalidates_and_updates_ports(self, mocker):
        """trigger_port_update should invalidate attrs and trigger updates."""
        p = MockPeripheral(name="test", dummy_param="v")
        fake_port1 = mocker.MagicMock()
        fake_port1.is_enabled.return_value = True
        fake_port1.invalidate_attrs = mocker.MagicMock()
        fake_port1.trigger_update = mocker.AsyncMock()
        fake_port1.save_asap = mocker.MagicMock()

        fake_port2 = mocker.MagicMock()
        fake_port2.is_enabled.return_value = False
        fake_port2.invalidate_attrs = mocker.MagicMock()
        fake_port2.trigger_update = mocker.AsyncMock()

        p._ports_by_id = {"port1": fake_port1, "port2": fake_port2}

        await p.trigger_port_update(save=False)

        # Both ports should have attrs invalidated
        fake_port1.invalidate_attrs.assert_called_once()
        fake_port2.invalidate_attrs.assert_called_once()

        # Only enabled port should be updated
        fake_port1.trigger_update.assert_called_once()
        fake_port2.trigger_update.assert_not_called()

        # save_asap should not be called when save=False
        fake_port1.save_asap.assert_not_called()

    async def test_trigger_port_update_saves_when_requested(self, mocker):
        """trigger_port_update with save=True should call save_asap on ports."""
        p = MockPeripheral(name="test", dummy_param="v")
        fake_port = mocker.MagicMock()
        fake_port.is_enabled.return_value = True
        fake_port.invalidate_attrs = mocker.MagicMock()
        fake_port.trigger_update = mocker.AsyncMock()
        fake_port.save_asap = mocker.MagicMock()

        p._ports_by_id = {"port1": fake_port}

        await p.trigger_port_update(save=True)

        fake_port.invalidate_attrs.assert_called_once()
        fake_port.trigger_update.assert_called_once()
        fake_port.save_asap.assert_called_once()

    def test_trigger_port_update_fire_and_forget_schedules_task(self, mocker):
        """trigger_port_update_fire_and_forget should schedule async task."""
        p = MockPeripheral(name="test", dummy_param="v")
        spy_create_task = mocker.patch("asyncio.create_task")
        fake_task = mocker.MagicMock()
        spy_create_task.return_value = fake_task

        p.trigger_port_update_fire_and_forget(save=True)

        spy_create_task.assert_called_once()
        assert p._port_update_task is fake_task

    def test_trigger_port_update_fire_and_forget_skips_if_already_scheduled(self, mocker):
        """Should not schedule duplicate port update tasks."""
        p = MockPeripheral(name="test", dummy_param="v")
        spy_create_task = mocker.patch("asyncio.create_task")
        fake_task = mocker.MagicMock()
        p._port_update_task = fake_task

        p.trigger_port_update_fire_and_forget(save=False)

        spy_create_task.assert_not_called()
        assert p._port_update_task is fake_task

    async def test_trigger_port_update_clears_task_reference(self, mocker):
        """trigger_port_update should clear _port_update_task when called."""
        p = MockPeripheral(name="test", dummy_param="v")
        fake_task = mocker.MagicMock()
        p._port_update_task = fake_task
        p._ports_by_id = {}

        await p.trigger_port_update(save=False)

        assert p._port_update_task is None


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


class TestPeripheralToPersisted:
    def test_includes_driver(self):
        """to_persisted should include driver."""
        p = MockPeripheral(name="test", dummy_param="value1")

        result = p.to_persisted()

        assert result["driver"] == "tests.unit.qtoggleserver.mock.peripherals.MockPeripheral"

    def test_includes_name(self):
        """to_persisted should include name."""
        p = MockPeripheral(name="my_peripheral", dummy_param="value1")

        result = p.to_persisted()

        assert result["name"] == "my_peripheral"

    def test_includes_display_name(self):
        """to_persisted should include display_name."""
        p = MockPeripheral(name="test", dummy_param="value1", display_name="My Test Peripheral")

        result = p.to_persisted()

        assert result["display_name"] == "My Test Peripheral"

    def test_includes_force_enabled(self):
        """to_persisted should include force_enabled."""
        p = MockPeripheral(name="test", dummy_param="value1", force_enabled=True)

        result = p.to_persisted()

        assert result["force_enabled"] is True

    def test_includes_params(self):
        """to_persisted should include params."""
        p = MockPeripheral(name="test", dummy_param="special_value")

        result = p.to_persisted()

        assert result["params"]["dummy_param"] == "special_value"

    def test_excludes_transient_fields(self):
        """to_persisted should not include transient fields like enabled, online, id, static."""
        p = MockPeripheral(name="test", dummy_param="value1", static=True)
        p._enabled = True
        p._online = True

        result = p.to_persisted()

        # These should NOT be in persisted data
        assert "enabled" not in result
        assert "online" not in result
        assert "id" not in result
        assert "static" not in result

    def test_with_none_name(self):
        """to_persisted should handle None name correctly."""
        p = MockPeripheral(dummy_param="value1")  # No name provided

        result = p.to_persisted()

        assert result["name"] is None

    def test_with_none_force_enabled(self):
        """to_persisted should handle None force_enabled correctly."""
        p = MockPeripheral(name="test", dummy_param="value1")  # force_enabled defaults to None

        result = p.to_persisted()

        assert result["force_enabled"] is None

    def test_different_from_to_json(self):
        """to_persisted should include different fields than to_json."""
        p = MockPeripheral(name="test", dummy_param="value1", static=True, force_enabled=True)
        p._enabled = True
        p._online = True

        persisted = p.to_persisted()
        json_data = p.to_json()

        # to_json includes these
        assert "enabled" in json_data
        assert "online" in json_data
        assert "id" in json_data
        assert "static" in json_data

        # to_persisted does NOT include these
        assert "enabled" not in persisted
        assert "online" not in persisted
        assert "id" not in persisted
        assert "static" not in persisted

        # Both include these
        assert "driver" in persisted and "driver" in json_data
        assert "name" in persisted and "name" in json_data
        assert "display_name" in persisted and "display_name" in json_data
        assert "force_enabled" in persisted and "force_enabled" in json_data
        assert "params" in persisted and "params" in json_data
