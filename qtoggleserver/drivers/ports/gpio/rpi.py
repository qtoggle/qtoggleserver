
from RPi import GPIO

from qtoggleserver.core import ports
from qtoggleserver.utils import json as json_utils


class RPiGPIO(ports.Port):
    TYPE = ports.TYPE_BOOLEAN

    ADDITIONAL_ATTRDEFS = {
        'output': {
            'display_name': 'Is Output',
            'description': 'Controls the port direction.',
            'type': 'boolean',
            'modifiable': True
        },
        'pull': {
            'display_name': 'Pull Mode',
            'description': "Configures port's pull resistors.",
            'type': 'string',
            'modifiable': True,
            'choices': [
                {'value': 'off', 'display_name': 'Off'},
                {'value': 'up', 'display_name': 'Pull-up'},
                {'value': 'down', 'display_name': 'Pull-down'}
            ]
        }
    }

    _PULL_GPIO_MAPPING = {
        None: GPIO.PUD_OFF,
        False: GPIO.PUD_DOWN,
        True: GPIO.PUD_UP
    }

    _PULL_VALUE_MAPPING = {
        None: 'off',
        True: 'up',
        False: 'down',
        'off': None,
        'up': True,
        'down': False
    }

    def __init__(self, no, def_value=None, def_output=None, monostable_timeout=None):
        self._no = no
        self._def_value = def_value  # also plays the role of pull setup
        self._monostable_timeout = monostable_timeout
        self._monostable_timeout_handle = None

        # the default i/o state
        if def_output is None:
            def_output = GPIO.gpio_function(self._no) == GPIO.OUT

        self._def_output = def_output

        super().__init__(port_id='gpio{}'.format(no))

    def handle_enable(self):
        self._configure(self._def_output, self._def_value)

    def read_value(self):
        return GPIO.input(self._no) == 1

    def write_value(self, value):
        self.debug('writing output value %s', json_utils.dumps(value))
        GPIO.output(self._no, value)

        if self._monostable_timeout_handle:
            self.cancel_timeout(self._monostable_timeout_handle)

        if self._monostable_timeout is not None and value != self._def_value:
            self._monostable_timeout_handle = self.add_timeout(self._monostable_timeout, self._monostable_callback)

    def _monostable_callback(self):
        self.debug('monostable timeout occurred')
        self.write_value(self._def_value)
        self._monostable_timeout_handle = None

    def attr_is_writable(self):
        return self.attr_is_output()

    def attr_set_output(self, output):
        if not self.is_enabled():
            self._def_output = output
            return

        self._configure(output, self._def_value)

    def attr_is_output(self):
        return GPIO.gpio_function(self._no) == GPIO.OUT

    def attr_get_pull(self):
        return self._PULL_VALUE_MAPPING[self._def_value]

    def attr_set_pull(self, pull):
        self._def_value = self._PULL_VALUE_MAPPING[pull]
        if self.is_enabled() and not self.attr_is_output():
            self._configure(output=False, def_value=self._def_value)

    def _configure(self, output, def_value):
        if output:
            def_value = def_value or False  # def_value can be None
            self.debug('configuring as output (initial=%s)', str(def_value).lower())
            GPIO.setup(self._no, GPIO.OUT, initial=def_value)

        else:
            self.debug('configuring as input (pull=%s)', self._PULL_VALUE_MAPPING[def_value])
            GPIO.setup(self._no, GPIO.IN, pull_up_down=self._PULL_GPIO_MAPPING[def_value])


GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
