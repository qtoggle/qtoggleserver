
import typing as _typing


source: _typing.Optional[str] = None  # Full path to the configuration file, automatically set at startup

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
        # Double quotes are necessary to avoid HOCON key split
        '"asyncio"': {'level': 'INFO'},
        '"qtoggleserver.core.sessions"': {'level': 'INFO'},
        '"qtoggleserver.persist"': {'level': 'INFO'},
        '"qtoggleserver.drivers.persist"': {'level': 'INFO'},
        '"qtoggleserver.utils.cmd"': {'level': 'INFO'}
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
    backup_support: bool = True
    history_support: bool = True
    history_janitor_interval: int = 600
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
    driver: str = 'qtoggleserver.drivers.persist.JSONDriver'
    file_path: str = 'qtoggleserver-data.json'


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

    class storage:
        path: _typing.Optional[str] = None

    class temperature:
        get_cmd: _typing.Optional[str] = None
        sensor_name: _typing.Optional[str] = None
        sensor_index: int = 0
        min: _typing.Optional[int] = 0
        max: _typing.Optional[int] = 100

    class battery:
        get_cmd: _typing.Optional[str] = None

    class fwupdate:
        driver: _typing.Optional[str] = None


class frontend:
    enabled: bool = True
    debug: bool = False
    static_url: str = None


class slaves:
    enabled: bool = True
    timeout: int = 10
    long_timeout: int = 60
    keepalive: int = 10
    retry_interval: int = 5
    retry_count: int = 3

    class discover:
        request_timeout: int = 5
        dhcp_timeout: int = 10
        dhcp_interface: str = None

        class ap:
            interface: str = None
            interface_cmd: str = None
            ssid: str = 'qToggleSetup'
            psk: str = None
            own_ip: str = '192.168.43.1'
            mask_len: int = 24
            start_ip: str = '192.168.43.50'
            stop_ip: str = '192.168.43.250'
            hostapd_binary: str = None
            hostapd_cli_binary: str = None
            dnsmasq_binary: str = None
            hostapd_log: str = '/tmp/hostapd.log'
            dnsmasq_log: str = '/tmp/dnsmasq.log'
            finish_timeout: int = 300


class webhooks:
    enabled: bool = False


class reverse:
    enabled: bool = False
    retry_interval: int = 5


event_handlers: _typing.List[_typing.Dict[str, _typing.Any]] = []

peripherals: _typing.List[_typing.Dict[str, _typing.Any]] = []

ports: _typing.List[_typing.Dict[str, _typing.Any]] = []

port_mappings: _typing.Dict[str, str] = {}
