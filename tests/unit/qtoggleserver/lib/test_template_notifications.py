from qtoggleserver.core import events as core_events
from qtoggleserver.lib.template_notifications import TemplateNotificationsHandler
from qtoggleserver.utils import expressions as expressions_utils


class ConcreteTemplateNotificationsHandler(TemplateNotificationsHandler):
    pass


class TestTemplateNotificationsCommonContext:
    async def test_values_from_build_context(self, mock_num_port1, mocker):
        """Should take port values, port read and written values, port attrs and device attrs from `build_context()`,
        so that templates see every port's values, even for ports the handler has seen no event for."""

        mocker.patch.object(mock_num_port1, "get_last_value", return_value=60)
        mocker.patch.object(mock_num_port1, "get_last_read_value", return_value=40)
        mocker.patch.object(mock_num_port1, "get_last_written_value", return_value=60)
        mocker.patch("qtoggleserver.core.ports.get_all", return_value=[mock_num_port1])

        handler = ConcreteTemplateNotificationsHandler()
        context = await handler.get_common_context(core_events.FullUpdate())

        assert context["port_values"] == {"nid1": 60}
        assert context["port_read_values"] == {"nid1": 40}
        assert context["port_written_values"] == {"nid1": 60}
        assert context["port_attrs"]["nid1"] == await mock_num_port1.get_attrs()
        assert "device_attrs" in context

    async def test_port_event_value_is_event_value(self, mock_num_port1, mocker):
        """Should give a port event's template the value the event carries, also as the port's last read value, while
        `port_values` keeps the port's last value."""

        mocker.patch.object(mock_num_port1, "get_attrs", new=mocker.AsyncMock(return_value={}))
        mocker.patch("qtoggleserver.core.ports.get_all", return_value=[mock_num_port1])
        mocker.patch("qtoggleserver.lib.template_notifications.core_main.is_ready", return_value=True)
        mock_num_port1.set_read_value(5)
        event = core_events.PortUpdate(mock_num_port1)
        await event.init_params()

        # Changed again before the event is handled
        mock_num_port1.set_read_value(6)
        mocker.patch.object(mock_num_port1, "get_last_value", return_value=60)

        handler = ConcreteTemplateNotificationsHandler(skip_startup=False)
        mocker.patch.object(handler, "push_template_message", new=mocker.AsyncMock())
        await handler.handle_event(event)

        context = handler.push_template_message.call_args.args[1]
        assert context["value"] == 5
        assert context["port_read_values"]["nid1"] == 5
        assert context["port_values"]["nid1"] == 60

    async def test_same_context_as_filter(self, mock_num_port1, mocker):
        """Should render templates with the same expression context that the filter used."""

        mocker.patch.object(mock_num_port1, "get_attrs", new=mocker.AsyncMock(return_value={}))
        mocker.patch("qtoggleserver.core.ports.get_all", return_value=[mock_num_port1])
        mocker.patch("qtoggleserver.lib.template_notifications.core_main.is_ready", return_value=True)
        build_context = mocker.patch(
            "qtoggleserver.utils.expressions.build_context", wraps=expressions_utils.build_context
        )

        handler = ConcreteTemplateNotificationsHandler(skip_startup=False, filter={"expression": "EQ($nid1, 10)"})
        mocker.patch.object(handler, "push_template_message", new=mocker.AsyncMock())
        mock_num_port1.set_read_value(10)
        await handler.handle_event(core_events.ValueChange(9, 10, mock_num_port1))

        build_context.assert_called_once()
        context = handler.push_template_message.call_args.args[1]
        assert context["port_read_values"]["nid1"] == 10

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

    async def test_port_remove_context(self, mock_num_port1, mocker):
        """Should keep a removed port in the template context of its removal, with the attrs its removal reports."""

        mocker.patch.object(mock_num_port1, "get_attrs", new=mocker.AsyncMock(return_value={"display_name": "B"}))
        mocker.patch("qtoggleserver.core.ports.get_all", return_value=[])
        mocker.patch("qtoggleserver.lib.template_notifications.core_main.is_ready", return_value=True)
        mock_num_port1.set_read_value(5)

        handler = ConcreteTemplateNotificationsHandler(skip_startup=False)
        handler._port_attrs = {"nid1": {"display_name": "A"}}
        mocker.patch.object(handler, "push_template_message", new=mocker.AsyncMock())
        await handler.handle_event(core_events.PortRemove(mock_num_port1))

        context = handler.push_template_message.call_args.args[1]
        assert context["value"] == 5
        assert context["attrs"] == {"display_name": "A"}
        assert context["port_attrs"] == {"nid1": {"display_name": "A"}}
        assert context["port_read_values"] == {"nid1": 5}
        assert context["port_values"] == {"nid1": 5}
