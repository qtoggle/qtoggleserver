import asyncio

from qtoggleserver.core.expressions.exceptions import ValueUnavailable


class TestPortGetLastValue:
    def test_pending(self, mock_num_port1, mocker):
        """Should return the pending value, since it's not None."""

        mocker.patch.object(mock_num_port1, "get_pending_value", return_value=100)
        mock_num_port1._last_written_value = None
        mock_num_port1._last_read_value = None
        assert mock_num_port1.get_last_value() == 100

        mock_num_port1._last_written_value = (200, 2000)
        mock_num_port1._last_read_value = (300, 1000)
        assert mock_num_port1.get_last_value() == 100

    def test_last_written(self, mock_num_port1, mocker):
        """Should return the last written value."""

        mocker.patch.object(mock_num_port1, "get_pending_value", return_value=None)
        mock_num_port1._last_written_value = (200, 2000)
        mock_num_port1._last_read_value = None
        assert mock_num_port1.get_last_value() == 200

        mock_num_port1._last_read_value = (300, 1000)  # older timestamp
        assert mock_num_port1.get_last_value() == 200

    def test_last_read(self, mock_num_port1, mocker):
        """Should return the last read value."""

        mocker.patch.object(mock_num_port1, "get_pending_value", return_value=None)
        mock_num_port1._last_written_value = None
        mock_num_port1._last_read_value = (300, 2000)
        assert mock_num_port1.get_last_value() == 300

        mock_num_port1._last_written_value = (200, 1000)  # newer timestamp
        assert mock_num_port1.get_last_value() == 300


class TestPortEvalAndPushWrite:
    async def test(self, mock_num_port1, mock_num_port2, mocker):
        """Should evaluate the expression with the provided eval context and push the result to the write queue."""

        mock_eval_context = mocker.Mock()
        mock_expression = mocker.Mock()
        mock_expression.eval = mocker.AsyncMock(return_value=99)
        mocker.patch.object(mock_num_port1, "get_expression", return_value=mock_expression)

        mocker.patch.object(mock_num_port1, "adapt_value_type", return_value=100)
        mocker.patch.object(mock_num_port1, "get_last_value", return_value=None)
        mock_num_port1._write_queue = mocker.Mock()

        await mock_num_port1.eval_and_push_write(mock_eval_context)

        mock_expression.eval.assert_called_once_with(mock_eval_context)
        mock_num_port1.adapt_value_type.assert_called_once_with(mock_expression.eval.return_value)
        mock_num_port1._write_queue.append.assert_called_once_with(100)

    async def test_unavailable_not_written(self, mock_num_port1, mocker):
        """Should not push anything to the write queue if the expression evaluation raises due to value being
        unavailable."""

        mock_eval_context = mocker.Mock()
        mock_num_port1._expression = mocker.Mock()
        mock_num_port1._expression.eval = mocker.AsyncMock(side_effect=ValueUnavailable)
        mock_num_port1._write_queue = mocker.Mock()

        await mock_num_port1.eval_and_push_write(mock_eval_context)
        mock_num_port1._write_queue.append.assert_not_called()


class TestPortGetPendingValue:
    def test_no_pending_value(self, mock_num_port1):
        """Should return `None` if there's no writing value and writing queue is empty."""

        mock_num_port1._writing_value = None
        assert mock_num_port1.get_pending_value() is None

    def test_with_queue(self, mock_num_port1):
        """Should return the most recent value from writing queue."""

        mock_num_port1._writing_value = 1
        mock_num_port1._write_queue.append(2)
        mock_num_port1._write_queue.append(3)
        mock_num_port1._write_queue.append(4)
        assert mock_num_port1.get_pending_value() == 4

    def test_empty_queue(self, mock_num_port1):
        """Should return the currently writing value, since writing queue is empty."""

        mock_num_port1._writing_value = 1
        assert mock_num_port1.get_pending_value() == 1


