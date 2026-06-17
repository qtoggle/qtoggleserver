from qtoggleserver.utils.misc import deep_update


class TestDeepUpdate:
    def test_merges_nested_dicts(self):
        """Should recursively merge nested dictionaries and keep unrelated keys."""

        dst = {"a": {"b": 1}, "c": 2}
        src = {"a": {"d": 3}, "e": 4}

        result = deep_update(dst, src)

        assert result is dst
        assert dst == {"a": {"b": 1, "d": 3}, "c": 2, "e": 4}

    def test_overwrites_non_dict_values(self):
        """Should replace existing values when either side is not a dict."""

        dst = {"a": {"b": 1}, "c": 2}
        src = {"a": "replaced", "c": {"d": 3}}

        deep_update(dst, src)

        assert dst == {"a": "replaced", "c": {"d": 3}}
