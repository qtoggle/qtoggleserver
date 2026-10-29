import pytest

from qtoggleserver.core import events as core_events
from qtoggleserver.core.expressions import Role
from qtoggleserver.core.expressions import exceptions as expression_exceptions
from qtoggleserver.core.expressions.ports import PortValue, PortValueKind
from qtoggleserver.lib.filter_event_handler import ANY_VALUE, FilterEventHandler


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
        new_attrs = handler.on_port_update.call_args.args[3]
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
        assert handler.on_port_remove.call_args.args[2] == {"display_name": "A"}
