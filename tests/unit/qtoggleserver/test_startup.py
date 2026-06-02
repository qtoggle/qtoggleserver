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
