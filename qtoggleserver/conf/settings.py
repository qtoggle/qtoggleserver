from typing import Any as _Any


source: str | None = None  # full path to the configuration file, automatically set at startup

debug: bool = False

public_url: str | None = None


logging: dict[str, _Any] = {
    "version": 1,
    "memory_logs_buffer_len": 10000,
    "formatters": {
        "default": {"format": "%(asctime)s: %(levelname)7s: [%(name)s] %(message)s", "datefmt": "%Y-%m-%d %H:%M:%S"}
    },
    "handlers": {"console": {"class": "logging.StreamHandler", "formatter": "default"}},
    "loggers": {
        # Double quotes are necessary to avoid HOCON key split
        '"asyncio"': {"level": "INFO"},
        '"bleak"': {"level": "INFO"},
        '"qtoggleserver.core.sessions"': {"level": "INFO"},
        '"qtoggleserver.persist"': {"level": "INFO"},
        '"qtoggleserver.drivers.persist"': {"level": "INFO"},
        '"qtoggleserver.utils.cmd"': {"level": "INFO"},
    },
    "root": {"level": "DEBUG", "handlers": ["console"]},
}


class core:
    class device_name:
        get_cmd: str | None = None
        set_cmd: str | None = None

    class passwords:
        set_cmd: str | None = None

    tick_interval: int = 50
    persist_interval: int = 2000
    event_queue_size: int = 1024
    max_client_time_skew: int = 300
    backup_support: bool = True
    history_support: bool = True
    history_janitor_interval: int = 3600
    listen_support: bool = True
    sequences_support: bool = True
    tls_support: bool = True
    virtual_ports: int = 1024


class server:
    addr: str = "0.0.0.0"
    port: int = 8888
    compress_response: bool = True

    class https:
        cert_file: str | None = None
        key_file: str | None = None


class persist:
    driver: str = "qtoggleserver.drivers.persist.JSONDriver"
    file_path: str = "qtoggleserver-data.json"


class system:
    setup_mode_cmd: str | None = None

    class date:
        set_cmd: str | None = None
        set_format: str | None = "%Y-%m-%dT%H:%M:%SZ"

    class timezone:
        get_cmd: str | None = None
        set_cmd: str | None = None

    class net:
        class wifi:
            get_cmd: str | None = None
            set_cmd: str | None = None

        class ip:
            get_cmd: str | None = None
            set_cmd: str | None = None

    class storage:
        path: str | None = None

    class temperature:
        get_cmd: str | None = None
        sensor_name: str | None = None
        sensor_index: int = 0
        min: int | None = 0
        max: int | None = 100

    class battery:
        get_cmd: str | None = None

    class fwupdate:
        driver: str | None = None


class frontend:
    enabled: bool = True
    debug: bool = False
    static_url: str | None = None
    display_name: str = "qToggleServer"
    display_short_name: str = "qToggleServer"
    description: str = "An application to control qToggleServer"  # TODO: i18n


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
        dhcp_interface: str | None = None

        class ap:
            interface: str | None = None
            interface_cmd: str | None = None
            ssid: str = "qToggleSetup"
            psk: str | None = None
            own_ip: str = "192.168.43.1"
            mask_len: int = 24
            start_ip: str = "192.168.43.50"
            stop_ip: str = "192.168.43.250"
            hostapd_binary: str | None = None
            hostapd_cli_binary: str | None = None
            dnsmasq_binary: str | None = None
            hostapd_log: str = "/tmp/hostapd.log"
            dnsmasq_log: str = "/tmp/dnsmasq.log"
            finish_timeout: int = 300


class webhooks:
    enabled: bool = False


class reverse:
    enabled: bool = False
    retry_interval: int = 5


event_handlers: list[dict[str, _Any]] = []

peripherals: list[dict[str, _Any]] = []

ports: list[dict[str, _Any]] = []

port_mappings: dict[str, str] = {}
