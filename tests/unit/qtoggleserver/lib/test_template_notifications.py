from qtoggleserver.core import events as core_events
from qtoggleserver.lib.template_notifications import TemplateNotificationsHandler


class ConcreteTemplateNotificationsHandler(TemplateNotificationsHandler):
    pass


class TestTemplateNotificationsCommonContext:
    async def test_values_from_build_context(self, mock_num_port1, mocker):
        """Should take port values, port attrs and device attrs from `build_context()`, so that templates see every
        port's last value, even for ports the handler has seen no event for."""

        mocker.patch.object(mock_num_port1, "get_last_value", return_value=60)
        mocker.patch("qtoggleserver.core.ports.get_all", return_value=[mock_num_port1])

        handler = ConcreteTemplateNotificationsHandler()
        context = await handler.get_common_context(core_events.FullUpdate())

        assert context["port_values"] == {"nid1": 60}
        assert context["port_attrs"]["nid1"] == await mock_num_port1.get_attrs()
        assert "device_attrs" in context

    async def test_port_event_value_is_last_value(self, mock_num_port1, mocker):
        """Should give a port event's template the port's last value, matching its entry in `port_values`."""

        mocker.patch.object(mock_num_port1, "get_last_value", return_value=60)
        mocker.patch("qtoggleserver.core.ports.get_all", return_value=[mock_num_port1])

        handler = ConcreteTemplateNotificationsHandler()
        mocker.patch.object(handler, "push_template_message", new=mocker.AsyncMock())
        await handler.on_port_update(core_events.PortUpdate(mock_num_port1), mock_num_port1, {}, {}, {}, {}, {})

        context = handler.push_template_message.call_args.args[1]
        assert context["value"] == 60
        assert context["port_values"]["nid1"] == 60

    async def test_value_change_uses_event_values(self, mock_num_port1, mocker):
        """Should give a value change template the event's own old and new values, even if the port has changed again
        by the time the event is handled."""

        mocker.patch.object(mock_num_port1, "get_attrs", new=mocker.AsyncMock(return_value={}))
        mocker.patch("qtoggleserver.core.ports.get_all", return_value=[mock_num_port1])
        mocker.patch("qtoggleserver.lib.template_notifications.core_main.is_ready", return_value=True)
        mock_num_port1.set_read_value(9)

        handler = ConcreteTemplateNotificationsHandler(skip_startup=False)
        mocker.patch.object(handler, "push_template_message", new=mocker.AsyncMock())
        await handler.handle_event(core_events.ValueChange(9, 10, mock_num_port1))

        context = handler.push_template_message.call_args.args[1]
        assert (context["old_value"], context["new_value"]) == (9, 10)
