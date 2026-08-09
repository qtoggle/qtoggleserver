import math

from datetime import date, datetime

import pytest

from qtoggleserver.utils import json as json_utils


class UnserializableClass:
    """A class that cannot be serialized to JSON by default."""

    def __init__(self, value: str) -> None:
        self.value = value

    def __str__(self) -> str:
        return f"UnserializableClass({self.value})"

    def __repr__(self) -> str:
        return self.__str__()


class TestDumps:
    """Test json_utils.dumps() with various extra_types modes."""

    def test_primitives(self) -> None:
        """Test serialization of primitive types (fast path)."""
        assert json_utils.dumps("hello") == '"hello"'
        assert json_utils.dumps(True) == "true"
        assert json_utils.dumps(False) == "false"
        assert json_utils.dumps(42) == "42"
        assert json_utils.dumps(3.14) == "3.14"
        assert json_utils.dumps(None) == "null"

    def test_nan_inf_primitives_none_mode(self) -> None:
        """Test that NaN and Infinity primitives are converted to null in NONE mode."""
        assert json_utils.dumps(math.nan) == "null"
        assert json_utils.dumps(math.inf) == "null"
        assert json_utils.dumps(-math.inf) == "null"
        assert json_utils.dumps(math.nan, extra_types=json_utils.ExtraTypes.NONE) == "null"

    def test_nan_inf_primitives_extended_mode(self) -> None:
        """Test that NaN and Infinity primitives are preserved in EXTENDED mode."""
        assert json_utils.dumps(math.nan, extra_types=json_utils.ExtraTypes.EXTENDED) == "NaN"
        assert json_utils.dumps(math.inf, extra_types=json_utils.ExtraTypes.EXTENDED) == "Infinity"
        assert json_utils.dumps(-math.inf, extra_types=json_utils.ExtraTypes.EXTENDED) == "-Infinity"

    def test_nan_inf_primitives_str_mode(self) -> None:
        """Test that NaN and Infinity primitives are preserved in STR mode."""
        assert json_utils.dumps(math.nan, extra_types=json_utils.ExtraTypes.STR) == "NaN"
        assert json_utils.dumps(math.inf, extra_types=json_utils.ExtraTypes.STR) == "Infinity"
        assert json_utils.dumps(-math.inf, extra_types=json_utils.ExtraTypes.STR) == "-Infinity"

    def test_nan_inf_in_collections_none_mode(self) -> None:
        """Test that NaN and Infinity in collections are replaced with null in NONE mode."""
        result = json_utils.dumps({"value": math.nan})
        assert result == '{"value": null}'

        result = json_utils.dumps([1, math.inf, 3])
        assert result == "[1, null, 3]"

    def test_nan_inf_in_collections_extended_mode(self) -> None:
        """Test that NaN and Infinity in collections are preserved in EXTENDED mode."""
        result = json_utils.dumps({"value": math.nan}, extra_types=json_utils.ExtraTypes.EXTENDED)
        assert result == '{"value": NaN}'

        result = json_utils.dumps([1, math.inf, 3], extra_types=json_utils.ExtraTypes.EXTENDED)
        assert result == "[1, Infinity, 3]"

    def test_nan_inf_in_collections_str_mode(self) -> None:
        """Test that NaN and Infinity in collections are preserved in STR mode."""
        result = json_utils.dumps({"value": math.nan}, extra_types=json_utils.ExtraTypes.STR)
        assert result == '{"value": NaN}'

        result = json_utils.dumps([1, -math.inf, 3], extra_types=json_utils.ExtraTypes.STR)
        assert result == "[1, -Infinity, 3]"

    def test_standard_json(self) -> None:
        """Test standard JSON serialization (no extra types)."""
        data = {"key": "value", "list": [1, 2, 3], "nested": {"a": 1}}
        result = json_utils.dumps(data)
        assert '"key": "value"' in result
        assert '"list": [1, 2, 3]' in result

    def test_date_datetime_none_mode_fails(self) -> None:
        """Test that date/datetime raise TypeError in NONE mode."""
        with pytest.raises(TypeError):
            json_utils.dumps({"date": date(2024, 1, 1)})

        with pytest.raises(TypeError):
            json_utils.dumps({"datetime": datetime(2024, 1, 1, 12, 30)})

    def test_date_datetime_iso_mode(self) -> None:
        """Test date/datetime serialization in ISO mode."""
        result = json_utils.dumps(
            {"date": date(2024, 1, 15), "datetime": datetime(2024, 1, 15, 14, 30, 45)},
            extra_types=json_utils.ExtraTypes.ISO,
        )
        assert '"date": "2024-01-15"' in result
        assert '"datetime": "2024-01-15T14:30:45Z"' in result

    def test_date_datetime_extended_mode(self) -> None:
        """Test date/datetime serialization in EXTENDED mode with type markers."""
        result = json_utils.dumps(
            {"date": date(2024, 1, 15)},
            extra_types=json_utils.ExtraTypes.EXTENDED,
        )
        assert '"__t": "__d"' in result
        assert '"__v": "2024-01-15"' in result

    def test_set_tuple_conversion(self) -> None:
        """Test that sets and tuples are converted to lists."""
        result = json_utils.dumps(
            {"set": {1, 2, 3}, "tuple": (4, 5, 6)},
            extra_types=json_utils.ExtraTypes.ISO,
        )
        # Parse back and compare as sets since set order is not guaranteed
        parsed = json_utils.loads(result)
        assert set(parsed["set"]) == {1, 2, 3}
        assert parsed["tuple"] == [4, 5, 6]  # Tuples preserve order

    def test_unserializable_str_mode(self) -> None:
        """Test that unserializable objects are converted to strings in STR mode."""
        obj = UnserializableClass("test_value")
        result = json_utils.dumps({"obj": obj}, extra_types=json_utils.ExtraTypes.STR)
        assert "UnserializableClass(test_value)" in result

    def test_unserializable_none_mode_fails(self) -> None:
        """Test that unserializable objects raise TypeError in NONE mode."""
        obj = UnserializableClass("test_value")
        with pytest.raises(TypeError):
            json_utils.dumps({"obj": obj})


