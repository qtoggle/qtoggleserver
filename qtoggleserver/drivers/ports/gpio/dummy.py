
from qtoggleserver.core import ports
from qtoggleserver.utils import json as json_utils


class DummyGPIO(ports.Port):
    TYPE = ports.TYPE_BOOLEAN

    ADDITIONAL_ATTRDEFS = {
        'output': {
            'display_name': 'Is Output',
            'description': 'Controls the port direction.',
            'type': 'boolean',
            'modifiable': True
        }
    }

    def __init__(self, no, def_value=None, def_output=None):
        self._no = no

        self._def_value = def_value
        self._def_output = def_output

        self._dummy_value = def_value
        self._dummy_output = def_output if def_output is not None else False

        super().__init__(port_id='gpio{}'.format(no))

    def enable(self):
        super().enable()

        if self._def_output is not None:
            self.attr_set_output(self._def_output)

    def read_value(self):
        return self._dummy_value

    def write_value(self, value):
        self.debug('writing "%s"', json_utils.dumps(value))
        self._dummy_value = value

    def attr_is_writable(self):
        return self._dummy_output

    def attr_set_output(self, output):
        self._dummy_output = output

        if output:
            self.debug('setting output mode')

        else:
            self.debug('setting input mode')

        if output and self._def_value is not None:
            self.write_value(self._def_value)

    def attr_is_output(self):
        return self._dummy_output