class TestPortGetAttr:
    async def test_unknown_attribute(self, mock_num_port1):
        """Should return `None` for an unsupported/unknown attribute."""

        assert await mock_num_port1.get_attr("unknown_attribute") is None

    async def test_cache(self, mock_num_port1, mocker):
        """Should return value from cache first, before trying any other sources."""

        class TempMockPort(type(mock_num_port1)):
            async def attr_get_display_name(self) -> str:
                return ""

            async def attr_get_default_display_name(self) -> str:
                raise AssertionError("Should not be called")

        mock_num_port2 = TempMockPort("tmp", None)
        mock_num_port2._display_name = "value1"
        mock_num_port2._attrs_cache["display_name"] = "value2"
        mocker.patch.object(mock_num_port2, "attr_get_display_name", return_value="value3")
        mocker.patch.object(mock_num_port2, "attr_get_value", return_value="value4")
        assert await mock_num_port2.get_attr("display_name") == "value2"
        mock_num_port2.attr_get_display_name.assert_not_called()
        mock_num_port2.attr_get_value.assert_not_called()

    async def test_call_attr_getter(self, mock_num_port1, mocker):
        """Should call the attribute getter method instead of returning the private property."""

        class TempMockPort(type(mock_num_port1)):
            async def attr_get_display_name(self) -> str:
                return ""

            def attr_get_sync_getter(self) -> str:
                return ""

            async def attr_is_boolean_getter(self) -> bool:
                return True

            def attr_is_sync_boolean_getter(self) -> bool:
                return True

            async def attr_get_default_display_name(self) -> str:
                raise AssertionError("Should not be called")

            def attr_get_default_sync_getter(self) -> str:
                raise AssertionError("Should not be called")

            async def attr_is_default_boolean_getter(self) -> bool:
                raise AssertionError("Should not be called")

            def attr_is_default_sync_boolean_getter(self) -> bool:
                raise AssertionError("Should not be called")

        mock_num_port2 = TempMockPort("tmp", None)
        mock_num_port2._display_name = "value1"
        mocker.patch.object(mock_num_port2, "attr_get_display_name", return_value="value2")
        mock_num_port2.invalidate_attrs()
        assert await mock_num_port2.get_attr("display_name") == "value2"
        mock_num_port2.attr_get_display_name.assert_called_once_with()

        mock_num_port2._sync_getter = "value1"
        mocker.patch.object(mock_num_port2, "attr_get_sync_getter", return_value="value2")
        mock_num_port2.invalidate_attrs()
        assert await mock_num_port2.get_attr("sync_getter") == "value2"
        mock_num_port2.attr_get_sync_getter.assert_called_once_with()

        mock_num_port2._boolean_getter = False
        mocker.patch.object(mock_num_port2, "attr_is_boolean_getter", return_value=True)
        mock_num_port2.invalidate_attrs()
        assert await mock_num_port2.get_attr("boolean_getter") is True
        mock_num_port2.attr_is_boolean_getter.assert_called_once_with()

        mock_num_port2._sync_boolean_getter = False
        mocker.patch.object(mock_num_port2, "attr_is_sync_boolean_getter", return_value=True)
        mock_num_port2.invalidate_attrs()
        assert await mock_num_port2.get_attr("sync_boolean_getter") is True
        mock_num_port2.attr_is_sync_boolean_getter.assert_called_once_with()

    async def test_read_property(self, mock_num_port1, mocker):
        """Should return the value stored in the private property, when no getter is defined and attribute is not
        cached."""

        class TempMockPort(type(mock_num_port1)):
            async def attr_get_default_display_name(self) -> str:
                raise AssertionError("Should not be called")

        mock_num_port2 = TempMockPort("tmp", None)
        mock_num_port2._display_name = "value1"
        mock_num_port2.invalidate_attrs()
        mocker.patch.object(mock_num_port2, "attr_get_value", return_value="value2")
        assert await mock_num_port2.get_attr("display_name") == "value1"
        mock_num_port2.attr_get_value.assert_not_called()

    async def test_call_attr_default_getter(self, mock_num_port1, mocker):
        """Should call the attribute *default* getter method, in the absence of any other source."""

        class TempMockPort(type(mock_num_port1)):
            async def attr_get_default_display_name(self) -> str:
                return ""

            def attr_get_default_sync_getter(self) -> str:
                return ""

            async def attr_is_default_boolean_getter(self) -> bool:
                return True

            def attr_is_default_sync_boolean_getter(self) -> bool:
                return True

        mock_num_port2 = TempMockPort("tmp", None)
        mock_num_port2._display_name = None
        mocker.patch.object(mock_num_port2, "attr_get_default_display_name", return_value="value2")
        mock_num_port2.invalidate_attrs()
        assert await mock_num_port2.get_attr("display_name") == "value2"
        mock_num_port2.attr_get_default_display_name.assert_called_once_with()

        mocker.patch.object(mock_num_port2, "attr_get_default_sync_getter", return_value="value2")
        assert await mock_num_port2.get_attr("sync_getter") == "value2"
        mock_num_port2.attr_get_default_sync_getter.assert_called_once_with()

        mocker.patch.object(mock_num_port2, "attr_is_default_boolean_getter", return_value=True)
        assert await mock_num_port2.get_attr("boolean_getter") is True
        mock_num_port2.attr_is_default_boolean_getter.assert_called_once_with()

        mocker.patch.object(mock_num_port2, "attr_is_default_sync_boolean_getter", return_value=True)
        assert await mock_num_port2.get_attr("sync_boolean_getter") is True
        mock_num_port2.attr_is_default_sync_boolean_getter.assert_called_once_with()


