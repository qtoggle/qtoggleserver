from qtoggleserver import startup


class TestInitPorts:
    async def test_initializes_peripheral_ports(self, mocker):
        peripheral1 = mocker.MagicMock()
        peripheral1.init_ports = mocker.AsyncMock()

        peripheral2 = mocker.MagicMock()
        peripheral2.init_ports = mocker.AsyncMock()

        spy_ports_init = mocker.patch("qtoggleserver.startup.ports.init")
        spy_ports_load = mocker.patch("qtoggleserver.startup.ports.load")
        spy_vports_init = mocker.patch("qtoggleserver.startup.vports.init")
        mocker.patch("qtoggleserver.startup.logger", mocker.MagicMock())
        mocker.patch("qtoggleserver.startup.peripherals.get_all", return_value=[peripheral1, peripheral2])

        await startup.init_ports()

        spy_ports_init.assert_called_once_with()
        spy_ports_load.assert_called_once_with(startup.settings.ports)
        peripheral1.init_ports.assert_called_once_with()
        peripheral2.init_ports.assert_called_once_with()
        spy_vports_init.assert_called_once_with()

    async def test_disables_peripheral_when_init_ports_fails(self, mocker):
        peripheral1 = mocker.MagicMock()
        peripheral1.get_id.return_value = "peripheral1"
        peripheral1.init_ports = mocker.AsyncMock(side_effect=Exception("init failed"))
        peripheral1.set_force_enabled = mocker.MagicMock()
        peripheral1.disable = mocker.AsyncMock()

        peripheral2 = mocker.MagicMock()
        peripheral2.get_id.return_value = "peripheral2"
        peripheral2.init_ports = mocker.AsyncMock()
        peripheral2.set_force_enabled = mocker.MagicMock()
        peripheral2.disable = mocker.AsyncMock()

        spy_ports_init = mocker.patch("qtoggleserver.startup.ports.init")
        spy_ports_load = mocker.patch("qtoggleserver.startup.ports.load")
        spy_vports_init = mocker.patch("qtoggleserver.startup.vports.init")
        spy_logger = mocker.patch("qtoggleserver.startup.logger")
        mocker.patch("qtoggleserver.startup.peripherals.get_all", return_value=[peripheral1, peripheral2])

        await startup.init_ports()

        spy_ports_init.assert_called_once_with()
        spy_ports_load.assert_called_once_with(startup.settings.ports)
        peripheral1.init_ports.assert_called_once_with()
        peripheral1.set_force_enabled.assert_called_once_with(False)
        peripheral1.disable.assert_called_once_with()
        spy_logger.exception.assert_called_once()
        peripheral2.init_ports.assert_called_once_with()
        peripheral2.set_force_enabled.assert_not_called()
        peripheral2.disable.assert_not_called()
        spy_vports_init.assert_called_once_with()

    async def test_continues_when_static_port_load_has_partial_errors(self, mocker):
        peripheral = mocker.MagicMock()
        peripheral.init_ports = mocker.AsyncMock()

        static_ports = [{"driver": "driver.One", "id": "p1"}, {"driver": "driver.Two", "id": "p2"}]
        mocker.patch.object(startup.settings, "ports", static_ports)

        errors = {0: RuntimeError("first failed"), 1: RuntimeError("second failed")}
        spy_ports_init = mocker.patch("qtoggleserver.startup.ports.init")
        spy_ports_load = mocker.patch(
            "qtoggleserver.startup.ports.load", side_effect=startup.ports.PortLoadErrors(errors)
        )
        spy_vports_init = mocker.patch("qtoggleserver.startup.vports.init")
        spy_logger = mocker.patch("qtoggleserver.startup.logger")
        mocker.patch("qtoggleserver.startup.peripherals.get_all", return_value=[peripheral])

        await startup.init_ports()

        spy_ports_init.assert_called_once_with()
        spy_ports_load.assert_called_once_with(static_ports)
        peripheral.init_ports.assert_called_once_with()
        spy_vports_init.assert_called_once_with()
        assert spy_logger.error.call_count == 2


class TestInit:
    _INIT_STEPS = [
        "init_metadata",
        "init_system",
        "init_persist",
        "init_peripherals",
        "init_events",
        "init_sessions",
        "init_history",
        "init_device",
        "init_webhooks",
        "init_reverse",
        "init_main",
        "init_ports",
        "init_slaves",
        "init_web",
    ]

    def _patch_steps(self, mocker, call_order=None):
        for name in self._INIT_STEPS:
            side_effect = (lambda n=name: call_order.append(n)) if call_order is not None else None
            mocker.patch(f"qtoggleserver.startup.{name}", side_effect=side_effect)

        mocker.patch("qtoggleserver.startup.parse_args")
        mocker.patch("qtoggleserver.startup.init_settings")
        mocker.patch("qtoggleserver.startup.init_logging")
        mocker.patch("qtoggleserver.startup.init_signals")
        mocker.patch("qtoggleserver.startup.init_tornado")
        mocker.patch("qtoggleserver.startup.logger", mocker.MagicMock())
        mocker.patch.object(startup.settings.slaves, "enabled", False)
        mocker.patch("asyncio.sleep", new_callable=mocker.AsyncMock)

    async def test_init_main_runs_before_ports_and_slaves(self, mocker):
        """init_main() (which registers core.main's attr-change event handler) must run before init_ports() and
        init_slaves(), so that PortAdd events fired while loading pre-existing ports are actually observed by the
        handler instead of being fired into an empty handler list."""

        call_order = []
        self._patch_steps(mocker, call_order)
        mocker.patch("qtoggleserver.startup.main.set_ready")

        await startup.init()

        assert call_order.index("init_main") < call_order.index("init_ports")
        assert call_order.index("init_main") < call_order.index("init_slaves")

    async def test_marks_main_ready_after_full_init(self, mocker):
        """init() should call main.set_ready() once initialization (including ports/slaves) has completed."""

        self._patch_steps(mocker)
        spy_set_ready = mocker.patch("qtoggleserver.startup.main.set_ready")

        await startup.init()

        spy_set_ready.assert_called_once_with()

    async def test_waits_for_slaves_ready_before_marking_main_ready(self, mocker):
        """init() should poll slaves_devices.ready() until true, when slaves are enabled, before calling
        main.set_ready()."""

        self._patch_steps(mocker)
        mocker.patch.object(startup.settings.slaves, "enabled", True)
        spy_set_ready = mocker.patch("qtoggleserver.startup.main.set_ready")
        spy_ready = mocker.patch("qtoggleserver.startup.slaves_devices.ready", side_effect=[False, True])

        await startup.init()

        assert spy_ready.call_count == 2
        spy_set_ready.assert_called_once_with()


class TestInitPeripherals:
    async def test_triggers_peripheral_add_events(self, mocker):
        peripheral1 = mocker.MagicMock()
        peripheral1.trigger_add = mocker.AsyncMock()

        peripheral2 = mocker.MagicMock()
        peripheral2.trigger_add = mocker.AsyncMock()

        spy_init = mocker.patch("qtoggleserver.startup.peripherals.init")
        mocker.patch("qtoggleserver.startup.logger", mocker.MagicMock())
        mocker.patch("qtoggleserver.startup.peripherals.get_all", return_value=[peripheral1, peripheral2])

        await startup.init_peripherals()

        spy_init.assert_called_once_with()
        peripheral1.trigger_add.assert_called_once_with()
        peripheral2.trigger_add.assert_called_once_with()
