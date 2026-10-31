from unittest import mock

import pytest

from qtoggleserver.core import events as core_events
from qtoggleserver.core import expressions as core_expressions
from qtoggleserver.core.expressions import Role
from qtoggleserver.core.expressions import exceptions as expression_exceptions
from qtoggleserver.core.expressions.ports import PortValue, PortValueKind
from qtoggleserver.lib.filter_event_handler import ANY_VALUE, FilterEventHandler
from qtoggleserver.slaves import events as slaves_events
from qtoggleserver.utils import expressions as expressions_utils


class ConcreteFilterEventHandler(FilterEventHandler):
    pass


class DummyEvent(core_events.Event):
    TYPE = "dummy"


class FilterEventHandlerTestBase:
    @staticmethod
    def make_dummy_event() -> DummyEvent:
        return DummyEvent()

    @staticmethod
    def make_dummy_handler(filter_dict=None) -> ConcreteFilterEventHandler:
        """Return a filter-prepared handler with the given filter dict."""
        handler = ConcreteFilterEventHandler(filter=filter_dict or {})
        handler._prepare_filter()
        return handler

    @staticmethod
    def make_mock_slave(mocker, json: dict) -> mock.Mock:
        slave = mocker.Mock()
        slave.get_name.return_value = "s1"
        slave.to_json.side_effect = lambda: dict(json, attrs=dict(json["attrs"]))
        return slave


class TestFilterEventHandlerAcceptsDevice(FilterEventHandlerTestBase):
    async def test_no_filter_passes(self):
        """Should accept any device event when no device attribute filter is set."""

        handler = self.make_dummy_handler()
        assert await handler.accepts_device(self.make_dummy_event(), {}, {}) is True

    async def test_attr_match_passes(self):
        """Should accept when the device attribute matches the filter value."""

        handler = self.make_dummy_handler({"device_name": "mydevice"})
        assert await handler.accepts_device(self.make_dummy_event(), {}, {"name": "mydevice"}) is True

    async def test_attr_mismatch_blocks(self):
        """Should reject when the device attribute does not match the filter value."""

        handler = self.make_dummy_handler({"device_name": "mydevice"})
        assert await handler.accepts_device(self.make_dummy_event(), {}, {"name": "other"}) is False

    async def test_attr_list_match_passes(self):
        """Should accept when the device attribute value appears in the filter list."""

        handler = self.make_dummy_handler({"device_name": ["d1", "d2"]})
        assert await handler.accepts_device(self.make_dummy_event(), {}, {"name": "d1"}) is True

    async def test_attr_list_mismatch_blocks(self):
        """Should reject when the device attribute value does not appear in the filter list."""

        handler = self.make_dummy_handler({"device_name": ["d1", "d2"]})
        assert await handler.accepts_device(self.make_dummy_event(), {}, {"name": "d3"}) is False

    async def test_transition_match_passes(self):
        """Should accept when old and new attribute values match the transition filter."""

        handler = self.make_dummy_handler({"device_name_transition": ("old", "new")})
        assert await handler.accepts_device(self.make_dummy_event(), {"name": "old"}, {"name": "new"}) is True

    async def test_transition_mismatch_blocks(self):
        """Should reject when old or new attribute values do not match the transition filter."""

        handler = self.make_dummy_handler({"device_name_transition": ("old", "new")})
        assert await handler.accepts_device(self.make_dummy_event(), {"name": "old"}, {"name": "other"}) is False

    async def test_transition_any_old_value_passes(self):
        """Should accept any old value when the transition filter uses ANY_VALUE for the old side."""

        handler = self.make_dummy_handler({"device_name_transition": (ANY_VALUE, "new")})
        assert await handler.accepts_device(self.make_dummy_event(), {"name": "anything"}, {"name": "new"}) is True

    async def test_transition_no_change_blocks(self):
        """Should reject when old and new values are identical (no actual transition occurred)."""

        handler = self.make_dummy_handler({"device_name_transition": (ANY_VALUE, "same")})
        assert await handler.accepts_device(self.make_dummy_event(), {"name": "same"}, {"name": "same"}) is False


class TestFilterEventHandlerAcceptsPortValue(FilterEventHandlerTestBase):
    async def test_no_filter_passes(self):
        """Should accept any port value when no port_value filter is set."""

        handler = self.make_dummy_handler()
        assert await handler.accepts_port_value(self.make_dummy_event(), (None, 42)) is True

    async def test_exact_value_match_passes(self):
        """Should accept when the new port value matches the filter value exactly."""

        handler = self.make_dummy_handler({"port_value": 42})
        assert await handler.accepts_port_value(self.make_dummy_event(), (None, 42)) is True

    async def test_exact_value_mismatch_blocks(self):
        """Should reject when the new port value does not match the filter value."""

        handler = self.make_dummy_handler({"port_value": 42})
        assert await handler.accepts_port_value(self.make_dummy_event(), (None, 99)) is False

    async def test_list_value_match_passes(self):
        """Should accept when the new port value appears in the filter value list."""

        handler = self.make_dummy_handler({"port_value": [1, 2, 3]})
        assert await handler.accepts_port_value(self.make_dummy_event(), (None, 2)) is True

    async def test_list_value_mismatch_blocks(self):
        """Should reject when the new port value does not appear in the filter value list."""

        handler = self.make_dummy_handler({"port_value": [1, 2, 3]})
        assert await handler.accepts_port_value(self.make_dummy_event(), (None, 99)) is False

    async def test_transition_match_passes(self):
        """Should accept when old and new values match the port_value_transition filter."""

        handler = self.make_dummy_handler({"port_value_transition": (10, 20)})
        assert await handler.accepts_port_value(self.make_dummy_event(), (10, 20)) is True

    async def test_transition_mismatch_blocks(self):
        """Should reject when old or new values do not match the port_value_transition filter."""

        handler = self.make_dummy_handler({"port_value_transition": (10, 20)})
        assert await handler.accepts_port_value(self.make_dummy_event(), (10, 99)) is False

    async def test_transition_any_old_value_passes(self):
        """Should accept any old value when the transition filter uses ANY_VALUE for the old side."""

        handler = self.make_dummy_handler({"port_value_transition": (ANY_VALUE, 20)})
        assert await handler.accepts_port_value(self.make_dummy_event(), (999, 20)) is True

    async def test_transition_no_change_blocks(self):
        """Should reject when old and new values are identical (no actual value transition)."""

        handler = self.make_dummy_handler({"port_value_transition": (ANY_VALUE, 20)})
        assert await handler.accepts_port_value(self.make_dummy_event(), (20, 20)) is False

    async def test_expression_match_passes(self, mocker):
        """Should accept when the new port value equals the result of the port_value expression."""

        mocker.patch("qtoggleserver.core.ports.get_all", return_value=[])
        handler = self.make_dummy_handler({"port_value": "50"})
        assert await handler.accepts_port_value(self.make_dummy_event(), (None, 50)) is True

    async def test_expression_mismatch_blocks(self, mocker):
        """Should reject when the new port value differs from the result of the port_value expression."""

        mocker.patch("qtoggleserver.core.ports.get_all", return_value=[])
        handler = self.make_dummy_handler({"port_value": "50"})
        assert await handler.accepts_port_value(self.make_dummy_event(), (None, 40)) is False

    async def test_expression_eval_error_blocks(self, mocker):
        """Should reject when port_value expression evaluation raises ExpressionEvalException."""

        mocker.patch("qtoggleserver.core.ports.get_all", return_value=[])
        handler = self.make_dummy_handler({"port_value": "50"})
        mocker.patch.object(
            handler._filter_port_value,
            "eval",
            new=mocker.AsyncMock(side_effect=expression_exceptions.ExpressionEvalException("eval error")),
        )
        assert await handler.accepts_port_value(self.make_dummy_event(), (None, 50)) is False


