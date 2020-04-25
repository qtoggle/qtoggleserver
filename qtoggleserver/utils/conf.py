
import types

from collections import OrderedDict
from typing import Any, Dict

import pyhocon


_config_factory = pyhocon.ConfigFactory()


def obj_to_dict(obj: Any) -> Dict[str, Any]:
    d = {}
    for k, v in obj.__dict__.items():
        if k.startswith('__') or isinstance(v, types.ModuleType):
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


def config_from_dict(d: Dict[str, Any]) -> pyhocon.ConfigTree:
    return _config_factory.from_dict(d)


def config_to_dict(config: pyhocon.ConfigTree) -> OrderedDict:
    return config.as_plain_ordered_dict()


def config_merge(config1: pyhocon.ConfigTree, config2: pyhocon.ConfigTree) -> pyhocon.ConfigTree:
    return pyhocon.ConfigTree.merge_configs(config1, config2)