class TestPortSetAttr:
    async def test_unknown_attribute(self, mock_num_port1, mocker):
        """Should silently do nothing for an unsupported/unknown attribute."""

        mocker.patch.object(mock_num_port1, "attr_set_value")
        mock_num_port1.attr_set_value.assert_not_called()
        assert not hasattr(mock_num_port1, "_unknown_attribute")

    async def test_unchanged_value(self, mock_num_port1, mocker):
        """Should not do anything if supplied value is the same as existent one."""

        await mock_num_port1.set_attr("display_name", "some name")  # initial value
        mocker.patch.object(mock_num_port1, "attr_set_value")
        await mock_num_port1.set_attr("display_name", "some name")  # same value, repeated
        mock_num_port1.attr_set_value.assert_not_called()

        class TempMockPort(type(mock_num_port1)):
            async def attr_set_display_name(self, value: str) -> None:
                self._display_name = value

        mock_num_port2 = TempMockPort("tmp", None)
        await mock_num_port2.set_attr("display_name", "some name")  # initial value
        mocker.patch.object(mock_num_port2, "attr_set_display_name")
        await mock_num_port2.set_attr("display_name", "some name")  # same value
        mock_num_port2.attr_set_display_name.assert_not_called()

    async def test_unmodifiable(self, mock_num_port1):
        """Should not fail for an unmodifiable attribute, as the modifiable flag is handled elsewhere."""

        await mock_num_port1.set_attr("type", "inexistent-type")

    async def test_call_setter(self, mock_num_port1, mocker):
        """Should call the attribute setter method instead of changing the private property or calling
        `attr_set_value()`."""

        class TempMockPort(type(mock_num_port1)):
            async def attr_set_my_attribute(self, value: str) -> None:
                pass

        mock_num_port2 = TempMockPort("tmp", None)
        mock_num_port2._my_attribute = "value1"
        mocker.patch.object(mock_num_port2, "attr_set_value")
        mocker.patch.object(mock_num_port2, "attr_set_my_attribute")
        await mock_num_port2.set_attr("my_attribute", "value2")
        mock_num_port2.attr_set_value.assert_not_called()
        assert mock_num_port2._my_attribute == "value1"
        mock_num_port2.attr_set_my_attribute.assert_called_once_with("value2")

    async def test_assign_property(self, mock_num_port1, mocker):
        """Should assign private property instead of calling `attr_set_value()`."""

        mock_num_port1._my_attribute = "value1"
        mocker.patch.object(mock_num_port1, "attr_set_value")
        await mock_num_port1.set_attr("my_attribute", "value2")
        mock_num_port1.attr_set_value.assert_not_called()
        assert mock_num_port1._my_attribute == "value2"

    async def test_call_attr_set_value(self, mock_num_port1, mocker):
        """Should call `attr_set_value()`, since there's no dedicated attribute setter, nor a private property."""

        class TempMockPort(type(mock_num_port1)):
            async def attr_get_my_attribute(self) -> str:
                return "value1"

        mock_num_port2 = TempMockPort("tmp", None)
        mocker.patch.object(mock_num_port2, "attr_set_value")
        await mock_num_port2.set_attr("my_attribute", "value2")
        mock_num_port2.attr_set_value.assert_called_once_with("my_attribute", "value2")

    async def test_invalidate_cache(self, mock_num_port1, mocker):
        """Should invalidate attribute cache as well as attribute definitions cache."""

        mock_num_port1._my_attribute = "value1"
        mocker.patch.object(mock_num_port1, "invalidate_attrdefs")
        await mock_num_port1.set_attr("my_attribute", "value2")
        mock_num_port1.invalidate_attrdefs.assert_called_once()

    async def test_call_handle_attr_change(self, mock_num_port1, mocker):
        """Should call the `handle_attr_change` method."""

        mock_num_port1._my_attribute = "value1"
        mocker.patch.object(mock_num_port1, "handle_attr_change")
        await mock_num_port1.set_attr("my_attribute", "value2")
        await asyncio.sleep(0.1)
        mock_num_port1.handle_attr_change.assert_called_once_with("my_attribute", "value2")


