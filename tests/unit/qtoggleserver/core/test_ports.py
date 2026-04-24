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
