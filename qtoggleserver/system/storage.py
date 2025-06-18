import psutil

from qtoggleserver.conf import settings


def has_storage_support() -> bool:
    return bool(settings.system.storage.path)


def get_storage_usage() -> int | None:
    if not settings.system.storage.path:
        return None

    return int(psutil.disk_usage(settings.system.storage.path).percent)