class TestFilterEventHandlerAcceptsPort(FilterEventHandlerTestBase):
    async def test_no_filter_passes(self, mock_num_port1):
        """Should accept any port event when no port filter is set."""

        handler = self.make_dummy_handler()
        event = core_events.ValueChange(None, 42, mock_num_port1)
        assert await handler.accepts_port(event, (None, 42), {}, {}) is True

    async def test_port_value_blocks(self, mock_num_port1):
        """Should reject when the port_value filter does not match the new value."""

        handler = self.make_dummy_handler({"port_value": 99})
        event = core_events.ValueChange(None, 42, mock_num_port1)
        assert await handler.accepts_port(event, (None, 42), {}, {}) is False

    async def test_port_attr_blocks(self, mock_num_port1):
        """Should reject when a port attribute filter does not match."""

        handler = self.make_dummy_handler({"port_tag": "expected-tag"})
        event = core_events.PortUpdate(mock_num_port1)
        assert await handler.accepts_port(event, (None, None), {}, {"tag": "other-tag"}) is False

    async def test_port_value_and_attr_pass(self, mock_num_port1):
        """Should accept when both the port_value and port attribute filters match."""

        handler = self.make_dummy_handler({"port_value": 42, "port_tag": "my-tag"})
        event = core_events.ValueChange(None, 42, mock_num_port1)
        assert await handler.accepts_port(event, (None, 42), {}, {"tag": "my-tag"}) is True


class TestFilterEventHandlerAcceptsSlave(FilterEventHandlerTestBase):
    async def test_no_filter_passes(self):
        """Should accept any slave event when no slave attribute filter is set."""

        handler = self.make_dummy_handler()
        assert await handler.accepts_slave(self.make_dummy_event(), {}, {}) is True

    async def test_attr_match_passes(self):
        """Should accept when the slave attribute matches the filter value."""

        handler = self.make_dummy_handler({"slave_enabled": True})
        assert await handler.accepts_slave(self.make_dummy_event(), {}, {"enabled": True}) is True

    async def test_attr_mismatch_blocks(self):
        """Should reject when the slave attribute does not match the filter value."""

        handler = self.make_dummy_handler({"slave_enabled": True})
        assert await handler.accepts_slave(self.make_dummy_event(), {}, {"enabled": False}) is False

    async def test_transition_match_passes(self):
        """Should accept when old and new slave attribute values match the transition filter."""

        handler = self.make_dummy_handler({"slave_enabled_transition": (False, True)})
        assert await handler.accepts_slave(self.make_dummy_event(), {"enabled": False}, {"enabled": True}) is True

    async def test_transition_mismatch_blocks(self):
        """Should reject when old or new slave attribute values do not match the transition filter."""

        handler = self.make_dummy_handler({"slave_enabled_transition": (False, True)})
        assert await handler.accepts_slave(self.make_dummy_event(), {"enabled": True}, {"enabled": True}) is False


