import sys

from typing import Any


class DynloadError(Exception):
    pass


class NoSuchModule(DynloadError):
    pass


class NoSuchAttribute(DynloadError):
    pass


def load_attr(attr_path: str) -> Any:
    m, attr = attr_path.rsplit(".", 1)

    try:
        __import__(m)
        mod = sys.modules[m]
    except ImportError as e:
        raise NoSuchModule(f"Error importing {attr_path}: {e}") from e

    try:
        attr = getattr(mod, attr)
    except AttributeError as e:
        raise NoSuchAttribute(f"Error importing {attr_path}: {e}") from e

    return attr