class TestPortToJSON:
    async def test_definitions_filtered(self, mock_num_port1, mocker):
        """Should strip private (`_`-prefixed) fields and `pattern` from additional attrdefs in the result."""

        mocker.patch.object(
            mock_num_port1,
            "get_additional_attrdefs",
            return_value={
                "extra_attr": {
                    "type": "string",
                    "modifiable": True,
                    "pattern": "^.*$",
                    "_internal": "should_be_removed",
                },
            },
        )
        mock_num_port1._to_json_attrdefs_cache = None

        result = await mock_num_port1.to_json()

        assert "definitions" in result
        assert result["definitions"] == {
            "extra_attr": {
                "type": "string",
                "modifiable": True,
            },
        }

    async def test_additional_attrdefs_cached(self, mock_num_port1, mocker):
        """Should compute filtered additional attrdefs only once; subsequent calls reuse the cached object."""

        mocker.patch.object(
            mock_num_port1,
            "get_additional_attrdefs",
            return_value={
                "extra_attr": {
                    "type": "string",
                    "modifiable": True,
                    "pattern": "^.*$",
                },
            },
        )
        mock_num_port1._to_json_attrdefs_cache = None

        result1 = await mock_num_port1.to_json()
        result2 = await mock_num_port1.to_json()

        assert result1["definitions"] is result2["definitions"]
        mock_num_port1.get_additional_attrdefs.assert_called_once()

    async def test_invalidate_attrdefs_clears_cache(self, mock_num_port1, mocker):
        """Should recompute additional attrdefs after `invalidate_attrdefs()` is called."""

        call_count = 0
        attrdefs_versions = [
            {"extra_attr": {"type": "string", "modifiable": True}},
            {"extra_attr": {"type": "number", "modifiable": False}},
        ]

        async def get_additional_attrdefs():
            nonlocal call_count
            r = attrdefs_versions[min(call_count, 1)]
            call_count += 1
            return r

        mocker.patch.object(mock_num_port1, "get_additional_attrdefs", side_effect=get_additional_attrdefs)
        mock_num_port1._to_json_attrdefs_cache = None

        result1 = await mock_num_port1.to_json()
        mock_num_port1.invalidate_attrdefs()
        result2 = await mock_num_port1.to_json()

        assert result1["definitions"]["extra_attr"]["type"] == "string"
        assert result2["definitions"]["extra_attr"]["type"] == "number"
        assert result1["definitions"] is not result2["definitions"]