class TestFilterEventHandlerAccepts(FilterEventHandlerTestBase):
    async def test_event_type_match_passes(self, mock_num_port1):
        """Should accept when the event type matches the type filter."""

        handler = self.make_dummy_handler({"type": "value-change"})
        event = core_events.ValueChange(None, 42, mock_num_port1)
        assert await handler.accepts(event, (None, 42), {}, {}, {}, {}, {}) is True

    async def test_event_type_mismatch_blocks(self, mock_num_port1):
        """Should reject when the event type does not match the type filter."""

        handler = self.make_dummy_handler({"type": "port-update"})
        event = core_events.ValueChange(None, 42, mock_num_port1)
        assert await handler.accepts(event, (None, 42), {}, {}, {}, {}, {}) is False

    async def test_multiple_types_match_passes(self, mock_num_port1):
        """Should accept when the event type matches one of the allowed types in the filter list."""

        handler = self.make_dummy_handler({"type": ["port-update", "value-change"]})
        event = core_events.ValueChange(None, 42, mock_num_port1)
        assert await handler.accepts(event, (None, 42), {}, {}, {}, {}, {}) is True

    async def test_expression_passes(self, mock_num_port1, mocker):
        """Should accept the event when the filter expression evaluates to True."""

        mock_num_port1.set_read_value(60)
        mocker.patch("qtoggleserver.core.ports.get_all", return_value=[mock_num_port1])

        handler = ConcreteFilterEventHandler(filter={"expression": "GT($nid1, 50)"})
        event = core_events.ValueChange(None, 60, mock_num_port1)
        assert await handler.accepts(event, (None, 60), {}, {}, {}, {}, {}) is True

    async def test_expression_blocks(self, mock_num_port1, mocker):
        """Should reject the event when the filter expression evaluates to False."""

        mock_num_port1.set_read_value(40)
        mocker.patch("qtoggleserver.core.ports.get_all", return_value=[mock_num_port1])

        handler = ConcreteFilterEventHandler(filter={"expression": "GT($nid1, 50)"})
        event = core_events.ValueChange(None, 40, mock_num_port1)
        assert await handler.accepts(event, (None, 40), {}, {}, {}, {}, {}) is False

    async def test_expression_eval_error_blocks(self, mock_num_port1, mocker):
        """Should reject when filter expression evaluation raises ExpressionEvalException."""

        mocker.patch("qtoggleserver.core.ports.get_all", return_value=[mock_num_port1])
        handler = ConcreteFilterEventHandler(filter={"expression": "GT($nid1, 50)"})
        handler._prepare_filter()
        mocker.patch.object(
            handler._filter_expression,
            "eval",
            new=mocker.AsyncMock(side_effect=expression_exceptions.ExpressionEvalException("eval error")),
        )
        event = core_events.ValueChange(None, 60, mock_num_port1)
        assert await handler.accepts(event, (None, 60), {}, {}, {}, {}, {}) is False

    async def test_invalid_expression(self, mock_num_port1):
        """Should raise ExpressionParseError when the filter expression is syntactically invalid."""

        handler = ConcreteFilterEventHandler(filter={"expression": "NOT_A_VALID_EXPRESSION("})
        event = core_events.ValueChange(None, 42, mock_num_port1)

        with pytest.raises(expression_exceptions.ExpressionParseError):
            await handler.accepts(event, (None, 42), {}, {}, {}, {}, {})

    async def test_filter_prepared_lazily(self, mock_num_port1):
        """Should prepare the filter on the first call to accepts() without an explicit _prepare_filter() call."""

        handler = ConcreteFilterEventHandler(filter={"type": "value-change"})
        assert not handler._filter_prepared

        event = core_events.ValueChange(None, 42, mock_num_port1)
        await handler.accepts(event, (None, 42), {}, {}, {}, {}, {})

        assert handler._filter_prepared


class TestFilterEventHandlerHandleEvent(FilterEventHandlerTestBase):
    async def test_rejected_event_skips_dispatch(self, mock_num_port1, mocker):
        """Should not call on_event or on_value_change when the event does not pass the filter."""

        mocker.patch.object(mock_num_port1, "get_attrs", new=mocker.AsyncMock(return_value={}))
        handler = ConcreteFilterEventHandler(filter={"type": "port-update"})
        handler.on_event = mocker.AsyncMock()
        handler.on_value_change = mocker.AsyncMock()

        event = core_events.ValueChange(None, 42, mock_num_port1)
        await handler.handle_event(event)

        handler.on_event.assert_not_called()
        handler.on_value_change.assert_not_called()

    async def test_value_change_dispatched(self, mock_num_port1, mocker):
        """Should call on_event and on_value_change when a ValueChange event is accepted."""

        mocker.patch.object(mock_num_port1, "get_attrs", new=mocker.AsyncMock(return_value={}))
        handler = ConcreteFilterEventHandler()
        handler.on_event = mocker.AsyncMock()
        handler.on_value_change = mocker.AsyncMock()

        mock_num_port1.set_read_value(42)
        event = core_events.ValueChange(None, 42, mock_num_port1)
        await handler.handle_event(event)

        handler.on_event.assert_called_once_with(event)
        handler.on_value_change.assert_called_once()

    async def test_port_update_dispatched(self, mock_num_port1, mocker):
        """Should call on_port_update when a PortUpdate event is accepted."""

        mocker.patch.object(mock_num_port1, "get_attrs", new=mocker.AsyncMock(return_value={}))
        handler = ConcreteFilterEventHandler()
        handler.on_event = mocker.AsyncMock()
        handler.on_port_update = mocker.AsyncMock()

        event = core_events.PortUpdate(mock_num_port1)
        await event.init_params()
        await handler.handle_event(event)

        handler.on_event.assert_called_once_with(event)
        handler.on_port_update.assert_called_once()

    async def test_port_add_dispatched(self, mock_num_port1, mocker):
        """Should call on_port_add when a PortAdd event is accepted."""

        mocker.patch.object(mock_num_port1, "get_attrs", new=mocker.AsyncMock(return_value={}))
        handler = ConcreteFilterEventHandler()
        handler.on_event = mocker.AsyncMock()
        handler.on_port_add = mocker.AsyncMock()

        event = core_events.PortAdd(mock_num_port1)
        await event.init_params()
        await handler.handle_event(event)

        handler.on_event.assert_called_once_with(event)
        handler.on_port_add.assert_called_once()

    async def test_port_remove_dispatched(self, mock_num_port1, mocker):
        """Should call on_port_remove when a PortRemove event is accepted."""

        mocker.patch.object(mock_num_port1, "get_attrs", new=mocker.AsyncMock(return_value={}))
        handler = ConcreteFilterEventHandler()
        handler.on_event = mocker.AsyncMock()
        handler.on_port_remove = mocker.AsyncMock()

        event = core_events.PortRemove(mock_num_port1)
        await handler.handle_event(event)

        handler.on_event.assert_called_once_with(event)
        handler.on_port_remove.assert_called_once()

    async def test_device_update_dispatched(self, mocker):
        """Should call on_device_update when a DeviceUpdate event is accepted."""

        mocker.patch("qtoggleserver.core.device.attrs.to_json", new=mocker.AsyncMock(return_value={"name": "mydevice"}))
        handler = ConcreteFilterEventHandler()
        handler.on_event = mocker.AsyncMock()
        handler.on_device_update = mocker.AsyncMock()

        event = core_events.DeviceUpdate()
        await event.init_params()
        await handler.handle_event(event)

        handler.on_event.assert_called_once_with(event)
        handler.on_device_update.assert_called_once()

    async def test_full_update_dispatched(self, mocker):
        """Should call on_full_update when a FullUpdate event is accepted."""

        mocker.patch("qtoggleserver.core.device.attrs.to_json", new=mocker.AsyncMock(return_value={"name": "mydevice"}))
        handler = ConcreteFilterEventHandler()
        handler.on_event = mocker.AsyncMock()
        handler.on_full_update = mocker.AsyncMock()

        event = core_events.FullUpdate()
        await handler.handle_event(event)

        handler.on_event.assert_called_once_with(event)
        handler.on_full_update.assert_called_once_with(event)


