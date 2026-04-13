import pytest

from qtoggleserver.core import events as core_events
from qtoggleserver.core.expressions import exceptions as expression_exceptions
from qtoggleserver.lib.filtereventhandler import ANY_VALUE, FilterEventHandler


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

        mock_num_port1.set_last_read_value(60)
        mocker.patch("qtoggleserver.core.ports.get_all", return_value=[mock_num_port1])

        handler = ConcreteFilterEventHandler(filter={"expression": "GT($nid1, 50)"})
        event = core_events.ValueChange(None, 60, mock_num_port1)
        assert await handler.accepts(event, (None, 60), {}, {}, {}, {}, {}) is True

    async def test_expression_blocks(self, mock_num_port1, mocker):
        """Should reject the event when the filter expression evaluates to False."""

        mock_num_port1.set_last_read_value(40)
        mocker.patch("qtoggleserver.core.ports.get_all", return_value=[mock_num_port1])

        handler = ConcreteFilterEventHandler(filter={"expression": "GT($nid1, 50)"})
        event = core_events.ValueChange(None, 40, mock_num_port1)
        assert await handler.accepts(event, (None, 40), {}, {}, {}, {}, {}) is False

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

        mock_num_port1.set_last_read_value(42)
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


class TestFilterEventHandlerGetters(FilterEventHandlerTestBase):
    def test_get_device_attrs_initially_empty(self):
        """Should return an empty dict before any device event is handled."""

        handler = ConcreteFilterEventHandler()
        assert handler.get_device_attrs() == {}

    def test_get_port_values_initially_empty(self):
        """Should return an empty dict before any port event is handled."""

        handler = ConcreteFilterEventHandler()
        assert handler.get_port_values() == {}

    def test_get_port_attrs_initially_empty(self):
        """Should return an empty dict before any port event is handled."""

        handler = ConcreteFilterEventHandler()
        assert handler.get_port_attrs() == {}

    def test_get_slave_attrs_initially_empty(self):
        """Should return an empty dict before any slave event is handled."""

        handler = ConcreteFilterEventHandler()
        assert handler.get_slave_attrs() == {}

    async def test_get_port_values_after_value_change(self, mock_num_port1, mocker):
        """Should reflect the updated port value after a ValueChange event is handled."""

        mocker.patch.object(mock_num_port1, "get_attrs", new=mocker.AsyncMock(return_value={}))
        handler = ConcreteFilterEventHandler()

        mock_num_port1.set_last_read_value(42)
        event = core_events.ValueChange(None, 42, mock_num_port1)
        await handler.handle_event(event)

        assert handler.get_port_values() == {"nid1": 42}

    async def test_get_device_attrs_after_device_update(self, mocker):
        """Should reflect the updated device attributes after a DeviceUpdate event is handled."""

        mocker.patch("qtoggleserver.core.device.attrs.to_json", new=mocker.AsyncMock(return_value={"name": "mydevice"}))
        handler = ConcreteFilterEventHandler()

        event = core_events.DeviceUpdate()
        await handler.handle_event(event)

        assert handler.get_device_attrs() == {"name": "mydevice"}