class TestLoadIter:
    async def test_yields_each_port_after_load(self, mocker):
        """Should yield each port after it's loaded (after port.load() is called)."""
        from qtoggleserver.core import ports as core_ports
        from tests.unit.qtoggleserver.mock.ports import MockBooleanPort, MockNumberPort

        mocker.patch("asyncio.Lock")

        port_args = [
            {"driver": MockBooleanPort, "port_id": "test_bool1", "value": True},
            {"driver": MockNumberPort, "port_id": "test_num1", "value": 42},
            {"driver": MockBooleanPort, "port_id": "test_bool2", "value": False},
        ]

        # Track when ports are loaded and yielded
        loaded_ports = []
        load_calls = []

        original_load = MockBooleanPort.load

        async def mock_load(self):
            load_calls.append(self.get_id())
            return await original_load(self)

        mocker.patch.object(MockBooleanPort, "load", side_effect=mock_load, autospec=True)
        mocker.patch.object(MockNumberPort, "load", side_effect=mock_load, autospec=True)

        async for port in core_ports.load_iter(port_args, trigger_add=False):
            loaded_ports.append(port.get_id())
            # At this point, port.load() should have been called for this port
            assert port.get_id() in load_calls

        # Verify all ports were yielded in order
        assert loaded_ports == ["test_bool1", "test_num1", "test_bool2"]

        # Clean up
        for port_id in ["test_bool1", "test_num1", "test_bool2"]:
            port = core_ports.get(port_id)
            if port:
                await port.remove(persisted_data=False)

    async def test_handles_port_mapping(self, mocker):
        """Should properly handle port ID mapping and yield with mapped IDs."""
        from qtoggleserver.conf import settings
        from qtoggleserver.core import ports as core_ports
        from tests.unit.qtoggleserver.mock.ports import MockNumberPort

        mocker.patch("asyncio.Lock")

        # Set up port mapping
        original_mappings = settings.port_mappings.copy()
        settings.port_mappings["test_map1"] = "mapped1"

        port_args = [
            {"driver": MockNumberPort, "port_id": "test_map1", "value": 100},
        ]

        yielded_ports = []
        async for port in core_ports.load_iter(port_args, trigger_add=False):
            yielded_ports.append(port)

        # Should yield with mapped ID
        assert len(yielded_ports) == 1
        assert yielded_ports[0].get_id() == "mapped1"

        # Clean up
        settings.port_mappings = original_mappings
        port = core_ports.get("mapped1")
        if port:
            await port.remove(persisted_data=False)

    async def test_trigger_add_called_when_enabled(self, mocker):
        """Should call trigger_add on each port when trigger_add=True."""
        from qtoggleserver.core import ports as core_ports
        from tests.unit.qtoggleserver.mock.ports import MockBooleanPort

        mocker.patch("asyncio.Lock")

        port_args = [
            {"driver": MockBooleanPort, "port_id": "test_trigger1", "value": True},
            {"driver": MockBooleanPort, "port_id": "test_trigger2", "value": False},
        ]

        trigger_add_calls = []

        async def mock_trigger_add(self):
            trigger_add_calls.append(self.get_id())

        mocker.patch.object(MockBooleanPort, "trigger_add", side_effect=mock_trigger_add, autospec=True)

        async for port in core_ports.load_iter(port_args, trigger_add=True):
            pass

        # trigger_add should be called for both ports
        assert trigger_add_calls == ["test_trigger1", "test_trigger2"]

        # Clean up
        for port_id in ["test_trigger1", "test_trigger2"]:
            port = core_ports.get(port_id)
            if port:
                await port.remove(persisted_data=False)

    async def test_trigger_add_not_called_when_disabled(self, mocker):
        """Should not call trigger_add on each port when trigger_add=False."""
        from qtoggleserver.core import ports as core_ports
        from tests.unit.qtoggleserver.mock.ports import MockBooleanPort

        mocker.patch("asyncio.Lock")

        port_args = [
            {"driver": MockBooleanPort, "port_id": "test_notrigger1", "value": True},
        ]

        trigger_add_mock = mocker.patch.object(MockBooleanPort, "trigger_add", autospec=True)

        async for port in core_ports.load_iter(port_args, trigger_add=False):
            pass

        # trigger_add should NOT be called
        trigger_add_mock.assert_not_called()

        # Clean up
        port = core_ports.get("test_notrigger1")
        if port:
            await port.remove(persisted_data=False)