class TestFilterEventHandlerEvalContext(FilterEventHandlerTestBase):
    async def test_expression_sees_last_value(self, mock_num_port1, mocker):
        """Should evaluate the filter expression with the port's last value, not just its last read value."""

        mock_num_port1.set_read_value(40)
        mocker.patch.object(mock_num_port1, "get_last_value", return_value=60)
        mocker.patch("qtoggleserver.core.ports.get_all", return_value=[mock_num_port1])

        handler = ConcreteFilterEventHandler(filter={"expression": "GT($nid1, 50)"})
        event = core_events.ValueChange(None, 40, mock_num_port1)
        assert await handler.accepts(event, (None, 40), {}, {}, {}, {}, {}) is True

    async def test_expression_sees_disabled_port_attrs(self, mock_num_port1, mocker):
        """Should let the filter expression read the attributes of a disabled port."""

        await mock_num_port1.disable()
        mocker.patch("qtoggleserver.core.ports.get_all", return_value=[mock_num_port1])

        handler = ConcreteFilterEventHandler(filter={"expression": "NOT($nid1:enabled)"})
        assert await handler.accepts(self.make_dummy_event(), (None, None), {}, {}, {}, {}, {}) is True

    async def test_port_value_expression_sees_ports_without_events(self, mock_num_port1, mocker):
        """Should let the port_value expression use ports that the handler has seen no event for."""

        mock_num_port1.set_read_value(50)
        mocker.patch("qtoggleserver.core.ports.get_all", return_value=[mock_num_port1])

        handler = self.make_dummy_handler({"port_value": "$nid1"})
        assert await handler.accepts_port_value(self.make_dummy_event(), (None, 50)) is True


class TestFilterEventHandlerEventValues(FilterEventHandlerTestBase):
    async def test_value_change_uses_event_values(self, mock_num_port1, mocker):
        """Should filter a value change by its own values, even if the port has changed again by the time the event is
        handled."""

        mocker.patch.object(mock_num_port1, "get_attrs", new=mocker.AsyncMock(return_value={}))
        mock_num_port1.set_read_value(9)  # changed back before the event is handled

        handler = ConcreteFilterEventHandler(filter={"port_value": 10, "port_value_transition": [9, 10]})
        mocker.patch.object(handler, "on_value_change", new=mocker.AsyncMock())
        await handler.handle_event(core_events.ValueChange(9, 10, mock_num_port1))

        handler.on_value_change.assert_called_once()
        assert handler.on_value_change.call_args.args[2:4] == (9, 10)

    async def test_eval_context_has_event_read_value(self, mock_num_port1, mocker):
        """Should give filter expressions the value change's own value as the port's last read value, while its last
        value stays the current one."""

        mock_num_port1.set_read_value(0)
        mocker.patch.object(mock_num_port1, "get_last_value", return_value=0)
        mocker.patch("qtoggleserver.core.ports.get_all", return_value=[mock_num_port1])

        handler = self.make_dummy_handler()
        event = core_events.ValueChange(0, 10, mock_num_port1)

        handler._filter_expression = PortValue("nid1", prefix="$", role=Role.FILTER, kind=PortValueKind.LAST_READ)
        assert await handler.accepts(event, (0, 10), {}, {}, {}, {}, {}) is True

        handler._filter_expression = PortValue("nid1", prefix="$", role=Role.FILTER)
        assert await handler.accepts(event, (0, 10), {}, {}, {}, {}, {}) is False

    async def test_port_update_uses_event_attrs(self, mock_num_port1, mocker):
        """Should take a port update's new attrs and value from the event, as they were when it was triggered, without
        changing the event's own params."""

        mocker.patch.object(mock_num_port1, "get_attrs", new=mocker.AsyncMock(return_value={"display_name": "A"}))
        mock_num_port1.set_read_value(5)
        event = core_events.PortUpdate(mock_num_port1)
        await event.init_params()

        # Changed again before the event is handled
        mock_num_port1.get_attrs.return_value = {"display_name": "B"}
        mock_num_port1.set_read_value(6)

        handler = ConcreteFilterEventHandler(filter={"port_display_name": "A", "port_value": 5})
        handler.on_port_update = mocker.AsyncMock()
        await handler.handle_event(event)

        handler.on_port_update.assert_called_once()
        assert handler.on_port_update.call_args.args[2] == 5
        new_attrs = handler.on_port_update.call_args.args[4]
        assert new_attrs == {"display_name": "A"}
        assert event.get_params()["value"] == 5
        assert "definitions" in event.get_params()

    async def test_device_update_uses_event_attrs(self, mocker):
        """Should take a device update's new attrs from the event, as they were when it was triggered."""

        to_json = mocker.patch(
            "qtoggleserver.core.device.attrs.to_json", new=mocker.AsyncMock(return_value={"name": "a"})
        )
        event = core_events.DeviceUpdate()
        await event.init_params()
        to_json.return_value = {"name": "b"}

        handler = ConcreteFilterEventHandler(filter={"device_name": "a"})
        handler.on_device_update = mocker.AsyncMock()
        await handler.handle_event(event)

        handler.on_device_update.assert_called_once()
        assert handler.on_device_update.call_args.args[2] == {"name": "a"}

    async def test_value_change_uses_tracked_attrs(self, mock_num_port1, mocker):
        """Should give a value change the attrs from the port's last update, not the ones at handling time."""

        mocker.patch.object(mock_num_port1, "get_attrs", new=mocker.AsyncMock(return_value={"display_name": "A"}))
        handler = ConcreteFilterEventHandler(filter={"port_display_name": "A"})
        update_event = core_events.PortUpdate(mock_num_port1)
        await update_event.init_params()
        await handler.handle_event(update_event)

        # Changed again, with its port update not handled yet
        mock_num_port1.get_attrs.return_value = {"display_name": "B"}

        handler.on_value_change = mocker.AsyncMock()
        await handler.handle_event(core_events.ValueChange(9, 10, mock_num_port1))

        handler.on_value_change.assert_called_once()
        assert handler.on_value_change.call_args.args[4] == {"display_name": "A"}

    async def test_value_change_falls_back_to_current_attrs(self, mock_num_port1, mocker):
        """Should give a value change the port's current attrs when the handler has seen no update for that port."""

        mocker.patch.object(mock_num_port1, "get_attrs", new=mocker.AsyncMock(return_value={"display_name": "A"}))
        handler = ConcreteFilterEventHandler(filter={"port_display_name": "A"})
        handler.on_value_change = mocker.AsyncMock()
        await handler.handle_event(core_events.ValueChange(9, 10, mock_num_port1))

        handler.on_value_change.assert_called_once()
        assert handler.on_value_change.call_args.args[4] == {"display_name": "A"}

    async def test_port_remove_uses_tracked_attrs(self, mock_num_port1, mocker):
        """Should give a port removal the attrs from the port's last update, and stop tracking them before awaiting
        anything."""

        mocker.patch.object(mock_num_port1, "get_attrs", new=mocker.AsyncMock(return_value={"display_name": "A"}))
        handler = ConcreteFilterEventHandler()
        update_event = core_events.PortUpdate(mock_num_port1)
        await update_event.init_params()
        await handler.handle_event(update_event)

        mock_num_port1.get_attrs.reset_mock()
        handler.on_port_remove = mocker.AsyncMock()
        await handler.handle_event(core_events.PortRemove(mock_num_port1))

        mock_num_port1.get_attrs.assert_not_called()
        assert handler._port_attrs == {}
        handler.on_port_remove.assert_called_once()
        assert handler.on_port_remove.call_args.args[3] == {"display_name": "A"}


