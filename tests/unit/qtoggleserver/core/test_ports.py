class TestPortGetLastValue:
    def test_pending(self, mock_num_port1):
        """Should return the pending value, since it's not None."""

        mock_num_port1._pending_value = 100
        mock_num_port1._last_written_value = None
        mock_num_port1._last_read_value = None
        assert mock_num_port1.get_last_value() == 100

        mock_num_port1._last_written_value = (200, 2000)
        mock_num_port1._last_read_value = (300, 1000)
        assert mock_num_port1.get_last_value() == 100

    def test_last_written(self, mock_num_port1):
        """Should return the last written value."""

        mock_num_port1._pending_value = None
        mock_num_port1._last_written_value = (200, 2000)
        mock_num_port1._last_read_value = None
        assert mock_num_port1.get_last_value() == 200

        mock_num_port1._last_read_value = (300, 1000)  # older timestamp
        assert mock_num_port1.get_last_value() == 200

    def test_last_read(self, mock_num_port1):
        """Should return the last read value."""

        mock_num_port1._pending_value = None
        mock_num_port1._last_written_value = None
        mock_num_port1._last_read_value = (300, 2000)
        assert mock_num_port1.get_last_value() == 300

        mock_num_port1._last_written_value = (200, 1000)  # newer timestamp
        assert mock_num_port1.get_last_value() == 300


class TestPortPushEval:
    def test(self, mock_num_port1, mock_num_port2, mocker):
        """Should schedule an expression evaluation. Should gather all ports using `core.ports.get_all()` and call
        `get_last_value()` on each of them to build the eval context."""

        mocker.patch("qtoggleserver.core.ports.get_all", return_value=[mock_num_port1, mock_num_port2])
        mocker.patch.object(mock_num_port1, "_make_eval_context", return_value="dummy_eval_context")
        mocker.patch.object(mock_num_port1, "get_last_value", return_value=42)
        mocker.patch.object(mock_num_port2, "get_last_value", return_value=84)
        mocker.patch.object(mock_num_port1._eval_queue, "put_nowait")

        mock_num_port1.push_eval(1234)

        mock_num_port1._make_eval_context.assert_called_once_with({"nid1": 42, "nid2": 84}, 1234)
        mock_num_port1._eval_queue.put_nowait.assert_called_once_with("dummy_eval_context")


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
        assert mock_num_port1._attrs_cache.get("my_attribute") != "value1"
        mock_num_port1.invalidate_attrdefs.assert_called_once()

    async def test_call_handle_attr_change(self, mock_num_port1, mocker):
        """Should call the `handle_attr_change` method."""

        mock_num_port1._my_attribute = "value1"
        mocker.patch.object(mock_num_port1, "handle_attr_change")
        await mock_num_port1.set_attr("my_attribute", "value2")
        mock_num_port1.handle_attr_change.assert_called_once_with("my_attribute", "value2")
