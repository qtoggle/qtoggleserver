
import os as _os

from collections.abc import MutableMapping as _MutableMapping


class ComplexSetting(_MutableMapping):
    def __init__(self, **kwargs):
        self.update(**kwargs)

    def __getitem__(self, key):
        return self.__dict__[key]

    def __setitem__(self, key, value):
        self.__dict__[key] = value

    def __delitem__(self, key):
        del self.__dict__[key]

    def __iter__(self):
        return self.__dict__.__iter__()

    def __len__(self):
        return len(self.__dict__)

    def merge(self, other):
        for key, value in other.items():
            if isinstance(value, ComplexSetting):
                self.setdefault(key, ComplexSetting()).merge(value)

            else:
                self[key] = value


debug = False

logging = ComplexSetting(
    version=1,
    formatters={
        'default': {
            'format': '%(asctime)s: %(levelname)7s: [%(name)s] %(message)s',
            'datefmt': '%Y-%m-%d %H:%M:%S'
        }
    },
    handlers={
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'default'
        }
    },
    root={
        'level': 'DEBUG',
        'handlers': ['console']
    },
    loggers={
    },
    memory_logs_buffer_len=10000
)

core = ComplexSetting(
    tick_interval=50,
    listen_keepalive=60,
    event_queue_size=256,
    max_client_time_skew=300,
    listen_support=True,
    sequences_support=True,
    ssl_support=False,
    virtual_ports=1024,
)

server = ComplexSetting(
    addr='0.0.0.0',
    port=8888
)

persist = ComplexSetting(
    driver='redis.RedisDriver',
    host='127.0.0.1',
    port=6379,
    db=0
)

system = ComplexSetting(
    date_support=False,
    network_interface=None,
    wpa_supplicant_conf=None,
    fwupdate_driver=None
)

frontend = ComplexSetting(
    enabled=True,
    debug=False
)

slaves = ComplexSetting(
    enabled=False,
    timeout=10,
    keepalive=300,
    retry_interval=5,
    retry_count=3
)

webhooks = ComplexSetting(
    enabled=False
)

reverse = ComplexSetting(
    enabled=False,
    retry_interval=5
)

config = {}

ports = []

device_name_hooks = ComplexSetting(
    get=None,
    set=None
)
password_hook = None

pkg_path = _os.path.dirname(_os.path.abspath(__file__))