class TestFilterEventHandlerUpdateFromEvent(FilterEventHandlerTestBase):
    async def test_port_add(self, mock_num_port1, mocker):
        """Should take a port add's attrs and value from its params, without changing them, and start tracking the
        attrs."""

        mocker.patch.object(mock_num_port1, "get_attrs", new=mocker.AsyncMock(return_value={"display_name": "A"}))
        mock_num_port1.set_read_value(5)
        event = core_events.PortAdd(mock_num_port1)
        await event.init_params()
        params = dict(event.get_params())

        handler = ConcreteFilterEventHandler()
        result = await handler._update_from_event(event)

        assert result == ((5, 5), {}, {"display_name": "A"}, {}, {"display_name": "A"}, {})
        assert handler._port_attrs == {"nid1": {"display_name": "A"}}
        assert event.get_params() == params

    async def test_port_update(self, mock_num_port1, mocker):
        """Should compare a port update's attrs with the tracked ones and track the new ones."""

        attrs = {"display_name": "A", "unit": "C"}
        mocker.patch.object(mock_num_port1, "get_attrs", new=mocker.AsyncMock(side_effect=lambda: dict(attrs)))
        mock_num_port1.set_read_value(5)
        event = core_events.PortUpdate(mock_num_port1)
        await event.init_params()

        handler = ConcreteFilterEventHandler()
        handler._port_attrs = {"nid1": {"display_name": "B", "description": "d"}}
        result = await handler._update_from_event(event)

        assert result == (
            (5, 5),
            {"display_name": "B", "description": "d"},
            attrs,
            {"display_name": ("B", "A")},
            {"unit": "C"},
            {"description": "d"},
        )
        assert handler._port_attrs == {"nid1": attrs}

    async def test_value_change(self, mock_num_port1, mocker):
        """Should give a value change its own values and a copy of the tracked attrs as both old and new attrs."""

        mocker.patch.object(mock_num_port1, "get_attrs", new=mocker.AsyncMock())
        handler = ConcreteFilterEventHandler()
        handler._port_attrs = {"nid1": {"display_name": "A"}}

        result = await handler._update_from_event(core_events.ValueChange(9, 10, mock_num_port1))

        assert result == ((9, 10), {"display_name": "A"}, {"display_name": "A"}, {}, {}, {})
        assert result[2] is not handler._port_attrs["nid1"]
        mock_num_port1.get_attrs.assert_not_called()

    async def test_value_change_untracked(self, mock_num_port1, mocker):
        """Should give a value change for an untracked port its current attrs as both old and new attrs, without
        tracking them."""

        mocker.patch.object(mock_num_port1, "get_attrs", new=mocker.AsyncMock(return_value={"display_name": "A"}))
        handler = ConcreteFilterEventHandler()

        result = await handler._update_from_event(core_events.ValueChange(9, 10, mock_num_port1))

        assert result == ((9, 10), {"display_name": "A"}, {"display_name": "A"}, {}, {}, {})
        assert handler._port_attrs == {}

    async def test_port_remove(self, mock_num_port1, mocker):
        """Should give a port removal the tracked attrs as removed, and stop tracking them."""

        mocker.patch.object(mock_num_port1, "get_attrs", new=mocker.AsyncMock())
        mock_num_port1.set_read_value(5)
        handler = ConcreteFilterEventHandler()
        handler._port_attrs = {"nid1": {"display_name": "A"}}

        result = await handler._update_from_event(core_events.PortRemove(mock_num_port1))

        assert result == ((5, 5), {"display_name": "A"}, {"display_name": "A"}, {}, {}, {"display_name": "A"})
        assert handler._port_attrs == {}
        mock_num_port1.get_attrs.assert_not_called()

    async def test_port_remove_untracked(self, mock_num_port1, mocker):
        """Should give a removal of an untracked port its current attrs as both old and new attrs, and nothing
        removed."""

        mocker.patch.object(mock_num_port1, "get_attrs", new=mocker.AsyncMock(return_value={"display_name": "A"}))
        mock_num_port1.set_read_value(5)
        handler = ConcreteFilterEventHandler()

        result = await handler._update_from_event(core_events.PortRemove(mock_num_port1))

        assert result == ((5, 5), {"display_name": "A"}, {"display_name": "A"}, {}, {}, {})

    async def test_value_change_untracked_rejected_by_attr_transition(self, mock_num_port1, mocker):
        """Should not let an attr transition filter accept a value change for an untracked port."""

        mocker.patch.object(mock_num_port1, "get_attrs", new=mocker.AsyncMock(return_value={"enabled": True}))
        handler = ConcreteFilterEventHandler(filter={"port_enabled_transition": [ANY_VALUE, True]})
        handler.on_value_change = mocker.AsyncMock()

        await handler.handle_event(core_events.ValueChange(9, 10, mock_num_port1))

        handler.on_value_change.assert_not_called()

    async def test_device_update(self, mocker):
        """Should compare a device update's attrs from its params with the tracked ones and track a copy of the new
        ones."""

        mocker.patch(
            "qtoggleserver.core.device.attrs.to_json", new=mocker.AsyncMock(return_value={"name": "a", "ip": "1"})
        )
        event = core_events.DeviceUpdate()
        await event.init_params()

        handler = ConcreteFilterEventHandler()
        handler._device_attrs = {"name": "b", "uptime": 2}
        result = await handler._update_from_event(event)

        assert result == (
            (None, None),
            {"name": "b", "uptime": 2},
            {"name": "a", "ip": "1"},
            {"name": ("b", "a")},
            {"ip": "1"},
            {"uptime": 2},
        )
        assert handler._device_attrs == {"name": "a", "ip": "1"}
        assert handler._device_attrs is not event.get_params()

    async def test_full_update(self, mocker):
        """Should compare a full update's current device attrs with the tracked ones and track the new ones."""

        mocker.patch("qtoggleserver.core.device.attrs.to_json", new=mocker.AsyncMock(return_value={"name": "a"}))
        handler = ConcreteFilterEventHandler()
        handler._device_attrs = {"name": "b"}

        result = await handler._update_from_event(core_events.FullUpdate())

        assert result == ((None, None), {"name": "b"}, {"name": "a"}, {"name": ("b", "a")}, {}, {})
        assert handler._device_attrs == {"name": "a"}

    async def test_slave_device_add(self, mocker):
        """Should flatten a slave add's params into attrs, without changing them, and start tracking the attrs."""

        slave = self.make_mock_slave(mocker, {"name": "s1", "online": True, "attrs": {"uptime": 1}})
        event = slaves_events.SlaveDeviceAdd(slave)
        await event.init_params()
        slave.to_json.side_effect = AssertionError("should use the event params")

        handler = ConcreteFilterEventHandler()
        result = await handler._update_from_event(event)

        attrs = {"name": "s1", "online": True, "uptime": 1}
        assert result == ((None, None), {}, attrs, {}, attrs, {})
        assert handler._slave_attrs == {"s1": attrs}
        assert event.get_params()["attrs"] == {"uptime": 1}

    async def test_slave_device_update(self, mocker):
        """Should compare a slave update's flattened attrs with the tracked ones and track the new ones."""

        slave = self.make_mock_slave(mocker, {"name": "s1", "online": False, "attrs": {"uptime": 1}})
        event = slaves_events.SlaveDeviceUpdate(slave)
        await event.init_params()

        handler = ConcreteFilterEventHandler()
        handler._slave_attrs = {"s1": {"name": "s1", "online": True}}
        result = await handler._update_from_event(event)

        attrs = {"name": "s1", "online": False, "uptime": 1}
        assert result == (
            (None, None),
            {"name": "s1", "online": True},
            attrs,
            {"online": (True, False)},
            {"uptime": 1},
            {},
        )
        assert handler._slave_attrs == {"s1": attrs}

    async def test_slave_device_remove(self, mocker):
        """Should give a slave removal the tracked attrs as removed, and stop tracking them."""

        slave = self.make_mock_slave(mocker, {"name": "s1", "online": True, "attrs": {"uptime": 1}})
        handler = ConcreteFilterEventHandler()
        handler._slave_attrs = {"s1": {"name": "s1", "online": False}}

        result = await handler._update_from_event(slaves_events.SlaveDeviceRemove(slave))

        assert result == (
            (None, None),
            {"name": "s1", "online": False},
            {"name": "s1", "online": True, "uptime": 1},
            {},
            {},
            {"name": "s1", "online": False},
        )
        assert handler._slave_attrs == {}

    async def test_other_event(self):
        """Should return no values and no attrs for other events, and track nothing."""

        handler = ConcreteFilterEventHandler()
        result = await handler._update_from_event(self.make_dummy_event())

        assert result == ((None, None), {}, {}, {}, {}, {})
        assert (handler._port_attrs, handler._device_attrs, handler._slave_attrs) == ({}, {}, {})


