
import asyncio

from typing import Tuple

from qtoggleserver import version
from qtoggleserver.system import fwupdate


_SLEEP_TIME = 1
_DUMMY_VERSION = '1.0.2222-11-10'
_DUMMY_URL = f'http://firmware.qtoggle.io/qtoggleserver/{_DUMMY_VERSION}'
_DUMMY_DATE = '2222-11-10'


class DummyDriver(fwupdate.BaseDriver):
    def __init__(self) -> None:
        self._status = fwupdate.STATUS_IDLE

        fwupdate.BaseDriver.__init__(self)

    async def get_current_version(self) -> str:
        return version.VERSION

    async def get_latest(self) -> Tuple[str, str, str]:
        if self._status == fwupdate.STATUS_IDLE:
            await asyncio.sleep(_SLEEP_TIME)

        return _DUMMY_VERSION, _DUMMY_DATE, _DUMMY_URL

    async def get_status(self) -> str:
        return self._status

    async def update_to_version(self, version: str) -> None:
        asyncio.create_task(self._perform_update())

    async def update_to_url(self, url: str) -> None:
        asyncio.create_task(self._perform_update())

    async def _perform_update(self) -> None:
        self._status = fwupdate.STATUS_CHECKING
        await asyncio.sleep(_SLEEP_TIME)
        self._status = fwupdate.STATUS_DOWNLOADING
        await asyncio.sleep(_SLEEP_TIME)
        self._status = fwupdate.STATUS_EXTRACTING
        await asyncio.sleep(_SLEEP_TIME)
        self._status = fwupdate.STATUS_VALIDATING
        await asyncio.sleep(_SLEEP_TIME)
        self._status = fwupdate.STATUS_FLASHING
        await asyncio.sleep(_SLEEP_TIME)
        self._status = fwupdate.STATUS_RESTARTING
        await asyncio.sleep(_SLEEP_TIME * 2)
        self._status = fwupdate.STATUS_IDLE
