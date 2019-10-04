
import json

from qtoggleserver.core import ports


class DummyGPIO(ports.Port):
    TYPE = ports.TYPE_BOOLEAN

    ADDITIONAL_ATTRDEFS = {
        'output': {
            'description': 'Controls the port direction.',
            'type': 'boolean',
            'modifiable': True
        }
    }

    def __init__(self, no, def_value=None, def_output=None, monostable_timeout=None):
        self._no = no
        self._def_value = def_value
        self._def_output = def_output
        self._monostable_timeout = monostable_timeout
        self._monostable_timeout_handle = None

        self._cur_value = False
        self._output = False

        super().__init__(port_id='gpio{}'.format(no))

    def enable(self):
        super().enable()

        if self._def_output is not None:
            self.attr_set_output(self._def_output)

    def read_value(self):
        return self._cur_value

    def write_value(self, value):
        self.debug('writing %s', json.dumps(value))

        self._cur_value = value

        if self._monostable_timeout_handle:
            self.cancel_timeout(self._monostable_timeout_handle)

        if self._monostable_timeout is not None and value != self._def_value:
            self._monostable_timeout_handle = self.add_timeout(self._monostable_timeout, self._monostable_callback)

    def _monostable_callback(self):
        self.debug('monostable timeout occurred')
        self.write_value(self._def_value)
        self._monostable_timeout_handle = None

    def attr_is_writable(self):
        return self._is_output()

    def attr_set_output(self, output):
        self.debug('configuring output = %s', output)
        self._output = output

        if output and self._def_value is not None:
            self.write_value(self._def_value)

    def attr_is_output(self):
        return self._is_output()

    def _is_output(self):
        return self._output