class TestFilterEventHandlerPrepareFilter(FilterEventHandlerTestBase):
    def test_splits_filter_keys(self):
        """Should split the filter into event types, attrs and attr transitions per object, keeping port_value and
        port_value_transition out of the port attrs."""

        handler = self.make_dummy_handler(
            {
                "type": "value-change",
                "device_name": "d",
                "device_online_transition": [False, True],
                "port_display_name": "p",
                "port_enabled_transition": [True, False],
                "port_value": 5,
                "port_value_transition": [4, 5],
                "slave_name": ["s1", "s2"],
                "slave_online_transition": [True, ANY_VALUE],
            }
        )

        assert handler._filter_event_types == {"value-change"}
        assert handler._filter_device_attrs == {"name": "d"}
        assert handler._filter_device_attr_transitions == {"online": [False, True]}
        assert handler._filter_device_attr_names == {"name", "online"}
        assert handler._filter_port_attrs == {"display_name": "p"}
        assert handler._filter_port_attr_transitions == {"enabled": [True, False]}
        assert handler._filter_port_attr_names == {"display_name", "enabled"}
        assert handler._filter_port_value == (5,)
        assert handler._filter_port_value_transition == [4, 5]
        assert handler._filter_slave_attrs == {"name": ["s1", "s2"]}
        assert handler._filter_slave_attr_transitions == {"online": [True, ANY_VALUE]}
        assert handler._filter_slave_attr_names == {"name", "online"}
        assert handler._filter_expression is None

    def test_list_values(self):
        """Should keep lists of event types and port values as they are."""

        handler = self.make_dummy_handler({"type": ["port-add", "port-remove"], "port_value": [1, 2]})

        assert handler._filter_event_types == {"port-add", "port-remove"}
        assert handler._filter_port_value == [1, 2]

    def test_port_value_expression(self):
        """Should parse a string port_value as an expression."""

        handler = self.make_dummy_handler({"port_value": "ADD($nid1, 1)"})

        assert isinstance(handler._filter_port_value, core_expressions.Expression)
        assert str(handler._filter_port_value) == "ADD($nid1, 1)"

    def test_invalid_port_value_expression(self):
        """Should raise ExpressionParseError when the port_value expression is invalid."""

        with pytest.raises(expression_exceptions.ExpressionParseError):
            self.make_dummy_handler({"port_value": "ADD("})


