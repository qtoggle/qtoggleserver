
from typing import Any, Dict

import logging
import os

from qtoggleserver.conf import settings
from qtoggleserver.utils import conf as conf_utils


logger = logging.getLogger(__name__)


def can_write_conf_file() -> bool:
    if not settings.source:
        return False

    return os.access(settings.source, os.W_OK)


def conf_file_to_dict() -> Dict[str, Any]:
    if not can_write_conf_file():
        raise Exception('Configuration file not available')

    return conf_utils.config_from_file(settings.source)


def conf_file_from_dict(d: Dict[str, Any]) -> None:
    if not can_write_conf_file():
        raise Exception('Configuration file not available')

    logger.debug('updating configuration file %s', settings.source)

    config = conf_utils.config_from_dict(d)
    config_str = conf_utils.config_to_str(config)

    with open(settings.source, 'wt') as f:
        f.write(config_str)
