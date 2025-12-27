import copy
import logging

from typing import Any

from qtoggleserver.conf import settings
from qtoggleserver.utils import json as json_utils
from qtoggleserver.utils.cmd import run_get_cmd
from qtoggleserver.utils.conf import DottedDict


logger = logging.getLogger(__name__)

_metadata_entries: DottedDict = DottedDict()


def get(key: str, default: Any = None) -> Any:
    return _metadata_entries.get(key, default)


def get_all() -> DottedDict:
    return copy.deepcopy(_metadata_entries)


async def load_metadata(params: dict) -> None:
    try:
        name = params["name"]
    except KeyError:
        raise ValueError("Missing 'name' parameter")

    value = params.get("value")
    cmd = params.get("cmd")
    if value is not None:
        pass
    elif cmd:
        result = run_get_cmd(cmd, f"metadata {name}", required_fields=["value"])
        value = result["value"]
    else:
        raise ValueError("Missing 'value' or 'cmd' parameter")

    sensitive = params.get("sensitive")
    if sensitive:
        logger.debug("loaded metadata %s", name)
    else:
        logger.debug("loaded metadata %s = %s", name, json_utils.dumps(value))

    _metadata_entries[name] = value


async def init() -> None:
    for params in settings.metadata:
        try:
            await load_metadata(params)
        except Exception:
            logger.error('failed to load metadata from params "%s"', params, exc_info=True)
