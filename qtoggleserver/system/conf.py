import logging
import os
import shutil

from typing import Any

from qtoggleserver.conf import settings
from qtoggleserver.utils import conf as conf_utils


logger = logging.getLogger(__name__)


def can_write_conf_file() -> bool:
    if not settings.source:
        return False

    return os.access(settings.source, os.W_OK)


def conf_file_to_dict() -> dict[str, Any]:
    if not can_write_conf_file():
        raise Exception("Configuration file not available")

    assert settings.source

    return conf_utils.config_from_file(settings.source)


def conf_file_from_dict(d: dict[str, Any]) -> None:
    if not can_write_conf_file():
        raise Exception("Configuration file not available")

    logger.debug("updating configuration file %s", settings.source)

    assert settings.source

    existing_d = conf_utils.config_from_file(settings.source)
    existing_d.update(d)

    config = conf_utils.config_from_dict(existing_d)
    config_str = conf_utils.config_to_str(config)

    # Create a backup
    try:
        shutil.copy(settings.source, f"{settings.source}.bak")
    except Exception:
        logger.warning("failed to create backup file %s", f"{settings.source}.bak", exc_info=True)

    with open(settings.source, "w") as f:
        f.write(config_str)
