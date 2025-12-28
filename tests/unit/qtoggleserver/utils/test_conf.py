import pytest

from qtoggleserver.utils.conf import DottedDict


class TestDottedDict:
    def test_getitem_simple_key(self):
        """Should retrieve value using a simple (non-dotted) key."""
        d = DottedDict({"key": "value"})
        assert d["key"] == "value"

    def test_getitem_nonexistent_simple_key(self):
        """Should raise KeyError when accessing a non-existent simple key."""
        d = DottedDict()
        with pytest.raises(KeyError):
            _ = d["nonexistent"]

    def test_getitem_dotted_key_single_level(self):
        """Should retrieve nested value using a single-level dotted key."""
        d = DottedDict({"parent": DottedDict({"child": "value"})})
        assert d["parent.child"] == "value"

    def test_getitem_dotted_key_multiple_levels(self):
        """Should retrieve deeply nested value using a multi-level dotted key."""
        d = DottedDict({"level1": DottedDict({"level2": DottedDict({"level3": "deep_value"})})})
        assert d["level1.level2.level3"] == "deep_value"

    def test_getitem_dotted_key_missing_parent(self):
        """Should raise KeyError when a parent segment in the dotted path doesn't exist."""
        d = DottedDict({"parent": DottedDict()})
        with pytest.raises(KeyError, match="Missing path segment: nonexistent"):
            _ = d["nonexistent.child"]

    def test_getitem_dotted_key_parent_not_dict(self):
        """Should raise KeyError when a parent segment in the dotted path is not a DottedDict."""
        d = DottedDict({"parent": "not_a_dict"})
        with pytest.raises(KeyError, match="Missing path segment: parent"):
            _ = d["parent.child"]

    def test_getitem_dotted_key_missing_leaf(self):
        """Should raise KeyError when the leaf key doesn't exist in the parent dict."""
        d = DottedDict({"parent": DottedDict({"other": "value"})})
        with pytest.raises(KeyError, match="child"):
            _ = d["parent.child"]

    def test_setitem_simple_key(self):
        """Should set value using a simple (non-dotted) key."""
        d = DottedDict()
        d["key"] = "value"
        assert d["key"] == "value"

    def test_setitem_dotted_key_creates_intermediate_dicts(self):
        """Should automatically create intermediate DottedDict instances when setting a dotted key."""
        d = DottedDict()
        d["parent.child"] = "value"
        assert isinstance(d["parent"], DottedDict)
        assert d["parent"]["child"] == "value"
        assert d["parent.child"] == "value"

    def test_setitem_dotted_key_multiple_levels(self):
        """Should create multiple intermediate DottedDict levels when setting a deeply nested key."""
        d = DottedDict()
        d["level1.level2.level3"] = "deep_value"
        assert isinstance(d["level1"], DottedDict)
        assert isinstance(d["level1"]["level2"], DottedDict)
        assert d["level1.level2.level3"] == "deep_value"

    def test_setitem_dotted_key_existing_parent(self):
        """Should set value in an existing parent DottedDict without replacing it."""
        d = DottedDict({"parent": DottedDict({"existing": "old_value"})})
        d["parent.new"] = "new_value"
        assert d["parent.existing"] == "old_value"
        assert d["parent.new"] == "new_value"

    def test_setitem_dotted_key_overwrite_non_dict_raises(self):
        """Should raise ValueError when trying to traverse through a non-dict value."""
        d = DottedDict({"parent": "not_a_dict"})
        with pytest.raises(ValueError, match="Cannot traverse through non-dict value at key 'parent'"):
            d["parent.child"] = "value"

    def test_setitem_dotted_key_replaces_leaf(self):
        """Should replace an existing leaf value when setting with a dotted key."""
        d = DottedDict({"parent": DottedDict({"child": "old_value"})})
        d["parent.child"] = "new_value"
        assert d["parent.child"] == "new_value"

    def test_get_existing_simple_key(self):
        """Should return value for an existing simple key using get()."""
        d = DottedDict({"key": "value"})
        assert d.get("key") == "value"

    def test_get_nonexistent_simple_key_returns_none(self):
        """Should return None for a non-existent simple key using get()."""
        d = DottedDict()
        assert d.get("nonexistent") is None

    def test_get_nonexistent_key_with_default(self):
        """Should return the specified default value for a non-existent key using get()."""
        d = DottedDict()
        assert d.get("nonexistent", "default") == "default"

    def test_get_existing_dotted_key(self):
        """Should return value for an existing dotted key using get()."""
        d = DottedDict({"parent": DottedDict({"child": "value"})})
        assert d.get("parent.child") == "value"

    def test_get_nonexistent_dotted_key_returns_none(self):
        """Should return None for a non-existent dotted key using get()."""
        d = DottedDict({"parent": DottedDict()})
        assert d.get("parent.nonexistent") is None

    def test_get_nonexistent_dotted_key_with_default(self):
        """Should return the specified default value for a non-existent dotted key using get()."""
        d = DottedDict({"parent": DottedDict()})
        assert d.get("parent.nonexistent", "default") == "default"

    def test_get_dotted_key_missing_parent_returns_default(self):
        """Should return default when a parent segment in dotted path doesn't exist using get()."""
        d = DottedDict()
        assert d.get("nonexistent.child", "default") == "default"

    def test_update_with_dict(self):
        """Should update DottedDict with key-value pairs from a regular dict."""
        d = DottedDict({"a": 1})
        d.update({"b": 2, "c": 3})
        assert d["a"] == 1
        assert d["b"] == 2
        assert d["c"] == 3

    def test_update_with_kwargs(self):
        """Should update DottedDict with keyword arguments."""
        d = DottedDict({"a": 1})
        d.update(b=2, c=3)
        assert d["a"] == 1
        assert d["b"] == 2
        assert d["c"] == 3

    def test_update_with_dict_and_kwargs(self):
        """Should update DottedDict with both a dict and keyword arguments."""
        d = DottedDict({"a": 1})
        d.update({"b": 2}, c=3)
        assert d["a"] == 1
        assert d["b"] == 2
        assert d["c"] == 3

    def test_update_with_dotted_keys(self):
        """Should support dotted keys in update operations."""
        d = DottedDict()
        d.update({"parent.child": "value"})
        assert d["parent.child"] == "value"
        assert isinstance(d["parent"], DottedDict)

    def test_update_overwrites_existing_values(self):
        """Should overwrite existing values when updating."""
        d = DottedDict({"a": 1, "b": 2})
        d.update({"b": 20, "c": 3})
        assert d["a"] == 1
        assert d["b"] == 20
        assert d["c"] == 3

    def test_mixed_access_simple_and_dotted(self):
        """Should allow mixing simple and dotted key access on the same DottedDict."""
        d = DottedDict()
        d["simple"] = "value1"
        d["parent.child"] = "value2"
        assert d["simple"] == "value1"
        assert d["parent"]["child"] == "value2"
        assert d["parent.child"] == "value2"

    def test_inheritance_from_dict(self):
        """Should properly inherit from dict and support standard dict operations."""
        d = DottedDict({"a": 1, "b": 2})
        assert len(d) == 2
        assert "a" in d
        assert "c" not in d
        assert list(d.keys()) == ["a", "b"]
        assert list(d.values()) == [1, 2]

    def test_nested_dotteddict_creation(self):
        """Should create nested DottedDict instances, not plain dicts."""
        d = DottedDict()
        d["a.b.c"] = "value"
        assert isinstance(d["a"], DottedDict)
        assert isinstance(d["a"]["b"], DottedDict)

    def test_separator_constant(self):
        """Should use dot as the separator constant."""
        assert DottedDict.SEP == "."

    def test_empty_dotteddict(self):
        """Should handle empty DottedDict creation."""
        d = DottedDict()
        assert len(d) == 0
        assert list(d.keys()) == []

    def test_complex_nested_structure(self):
        """Should handle complex nested structures with multiple branches."""
        d = DottedDict()
        d["app.database.host"] = "localhost"
        d["app.database.port"] = 5432
        d["app.cache.enabled"] = True
        d["app.cache.ttl"] = 300
        d["logging.level"] = "INFO"

        assert d["app.database.host"] == "localhost"
        assert d["app.database.port"] == 5432
        assert d["app.cache.enabled"] is True
        assert d["app.cache.ttl"] == 300
        assert d["logging.level"] == "INFO"

        assert isinstance(d["app"], DottedDict)
        assert isinstance(d["app"]["database"], DottedDict)
        assert isinstance(d["app"]["cache"], DottedDict)
        assert isinstance(d["logging"], DottedDict)