class TestFilterEventHandlerMakeChangedAddedRemoved:
    def test_changed_added_removed(self):
        """Should sort attrs into changed, added and removed ones, leaving out unchanged ones."""

        result = FilterEventHandler._make_changed_added_removed({"a": 1, "b": 2, "c": 3}, {"a": 1, "b": 20, "d": 4})

        assert result == ({"b": (2, 20)}, {"d": 4}, {"c": 3})

    def test_none_counts_as_missing(self):
        """Should treat an attr whose value is None like a missing one."""

        result = FilterEventHandler._make_changed_added_removed({"a": None, "b": 2, "c": None}, {"a": 1, "b": None})

        assert result == ({}, {"a": 1}, {"b": 2})


class TestFilterEventHandlerAcceptsEventKinds(FilterEventHandlerTestBase):
    async def test_port_filters_ignore_other_events(self):
        """Should apply port filters only to port events."""

        handler = self.make_dummy_handler({"port_value": 5, "port_display_name": "p"})

        assert await handler.accepts(core_events.DeviceUpdate(), (None, None), {}, {}, {}, {}, {}) is True
        assert await handler.accepts(self.make_dummy_event(), (None, None), {}, {}, {}, {}, {}) is True

    async def test_device_filters_ignore_other_events(self, mock_num_port1):
        """Should apply device filters only to device events."""

        handler = self.make_dummy_handler({"device_name": "d"})
        event = core_events.ValueChange(None, 5, mock_num_port1)

        assert await handler.accepts(event, (None, 5), {}, {}, {}, {}, {}) is True
        assert await handler.accepts(core_events.DeviceUpdate(), (None, None), {}, {"name": "x"}, {}, {}, {}) is False

    async def test_slave_filters_apply_to_slave_events(self, mocker):
        """Should apply slave filters to slave events."""

        slave = self.make_mock_slave(mocker, {"name": "s1", "attrs": {}})
        handler = self.make_dummy_handler({"slave_name": "s2"})
        event = slaves_events.SlaveDeviceUpdate(slave)

        assert await handler.accepts(event, (None, None), {}, {"name": "s1"}, {}, {}, {}) is False
        assert await handler.accepts(event, (None, None), {}, {"name": "s2"}, {}, {}, {}) is True

    async def test_port_value_transition_to_any(self):
        """Should accept a port value transition to any value, as long as the value changes."""

        handler = self.make_dummy_handler({"port_value_transition": [4, ANY_VALUE]})

        assert await handler.accepts_port_value(self.make_dummy_event(), (4, 7)) is True
        assert await handler.accepts_port_value(self.make_dummy_event(), (5, 7)) is False


class TestFilterEventHandlerBuildEvalContext:
    async def test_port_event_read_value(self, mock_num_port1, mocker):
        """Should give a port event's port the value the event carries as its last read value."""

        mock_num_port1.set_read_value(5)
        event = core_events.PortUpdate(mock_num_port1)
        await event.init_params()
        mock_num_port1.set_read_value(7)  # read again before the event is handled
        mocker.patch("qtoggleserver.core.ports.get_all", return_value=[mock_num_port1])

        context = await FilterEventHandler._build_eval_context(event)

        assert context.port_read_values == {"nid1": 5}

    async def test_other_events_keep_read_values(self, mock_num_port1, mocker):
        """Should leave the ports' current last read values in place for events other than port events."""

        mock_num_port1.set_read_value(7)
        mocker.patch("qtoggleserver.core.ports.get_all", return_value=[mock_num_port1])

        context = await FilterEventHandler._build_eval_context(core_events.FullUpdate())

        assert context.port_read_values == {"nid1": 7}