class TestLoad:
    async def test_basic_call(self, mocker):
        """Should load given port."""
        from qtoggleserver.core import ports as core_ports
        from tests.unit.qtoggleserver.mock.ports import MockBooleanPort

        mocker.patch("asyncio.Lock")

        # This is how existing code uses load()
        port_args = [{"driver": MockBooleanPort, "port_id": "test_compat1", "value": False}]
        ports = await core_ports.load(port_args, trigger_add=False)

        assert isinstance(ports, list)
        assert len(ports) == 1
        assert ports[0].get_id() == "test_compat1"

        # Clean up
        for port in ports:
            await port.remove(persisted_data=False)

    async def test_returns_all_ports_after_completion(self, mocker):
        """Should return all loaded ports in a list after completion."""
        from qtoggleserver.core import ports as core_ports
        from tests.unit.qtoggleserver.mock.ports import MockBooleanPort, MockNumberPort

        mocker.patch("asyncio.Lock")

        port_args = [
            {"driver": MockBooleanPort, "port_id": "test_load1", "value": True},
            {"driver": MockNumberPort, "port_id": "test_load2", "value": 99},
        ]

        ports = await core_ports.load(port_args, trigger_add=False)

        # Should return a list with all ports
        assert len(ports) == 2
        assert ports[0].get_id() == "test_load1"
        assert ports[1].get_id() == "test_load2"

        # Clean up
        for port in ports:
            await port.remove(persisted_data=False)


class TestPortToPersisted:
    async def test_includes_id_and_history_timestamp(self, mock_num_port1):
        """to_persisted should always include id and history_last_timestamp."""
        mock_num_port1._history_last_timestamp = 123456

        result = await mock_num_port1.to_persisted()

        assert result["id"] == "nid1"
        assert result["history_last_timestamp"] == 123456

    async def test_includes_value_when_persisted(self, mock_num_port1, mocker):
        """to_persisted should include value when port is persisted."""
        mocker.patch.object(mock_num_port1, "is_persisted", return_value=True)
        mock_num_port1._last_read_value = (42, 1234567890)

        result = await mock_num_port1.to_persisted()

        assert result["value"] == 42

    async def test_value_none_when_not_persisted(self, mock_num_port1, mocker):
        """to_persisted should set value to None when port is not persisted."""
        mocker.patch.object(mock_num_port1, "is_persisted", return_value=False)
        mock_num_port1._last_read_value = (42, 1234567890)

        result = await mock_num_port1.to_persisted()

        assert result["value"] is None

    async def test_value_none_when_no_last_read_value(self, mock_num_port1, mocker):
        """to_persisted should set value to None when no last_read_value."""
        mocker.patch.object(mock_num_port1, "is_persisted", return_value=True)
        mock_num_port1._last_read_value = None

        result = await mock_num_port1.to_persisted()

        assert result["value"] is None

    async def test_includes_modifiable_attrs(self, mock_num_port1, mocker):
        """to_persisted should include all modifiable attributes."""
        mocker.patch.object(mock_num_port1, "is_persisted", return_value=False)
        mocker.patch.object(mock_num_port1, "get_modifiable_attrs", return_value=["display_name", "unit", "enabled"])

        # Mock get_attr to return test values
        async def mock_get_attr(name):
            if name == "display_name":
                return "Test Port"
            elif name == "unit":
                return "V"
            elif name == "enabled":
                return True
            return None

        mocker.patch.object(mock_num_port1, "get_attr", side_effect=mock_get_attr)

        result = await mock_num_port1.to_persisted()

        assert result["display_name"] == "Test Port"
        assert result["unit"] == "V"
        assert result["enabled"] is True

    async def test_skips_none_attrs(self, mock_num_port1, mocker):
        """to_persisted should skip attributes that are None."""
        mocker.patch.object(mock_num_port1, "is_persisted", return_value=False)
        mocker.patch.object(mock_num_port1, "get_modifiable_attrs", return_value=["display_name", "unit"])

        # Mock get_attr to return None for 'unit'
        async def mock_get_attr(name):
            if name == "display_name":
                return "Test Port"
            elif name == "unit":
                return None
            return None

        mocker.patch.object(mock_num_port1, "get_attr", side_effect=mock_get_attr)

        result = await mock_num_port1.to_persisted()

        assert result["display_name"] == "Test Port"
        assert "unit" not in result
