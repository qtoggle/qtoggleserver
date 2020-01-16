
import argparse
import asyncio
import logging.config
import signal
import sys

from typing import Any

from tornado import httpclient

from qtoggleserver import lib
from qtoggleserver import persist
from qtoggleserver import version
from qtoggleserver.conf import settings
from qtoggleserver.core import device
from qtoggleserver.core import events
from qtoggleserver.core import main
from qtoggleserver.core import ports
from qtoggleserver.core import reverse
from qtoggleserver.core import sessions
from qtoggleserver.core import vports
from qtoggleserver.core import webhooks
from qtoggleserver.slaves import devices as slaves_devices
from qtoggleserver.utils import conf as conf_utils
from qtoggleserver.utils import dynload as dynload_utils
from qtoggleserver.utils import logging as logging_utils

logger = None
options = None

_stopping = False


def parse_args() -> None:
    global options

    description = f'qToggleServer {version.VERSION}'
    epilog = None

    class VersionAction(argparse.Action):
        def __call__(self, *args, **kwargs) -> None:
            sys.stdout.write(f'{description}\n')
            sys.exit()

    parser = argparse.ArgumentParser(
        prog=sys.argv[0],
        description=description,
        epilog=epilog,
        add_help=False,
        formatter_class=argparse.RawTextHelpFormatter
    )

    parser.add_argument(
        '-c',
        help='specify the configuration file',
        type=str,
        dest='config_file'
    )

    parser.add_argument(
        '-h',
        help='print this help and exit',
        action='help',
        default=argparse.SUPPRESS
    )

    parser.add_argument(
        '-v',
        help='print program version and exit',
        action=VersionAction,
        default=argparse.SUPPRESS,
        nargs=0
    )

    options = parser.parse_args()

    if not options.config_file:
        parser.print_usage()
        sys.exit(-1)


def init_settings() -> None:
    try:
        parsed_config = conf_utils.config_from_file(options.config_file)

    except IOError as e:
        sys.stderr.write(f'failed to open config file "{options.config_file}": {e}\n')
        sys.exit(-1)

    except Exception as e:
        sys.stderr.write(f'failed to load config file "{options.config_file}": {e}\n')
        sys.exit(-1)

    def_config = conf_utils.obj_to_dict(settings)
    def_config = conf_utils.config_from_dict(def_config)

    config = conf_utils.config_merge(def_config, parsed_config)
    config = conf_utils.config_to_dict(config)

    conf_utils.update_obj_from_dict(settings, config)


def init_logging() -> None:
    global logger

    settings.logging['disable_existing_loggers'] = False
    logging.config.dictConfig(settings.logging)

    # Add memory logs handler
    root_logger = logging.getLogger()
    main.memory_logs = logging_utils.FifoMemoryHandler(capacity=settings.logging['memory_logs_buffer_len'])
    root_logger.addHandler(main.memory_logs)

    logger = logging.getLogger('qtoggleserver')

    logger.info('hello!')
    logger.info('this is qToggleServer %s', version.VERSION)

    # We can't do this in init_settings() because we have no logging there
    logger.info('using config from %s', options.config_file)


def init_signals() -> None:
    loop = asyncio.get_event_loop()

    def bye_handler(sig: int, frame: Any) -> None:
        global _stopping

        if _stopping:
            logger.error('interrupt signal already received, ignoring')
            return

        _stopping = True

        logger.info('interrupt signal received, shutting down')

        loop.call_soon_threadsafe(loop.stop)

    signal.signal(signal.SIGINT, bye_handler)
    signal.signal(signal.SIGTERM, bye_handler)


def init_configurables() -> None:
    httpclient.AsyncHTTPClient.configure('tornado.simple_httpclient.SimpleAsyncHTTPClient', max_clients=1024)

    configurables = conf_utils.obj_to_dict(settings.configurables)
    for class_name, opts in sorted(configurables.items()):
        try:
            logger.debug('configuring class %s', class_name)
            klass = dynload_utils.load_attr(class_name)

        except Exception as e:
            logger.error('failed to load class %s: %s', class_name, e, exc_info=True)
            continue

        try:
            klass.configure(**opts)

        except Exception as e:
            logger.error('failed to configure class %s: %s', class_name, e, exc_info=True)


async def init_persist() -> None:
    logger.info('initializing persistence')
    try:
        persist.get_value('device')

    except Exception as e:
        logger.error('failed to initialize persistence: %s', e, exc_info=True)
        sys.exit(-1)


async def cleanup_persist() -> None:
    persist.close()


async def init_events() -> None:
    logger.info('initializing events')
    await events.init()


async def cleanup_events() -> None:
    logger.info('cleaning up events')
    await events.cleanup()


async def init_sessions() -> None:
    logger.info('initializing sessions')
    await sessions.init()


async def cleanup_sessions() -> None:
    logger.info('cleaning up sessions')
    await sessions.cleanup()


async def init_device() -> None:
    logger.info('initializing device')
    device.load()

    if settings.webhooks.enabled:
        logger.info('initializing webhooks')
        webhooks.load()

    if settings.reverse.enabled:
        logger.info('initializing reverse API calls')
        reverse.load()


async def init_ports() -> None:
    logger.info('initializing ports')
    vports.load()
    port_settings = settings.ports + vports.all_settings()

    # Use raise_on_error=False because we prefer a partial successful startup rather than a failed one
    await ports.load(port_settings, raise_on_error=False)


async def cleanup_ports() -> None:
    logger.info('cleaning up ports')
    await ports.cleanup()


async def init_slaves() -> None:
    if settings.slaves.enabled:
        logger.info('initializing slaves')
        await slaves_devices.load()


async def cleanup_slaves() -> None:
    if settings.slaves.enabled:
        logger.info('cleaning up slaves')
        await slaves_devices.cleanup()


async def init_lib() -> None:
    logger.info('initializing libs')
    await lib.init()


async def cleanup_lib() -> None:
    logger.info('cleaning up libs')
    await lib.cleanup()


async def init_main() -> None:
    logger.info('initializing main')
    await main.init()

    # Wait until slaves are also ready before actually considering main loop ready
    if settings.slaves.enabled:
        logger.info('waiting for slaves to become ready')
        while not slaves_devices.ready():
            await asyncio.sleep(0.1)

    # Mark main as ready after all slaves with their ports have been initialized and hopefully brought online. Allow an
    # extra second for pending loop tasks.
    await asyncio.sleep(1)
    main.set_ready()


async def cleanup_main() -> None:
    logger.info('cleaning up main')
    await main.cleanup()


async def init() -> None:
    parse_args()

    init_settings()
    init_logging()
    init_signals()
    init_configurables()

    await init_persist()
    await init_events()
    await init_sessions()
    await init_device()
    await init_ports()
    await init_slaves()
    await init_lib()
    await init_main()


async def cleanup() -> None:
    await cleanup_main()
    await cleanup_lib()
    await cleanup_slaves()
    await cleanup_ports()
    await cleanup_sessions()
    await cleanup_events()
    await cleanup_persist()
