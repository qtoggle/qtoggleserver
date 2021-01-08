
import argparse
import asyncio
import logging.config
import os
import signal
import sys
import types

from typing import Any, Dict, Optional

from tornado import httpclient
from tornado import netutil

from qtoggleserver import persist
from qtoggleserver import slaves
from qtoggleserver import system
from qtoggleserver import version
from qtoggleserver import web
from qtoggleserver.core import device
from qtoggleserver.core import events
from qtoggleserver.core import history
from qtoggleserver.core import main
from qtoggleserver.core import ports
from qtoggleserver.core import reverse
from qtoggleserver.core import sessions
from qtoggleserver.conf import settings
from qtoggleserver.core import vports
from qtoggleserver.core import webhooks
from qtoggleserver.slaves import devices as slaves_devices
from qtoggleserver.utils import conf as conf_utils
from qtoggleserver.utils import logging as logging_utils
from qtoggleserver import peripherals  # This must be imported after core.ports


logger: Optional[logging.Logger] = None
options: Optional[types.SimpleNamespace] = None

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


def init_settings() -> None:
    if options.config_file:
        try:
            parsed_config = conf_utils.config_from_file(options.config_file)

        except IOError as e:
            sys.stderr.write(f'failed to open config file "{options.config_file}": {e}\n')
            sys.exit(-1)

        except Exception as e:
            sys.stderr.write(f'failed to load config file "{options.config_file}": {e}\n')
            sys.exit(-1)

        settings.source = os.path.abspath(options.config_file)

    else:
        parsed_config = {}

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
    if options.config_file:
        logger.info('using config from %s', options.config_file)

    else:
        logger.info('using default config')


def init_signals() -> None:
    loop = asyncio.get_event_loop()

    async def shutdown() -> None:
        global _stopping

        if _stopping:
            logger.error('interrupt signal received again')
            # TODO: commit suicide
            return

        _stopping = True

        logger.info('interrupt signal received')

        loop.stop()

    loop.add_signal_handler(signal.SIGINT, lambda: asyncio.create_task(shutdown()))
    loop.add_signal_handler(signal.SIGTERM, lambda: asyncio.create_task(shutdown()))


def handle_loop_exception(loop: asyncio.AbstractEventLoop, context: Dict[str, Any]) -> None:
    if isinstance(context.get('exception'), asyncio.CancelledError):
        return  # Ignore any cancelled errors

    loop.default_exception_handler(context)


async def init_loop() -> None:
    loop = asyncio.get_event_loop()

    loop.set_exception_handler(handle_loop_exception)


async def cleanup_loop() -> None:
    # Cancel all running tasks
    tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]

    for task in tasks:
        logger.debug(f'cancelling {task.get_coro()}')
        task.cancel()

    await asyncio.gather(*tasks)

    await asyncio.get_event_loop().shutdown_asyncgens()


def init_tornado() -> None:
    httpclient.AsyncHTTPClient.configure('tornado.simple_httpclient.SimpleAsyncHTTPClient', max_clients=1024)
    netutil.Resolver.configure(
        'tornado.netutil.OverrideResolver',
        mapping=system.dns.get_custom_dns_mapping_dict(),
        resolver=netutil.DefaultExecutorResolver()
    )


async def init_persist() -> None:
    logger.info('initializing persistence')
    try:
        await persist.get_value('device')

    except Exception as e:
        logger.error('failed to initialize persistence: %s', e, exc_info=True)
        sys.exit(-1)


async def cleanup_persist() -> None:
    logger.info('cleaning up persistence')
    await persist.cleanup()


async def init_system() -> None:
    logger.info('initializing system')
    await system.init()


async def cleanup_system() -> None:
    logger.info('cleaning up system')
    await system.cleanup()


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


async def init_history() -> None:
    if history.is_enabled():
        logger.info('initializing history')
        await history.init()


async def cleanup_history() -> None:
    if history.is_enabled():
        logger.info('cleaning history')
        await history.cleanup()


async def init_device() -> None:
    logger.info('initializing device')
    await device.init()


async def cleanup_device() -> None:
    logger.info('cleaning up device')
    await device.cleanup()


async def init_webhooks() -> None:
    if settings.webhooks.enabled:
        logger.info('initializing webhooks')
        await webhooks.init()


async def cleanup_webhooks() -> None:
    if settings.webhooks.enabled:
        logger.info('cleaning up webhooks')
        await webhooks.cleanup()


async def init_reverse() -> None:
    if settings.reverse.enabled:
        logger.info('initializing reverse API calls')
        await reverse.init()


async def cleanup_reverse() -> None:
    if settings.reverse.enabled:
        logger.info('cleaning up reverse API calls')
        await reverse.cleanup()


async def init_ports() -> None:
    logger.info('initializing ports')

    # Load ports statically configured in settings
    await ports.init()

    # Peripheral ports
    for peripheral in peripherals.all_peripherals():
        try:
            port_args = await peripheral.get_port_args()
            # Use raise_on_error=False because we prefer a partial successful startup rather than a failed one
            loaded_ports = await ports.load(port_args, raise_on_error=False)
            peripheral.set_ports(loaded_ports)

        except Exception as e:
            logger.error('failed to load ports of %s: %s', peripheral, e, exc_info=True)

    # Load virtual ports
    await vports.init()


async def cleanup_ports() -> None:
    logger.info('cleaning up ports')
    await ports.cleanup()


async def init_slaves() -> None:
    if settings.slaves.enabled:
        logger.info('initializing slaves')
        await slaves.init()


async def cleanup_slaves() -> None:
    if settings.slaves.enabled:
        logger.info('cleaning up slaves')
        await slaves.cleanup()


async def init_peripherals() -> None:
    logger.info('initializing peripherals')
    await peripherals.init()


async def cleanup_peripherals() -> None:
    logger.info('cleaning up peripherals')
    await peripherals.cleanup()


async def init_main() -> None:
    logger.info('initializing main')
    await main.init()

    # Wait until slaves are also ready before actually considering main loop ready
    if settings.slaves.enabled:
        logger.debug('waiting for slaves to become ready')
        while not slaves_devices.ready():
            await asyncio.sleep(0.1)

        logger.debug('slaves are ready')

    # Mark main as ready after all slaves with their ports have been initialized and hopefully brought online. Allow an
    # extra second for pending loop tasks.
    await asyncio.sleep(1)
    main.set_ready()


async def cleanup_main() -> None:
    logger.info('cleaning up main')
    await main.cleanup()


async def init_web() -> None:
    logger.info('initializing web')
    await web.init()


async def cleanup_web() -> None:
    logger.info('cleaning up web')
    await web.cleanup()


async def init() -> None:
    parse_args()

    init_settings()
    init_logging()
    init_signals()
    init_tornado()

    await init_system()
    await init_persist()
    await init_peripherals()
    await init_events()
    await init_sessions()
    await init_history()
    await init_device()
    await init_webhooks()
    await init_reverse()
    await init_ports()
    await init_slaves()
    await init_main()
    await init_web()


async def cleanup() -> None:
    await cleanup_web()
    await cleanup_main()
    await cleanup_ports()
    await cleanup_slaves()
    await cleanup_reverse()
    await cleanup_webhooks()
    await cleanup_device()
    await cleanup_history()
    await cleanup_sessions()
    await cleanup_events()
    await cleanup_peripherals()
    await cleanup_persist()
    await cleanup_system()