class TestLoads:
    """Test json_utils.loads() with various extra_types modes."""

    def test_primitives(self) -> None:
        """Test deserialization of primitive types."""
        assert json_utils.loads('"hello"') == "hello"
        assert json_utils.loads("true") is True
        assert json_utils.loads("false") is False
        assert json_utils.loads("42") == 42
        assert json_utils.loads("3.14") == 3.14
        assert json_utils.loads("null") is None

    def test_standard_json(self) -> None:
        """Test standard JSON deserialization."""
        data = '{"key": "value", "list": [1, 2, 3]}'
        result = json_utils.loads(data)
        assert result == {"key": "value", "list": [1, 2, 3]}

    def test_date_datetime_iso_mode(self) -> None:
        """Test date/datetime deserialization in ISO mode."""
        data = '{"date": "2024-01-15", "datetime": "2024-01-15T14:30:45Z"}'
        result = json_utils.loads(data, extra_types=json_utils.ExtraTypes.ISO)
        assert result["date"] == date(2024, 1, 15)
        assert result["datetime"] == datetime(2024, 1, 15, 14, 30, 45)

    def test_date_datetime_extended_mode(self) -> None:
        """Test date/datetime deserialization in EXTENDED mode."""
        data = '{"date": {"__t": "__d", "__v": "2024-01-15"}}'
        result = json_utils.loads(data, extra_types=json_utils.ExtraTypes.EXTENDED)
        assert result["date"] == date(2024, 1, 15)

    def test_roundtrip_iso(self) -> None:
        """Test roundtrip serialization/deserialization in ISO mode."""
        original = {"date": date(2024, 1, 15), "datetime": datetime(2024, 1, 15, 14, 30, 45), "value": 42}
        serialized = json_utils.dumps(original, extra_types=json_utils.ExtraTypes.ISO)
        deserialized = json_utils.loads(serialized, extra_types=json_utils.ExtraTypes.ISO)
        assert deserialized == original

    def test_roundtrip_extended(self) -> None:
        """Test roundtrip serialization/deserialization in EXTENDED mode."""
        original = {"date": date(2024, 1, 15), "datetime": datetime(2024, 1, 15, 14, 30, 45, 123456)}
        serialized = json_utils.dumps(original, extra_types=json_utils.ExtraTypes.EXTENDED)
        deserialized = json_utils.loads(serialized, extra_types=json_utils.ExtraTypes.EXTENDED)
        assert deserialized == original


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_nested_nan_inf_replacement_none_mode(self) -> None:
        """Test that deeply nested NaN/Inf values are replaced in NONE mode."""
        data = {"level1": {"level2": {"value": math.nan, "list": [1, math.inf, 3]}}}
        result = json_utils.dumps(data)
        assert "null" in result
        assert "NaN" not in result
        assert "Infinity" not in result

    def test_nested_nan_inf_preserved_extended_mode(self) -> None:
        """Test that deeply nested NaN/Inf values are preserved in EXTENDED mode."""
        data = {"level1": {"level2": {"value": math.nan, "list": [1, math.inf, 3]}}}
        result = json_utils.dumps(data, extra_types=json_utils.ExtraTypes.EXTENDED)
        assert "NaN" in result
        assert "Infinity" in result
        assert "null" not in result or '"null"' in result  # Allow literal null strings in keys/values

    def test_complex_unserializable_object(self) -> None:
        """Test serialization of complex nested structures with unserializable objects."""

        class ComplexClass:
            def __init__(self) -> None:
                self.nested = UnserializableClass("nested")

            def __str__(self) -> str:
                return f"ComplexClass(nested={self.nested})"

        data = {"obj": ComplexClass(), "list": [1, UnserializableClass("in_list"), 3]}
        result = json_utils.dumps(data, extra_types=json_utils.ExtraTypes.STR)
        assert "ComplexClass" in result
        assert "UnserializableClass" in result

    def test_str_mode_not_roundtrippable(self) -> None:
        """Verify that STR mode is not suitable for roundtrip (objects become strings)."""
        obj = UnserializableClass("test")
        serialized = json_utils.dumps({"obj": obj}, extra_types=json_utils.ExtraTypes.STR)
        deserialized = json_utils.loads(serialized)

        # The deserialized value is a string, not the original object
        assert isinstance(deserialized["obj"], str)
        assert deserialized["obj"] == "UnserializableClass(test)"