class TestFilterEventHandlerDispatch(FilterEventHandlerTestBase):
    async def test_rejected_event_still_tracked(self, mock_num_port1, mocker):
        """Should track a port's attrs even from an event the filter rejects, so later events see the right old
        attrs."""

        mocker.patch.object(mock_num_port1, "get_attrs", new=mocker.AsyncMock(return_value={"display_name": "A"}))
        handler = ConcreteFilterEventHandler(filter={"type": "value-change"})
        handler.on_port_update = mocker.AsyncMock()
        event = core_events.PortUpdate(mock_num_port1)
        await event.init_params()

        await handler.handle_event(event)

        handler.on_port_update.assert_not_called()
        assert handler._port_attrs == {"nid1": {"display_name": "A"}}

    async def test_port_update_args(self, mock_num_port1, mocker):
        """Should pass a port update's value and its old, new, changed, added and removed attrs to on_port_update."""

        mocker.patch.object(mock_num_port1, "get_attrs", new=mocker.AsyncMock(return_value={"display_name": "A"}))
        handler = ConcreteFilterEventHandler()
        handler._port_attrs = {"nid1": {"display_name": "B", "unit": "C"}}
        handler.on_port_update = mocker.AsyncMock()
        mock_num_port1.set_read_value(5)
        event = core_events.PortUpdate(mock_num_port1)
        await event.init_params()

        await handler.handle_event(event)

        handler.on_port_update.assert_called_once_with(
            event,
            mock_num_port1,
            5,
            {"display_name": "B", "unit": "C"},
            {"display_name": "A"},
            {"display_name": ("B", "A")},
            {},
            {"unit": "C"},
        )

    async def test_slave_device_add_dispatched(self, mocker):
        """Should call on_slave_device_add with the slave's flattened attrs."""

        slave = self.make_mock_slave(mocker, {"name": "s1", "attrs": {"uptime": 1}})
        handler = ConcreteFilterEventHandler()
        handler.on_slave_device_add = mocker.AsyncMock()
        event = slaves_events.SlaveDeviceAdd(slave)
        await event.init_params()

        await handler.handle_event(event)

        handler.on_slave_device_add.assert_called_once_with(event, slave, {"name": "s1", "uptime": 1})

    async def test_slave_device_update_dispatched(self, mocker):
        """Should call on_slave_device_update with the slave's old, new, changed, added and removed attrs."""

        slave = self.make_mock_slave(mocker, {"name": "s1", "attrs": {"uptime": 2}})
        handler = ConcreteFilterEventHandler()
        handler._slave_attrs = {"s1": {"name": "s1", "uptime": 1}}
        handler.on_slave_device_update = mocker.AsyncMock()
        event = slaves_events.SlaveDeviceUpdate(slave)
        await event.init_params()

        await handler.handle_event(event)

        handler.on_slave_device_update.assert_called_once_with(
            event, slave, {"name": "s1", "uptime": 1}, {"name": "s1", "uptime": 2}, {"uptime": (1, 2)}, {}, {}
        )

    async def test_slave_device_remove_dispatched(self, mocker):
        """Should call on_slave_device_remove with the slave's current flattened attrs."""

        slave = self.make_mock_slave(mocker, {"name": "s1", "attrs": {"uptime": 1}})
        handler = ConcreteFilterEventHandler()
        handler.on_slave_device_remove = mocker.AsyncMock()
        event = slaves_events.SlaveDeviceRemove(slave)

        await handler.handle_event(event)

        handler.on_slave_device_remove.assert_called_once_with(event, slave, {"name": "s1", "uptime": 1})

    async def test_on_event_error_does_not_stop_dispatch(self, mock_num_port1, mocker):
        """Should still call on_value_change when on_event fails, and raise neither error."""

        mocker.patch.object(mock_num_port1, "get_attrs", new=mocker.AsyncMock(return_value={}))
        handler = ConcreteFilterEventHandler()
        handler.on_event = mocker.AsyncMock(side_effect=Exception("on_event"))
        handler.on_value_change = mocker.AsyncMock(side_effect=Exception("on_value_change"))

        await handler.handle_event(core_events.ValueChange(9, 10, mock_num_port1))

        handler.on_value_change.assert_called_once()


class TestFilterEventHandlerSharedEvalContext(FilterEventHandlerTestBase):
    async def test_one_context_per_event(self, mock_num_port1, mocker):
        """Should build a single expression context per handled event, shared by all filter expressions, and drop it
        once the event is handled."""

        mocker.patch.object(mock_num_port1, "get_attrs", new=mocker.AsyncMock(return_value={}))
        mocker.patch("qtoggleserver.core.ports.get_all", return_value=[mock_num_port1])
        build_context = mocker.patch(
            "qtoggleserver.utils.expressions.build_context", wraps=expressions_utils.build_context
        )
        handler = ConcreteFilterEventHandler(filter={"port_value": "$nid1", "expression": "EQ($nid1, 10)"})
        handler.on_value_change = mocker.AsyncMock()

        mock_num_port1.set_read_value(10)
        await handler.handle_event(core_events.ValueChange(9, 10, mock_num_port1))

        handler.on_value_change.assert_called_once()
        build_context.assert_called_once()
        assert handler._eval_contexts == {}

    async def test_context_not_kept_outside_handling(self, mock_num_port1, mocker):
        """Should not keep a context built for an event that isn't being handled."""

        mocker.patch("qtoggleserver.core.ports.get_all", return_value=[mock_num_port1])
        handler = ConcreteFilterEventHandler()

        await handler.get_eval_context(core_events.ValueChange(9, 10, mock_num_port1))

        assert handler._eval_contexts == {}

    async def test_port_hooks_get_event_value(self, mock_num_port1, mocker):
        """Should pass the value a port add carries to on_port_add, even if the port has been read again since."""

        mocker.patch.object(mock_num_port1, "get_attrs", new=mocker.AsyncMock(return_value={}))
        mock_num_port1.set_read_value(5)
        event = core_events.PortAdd(mock_num_port1)
        await event.init_params()
        mock_num_port1.set_read_value(6)

        handler = ConcreteFilterEventHandler(filter={"port_value": 5})
        handler.on_port_add = mocker.AsyncMock()
        await handler.handle_event(event)

        handler.on_port_add.assert_called_once_with(event, mock_num_port1, 5, {})
