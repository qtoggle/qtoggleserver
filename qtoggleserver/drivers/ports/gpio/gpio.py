
import os

from typing import Optional, TextIO, Tuple

from qtoggleserver.core import ports
from qtoggleserver.utils import json as json_utils


class GPIO(ports.Port):
    TYPE = ports.TYPE_BOOLEAN

    ADDITIONAL_ATTRDEFS = {
        'output': {
            'display_name': 'Is Output',
            'description': 'Controls the port direction.',
            'type': 'boolean',
            'modifiable': True
        }
    }

    BASE_PATH = '/sys/class/gpio'

    def __init__(self, no: int, def_value: Optional[bool] = None, def_output: Optional[bool] = None) -> None:
        self._no: int = no
        self._def_value: Optional[bool] = def_value
        self._def_output: Optional[bool] = def_output

        self._val_file: Optional[TextIO] = None
        self._dir_file: Optional[TextIO] = None

        super().__init__(port_id=f'gpio{no}')

    async def handle_enable(self) -> None:
        try:
            (self._val_file, self._dir_file) = self._configure()

        except Exception as e:
            self.error('failed to configure %s: %s', self, e)

            raise

        if self._def_output is not None:
            await self.attr_set_output(self._def_output)

    async def read_value(self) -> bool:
        self._val_file.seek(0)

        return self._val_file.read(1) == '1'

    async def write_value(self, value: bool) -> None:
        self._val_file.seek(0)

        if value:
            value = '1'

        else:
            value = '0'

        self.debug('writing %s to "%s"', json_utils.dumps(value), self._val_file.name)
        self._val_file.write(value)
        self._val_file.flush()

    async def attr_is_writable(self) -> bool:
        return self._is_output()

    async def attr_set_output(self, output: bool) -> None:
        if not self._dir_file:
            return

        self._dir_file.seek(0)

        if output:
            text = 'out'

        else:
            text = 'in'

        self.debug('writing "%s" to "%s"', text, self._dir_file.name)
        self._dir_file.write(text)
        self._dir_file.flush()

        if output and self._def_value is not None:
            await self.write_value(self._def_value)

    async def attr_is_output(self) -> bool:
        return self._is_output()

    def _is_output(self) -> bool:
        if not self._dir_file:
            return False

        self._dir_file.seek(0)

        return self._dir_file.read(3) == 'out'

    def _configure(self) -> Tuple[TextIO, TextIO]:
        path = os.path.join(self.BASE_PATH, self.get_id())

        if not os.path.exists(path):
            self.debug('exporting %s', self)
            with open(os.path.join(self.BASE_PATH, 'export'), 'w') as f:
                f.write(str(self._no))

        return (
            open(os.path.join(path, 'value'), 'r+'),
            open(os.path.join(path, 'direction'), 'r+')
        )
