
import asyncio
import json
import re

from qtoggleserver.system import fwupdate
from qtoggleserver.utils import process


class FWUpdateCommandError(fwupdate.FWUpdateException):
    pass


class ThingOSDriver(fwupdate.BaseDriver):
    FWUPDATE_BIN = '/sbin/fwupdate'

    async def get_current_version(self):
        return await self._call_fwupdate(['current'])

    async def get_latest(self):
        versions = await self._call_fwupdate(['versions', '-j'])
        if not versions:
            return '', '', ''

        versions = versions.split('\n')

        # versions are sorted from latest to oldest
        latest = versions[0]

        info = json.loads(latest)

        return info['version'], info['date'], info['url']

    async def get_status(self):
        s = await self._call_fwupdate(['status'])

        if s == 'idle':
            status = fwupdate.STATUS_IDLE

        elif re.match('^downloading .*$', s):
            status = fwupdate.STATUS_DOWNLOADING

        elif re.match('^downloaded .*$', s):
            status = fwupdate.STATUS_EXTRACTING

        elif re.match('^extracting .*$', s):
            status = fwupdate.STATUS_EXTRACTING

        elif re.match('^extracted .*$', s):
            status = fwupdate.STATUS_FLASHING

        elif re.match('^flashing boot .*$', s):
            status = fwupdate.STATUS_FLASHING

        elif re.match('^boot ready .*$', s):
            status = fwupdate.STATUS_RESTARTING

        else:
            status = fwupdate.STATUS_ERROR

        return status

    async def update_to_version(self, version):
        asyncio.create_task(self._call_fwupdate(['upgrade', version]))
        await self._wait_idle()

    async def update_to_url(self, url):
        asyncio.create_task(self._call_fwupdate(['upgrade', url]))
        await self._wait_idle()

    async def _call_fwupdate(self, args):
        args = [self.FWUPDATE_BIN] + args
        exit_code, output, error = await process.call_subprocess(args)

        if exit_code:
            raise FWUpdateCommandError(error)

        return output.strip().decode()

    async def _wait_idle(self):
        for _ in range(50):  # wait at most 5 seconds
            output = await self._call_fwupdate(['status'])
            if output != 'idle':
                break

            await asyncio.sleep(0.1)

        else:
            raise FWUpdateCommandError('timeout waiting for update to begin')
