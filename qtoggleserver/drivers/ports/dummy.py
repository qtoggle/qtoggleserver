
from qtoggleserver.core import ports


class DummyPort(ports.Port):
    TYPE = ports.TYPE_NUMBER
    DUMMY_ATTR = 163
    INTEGER = True

    ADDITIONAL_ATTRDEFS = {
        'dummy_attr': {
            'description': 'some dummy attribute',
            'type': 'number',
            'modifiable': True
        },
        'output': {
            'description': 'Is output',
            'type': 'boolean',
            'modifiable': True
        }
    }
    
    def __init__(self, no, writable, def_value=None, monostable_timeout=None):
        self._no = no
        self._writable = writable
        self._def_value = def_value
        self._dummy_attr = 5
        self._dummy_value = False
        self._output = False
        self._monostable_timeout = monostable_timeout
        self._monostable_timeout_handle = None

        super().__init__(port_id='dummy{}'.format(no))

        self._dummy_value = def_value if def_value is not None else self.adapt_value_type(0)

    def initialize(self):
        self._dummy_value = self.get_value()

    def read_value(self):
        return self._dummy_value

    def attr_is_writable(self):
        return self._output

    def write_value(self, value):
        self._dummy_value = value
        self.debug('VALUE = %s (before)', value)
        # await asyncio.sleep(2)
        # self.debug('VALUE = %s (after)' % value)
        #
        # if self._monostable_timeout_handle:
        #     self.cancel_timeout(self._monostable_timeout_handle)
        #     self._monostable_timeout_handle = None
        #
        # if self._monostable_timeout is not None and value != self._def_value:
        #     self._monostable_timeout_handle = self.add_timeout(self._monostable_timeout, self._monostable_callback)

    def _monostable_callback(self):
        self.debug('monostable timeout occurred')
        self.write_value(self._def_value)
        self._monostable_timeout_handle = None
