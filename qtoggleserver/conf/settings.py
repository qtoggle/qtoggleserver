
import os as _os


debug = False


logging = {
    'version': 1,
    'memory_logs_buffer_len': 10000,
    'formatters': {
        'default': {
            'format': '%(asctime)s: %(levelname)7s: [%(name)s] %(message)s',
            'datefmt': '%Y-%m-%d %H:%M:%S'
        }
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'default'
        }
    },
    'loggers': {},

    'root': {
        'level': 'DEBUG',
        'handlers': ['console']
    }
}


class core:
    tick_interval = 50
    listen_keepalive = 60
    event_queue_size = 256
    max_client_time_skew = 300
    listen_support = True
    sequences_support = True
    ssl_support = False
    virtual_ports = 1024


class server:
    addr = '0.0.0.0'
    port = 8888


class persist:
    driver = 'qtoggleserver.drivers.persist.redis.RedisDriver'
    host = '127.0.0.1'
    port = 6379
    db = 0


class system:
    date_support = False
    network_interface = None
    wpa_supplicant_conf = None
    fwupdate_driver = None


class frontend:
    enabled = True
    debug = False


class slaves:
    enabled = False
    timeout = 10
    keepalive = 300
    retry_interval = 5
    retry_count = 3


class webhooks:
    enabled = False


class reverse:
    enabled = False
    retry_interval = 5


class configurables:
    pass


class device_name_hooks:
    get = None
    set = None


password_hook = None


ports = []


pkg_path = _os.path.dirname(_os.path.abspath(__file__))
