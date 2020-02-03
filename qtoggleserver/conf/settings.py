
import os as _os
import typing as _typing


debug: bool = False

public_url: _typing.Optional[str] = None


logging: _typing.Dict[str, _typing.Any] = {
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
    'loggers': {
        '"qtoggleserver.persist"': {'level': 'INFO'}  # Double quotes are necessary to avoid HOCON key split
    },
    'root': {
        'level': 'DEBUG',
        'handlers': ['console']
    }
}


class core:

    class device_name:
        get_cmd: _typing.Optional[str] = None
        set_cmd: _typing.Optional[str] = None

    class passwords:
        set_cmd: _typing.Optional[str] = None

    tick_interval: int = 50
    event_queue_size: int = 256
    max_client_time_skew: int = 300
    listen_support: bool = True
    sequences_support: bool = True
    ssl_support: bool = True
    virtual_ports: int = 1024


class server:
    addr: str = '0.0.0.0'
    port: int = 8888
    compress_response: bool = True

    class https:
        cert_file: _typing.Optional[str] = None
        key_file: _typing.Optional[str] = None


class persist:
    driver: str = 'qtoggleserver.drivers.persist.redis.RedisDriver'
    host: _typing.Optional[str] = '127.0.0.1'
    port: _typing.Optional[int] = 6379
    db: _typing.Union[str, int] = 0


class system:

    class date:
        set_cmd: _typing.Optional[str] = None
        set_format: _typing.Optional[str] = '%Y-%m-%dT%H:%M:%SZ'

    class timezone:
        get_cmd: _typing.Optional[str] = None
        set_cmd: _typing.Optional[str] = None

    class net:
        class wifi:
            get_cmd: _typing.Optional[str] = None
            set_cmd: _typing.Optional[str] = None

        class ip:
            get_cmd: _typing.Optional[str] = None
            set_cmd: _typing.Optional[str] = None

    fwupdate_driver: _typing.Optional[str] = None


class frontend:
    enabled: bool = True
    debug: bool = False


class slaves:
    enabled: bool = True
    timeout: int = 10
    long_timeout: int = 60
    keepalive: int = 300
    retry_interval: int = 5
    retry_count: int = 3


class webhooks:
    enabled: bool = False


class reverse:
    enabled: bool = False
    retry_interval: int = 5


class configurables:
    pass


event_handlers: _typing.List[_typing.Dict[str, _typing.Any]] = []

ports: _typing.List[_typing.Dict[str, _typing.Any]] = []

port_mappings: _typing.Dict[str, str] = {}

pkg_path: str = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
