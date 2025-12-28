import types

from collections import OrderedDict
from typing import Any

import pyhocon


_config_factory = pyhocon.ConfigFactory()


class DottedDict(dict):
    """
    DottedDict is a dictionary subclass that supports accessing nested dictionary values using dot-separated keys
    (e.g., "parent.child.value"). It automatically creates intermediate DottedDict instances when setting nested values.
    """

    SEP = "."

    def __getitem__(self, key: str) -> Any:
        if isinstance(key, str) and self.SEP in key:
            *parents, leaf = key.split(self.SEP)
            d = self
            for part in parents:
                if part not in d or not isinstance(d[part], DottedDict):
                    raise KeyError(f"Missing path segment: {part}")
                d = d[part]
            if leaf not in d:
                raise KeyError(leaf)
            return d[leaf]
        return super().__getitem__(key)

    def __setitem__(self, key: str, value: Any) -> None:
        if isinstance(key, str) and self.SEP in key:
            *parents, leaf = key.split(self.SEP)
            d = self
            for part in parents:
                if part not in d:
                    d[part] = DottedDict()  # Use subclass for recursion
                elif not isinstance(d[part], DottedDict):
                    raise ValueError(f"Cannot traverse through non-dict value at key '{part}'")
                d = d[part]
            d[leaf] = value
        else:
            super().__setitem__(key, value)

    def get(self, key: str, default: Any = None) -> Any:
        try:
            return self[key]
        except KeyError:
            return default

    def update(self, other: dict = None, **kwargs) -> None:
        if other is None:
            other = {}

        # Emulate dict.update semantics:
        # - if 'other' is a mapping (has 'keys'), update from its keys
        # - otherwise, expect an iterable of (key, value) pairs
        if hasattr(other, "keys"):
            for k in other:
                self[k] = other[k]
        else:
            for k, v in other:
                self[k] = v
        for k, v in kwargs.items():
            self[k] = v


def obj_to_dict(obj: Any) -> dict[str, Any]:
    d = {}
    for k, v in obj.__dict__.items():
        if k.startswith("__") or isinstance(v, types.ModuleType):
            continue

        if isinstance(v, type):
            v = obj_to_dict(v)

        d[k] = v

    return d


def update_obj_from_dict(obj: Any, d: OrderedDict) -> None:
    for k, v in d.items():
        ov = getattr(obj, k, None)
        if isinstance(ov, type):
            update_obj_from_dict(ov, v)
        elif isinstance(ov, types.ModuleType):
            continue
        else:
            setattr(obj, k, v)


def config_from_file(file: str) -> pyhocon.ConfigTree:
    return _config_factory.parse_file(file)


def config_from_dict(d: dict[str, Any]) -> pyhocon.ConfigTree:
    return _config_factory.from_dict(d)


def config_to_str(config: pyhocon.ConfigTree) -> str:
    return pyhocon.HOCONConverter.to_hocon(config, indent=4, compact=False)


def config_to_dict(config: pyhocon.ConfigTree) -> OrderedDict:
    return config.as_plain_ordered_dict()


def config_merge(config1: pyhocon.ConfigTree, config2: pyhocon.ConfigTree) -> pyhocon.ConfigTree:
    return pyhocon.ConfigTree.merge_configs(config1, config2)
