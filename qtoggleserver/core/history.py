
from __future__ import annotations

import asyncio
import logging
import time

from typing import Iterable, Optional

from qtoggleserver import persist
from qtoggleserver.conf import settings
from qtoggleserver.core import events as core_events
from qtoggleserver.core import ports as core_ports
from qtoggleserver.core.typing import GenericJSONDict
from qtoggleserver.utils import json as json_utils


PERSIST_COLLECTION = 'value_history'

logger = logging.getLogger(__name__)

_history_event_handler: Optional[HistoryEventHandler] = None
_sampling_task: Optional[asyncio.Task] = None
_janitor_task: Optional[asyncio.Task] = None


class HistoryEventHandler(core_events.Handler):
    FIRE_AND_FORGET = False

    async def handle_event(self, event: core_events.Event) -> None:
        if not isinstance(event, core_events.ValueChange):
            return  # We're only interested in port value changes

        port = event.get_port()
        history_interval = await port.get_history_interval()
        if history_interval != -1:
            return  # Only consider ports with history interval set to special -1 (on value change)

        now = int(time.time() * 1000)

        save_sample(port, now)
        port.set_history_last_timestamp(now)


async def sampling_task() -> None:
    while True:
        try:
            await asyncio.sleep(1)

            now = int(time.time() * 1000)
            for port in core_ports.get_all():
                if not port.is_enabled():
                    continue

                history_last_timestamp = port.get_history_last_timestamp()
                history_interval = await port.get_history_interval()
                if history_interval <= 0:  # Disabled or on value change
                    continue

                if now - history_last_timestamp < history_interval * 1000:
                    continue

                save_sample(port, now)
                port.set_history_last_timestamp(now)

        except asyncio.CancelledError:
            logger.debug('sampling task cancelled')
            break


async def janitor_task() -> None:
    while True:
        try:
            await asyncio.sleep(settings.core.history_janitor_interval)

            now = int(time.time())
            for port in core_ports.get_all():
                history_retention = await port.get_history_retention()
                if history_retention <= 0:
                    continue

                to_timestamp = (now - history_retention) * 1000
                logger.debug('removing old samples of %s from history', port)
                remove_samples(port, from_timestamp=0, to_timestamp=to_timestamp, background=True)

        except asyncio.CancelledError:
            logger.debug('janitor task cancelled')
            break

        except Exception as e:
            logger.error('janitor task error: %s', e, exc_info=True)


def is_enabled() -> bool:
    return persist.is_history_supported() and settings.core.history_support


def get_samples(
    port: core_ports.BasePort,
    from_timestamp: Optional[int] = None,
    to_timestamp: Optional[int] = None,
    limit: Optional[int] = None
) -> Iterable[GenericJSONDict]:
    filt = {
        'pid': port.get_id(),
    }

    if from_timestamp is not None:
        filt.setdefault('ts', {})['ge'] = from_timestamp

    if to_timestamp is not None:
        filt.setdefault('ts', {})['lt'] = to_timestamp

    results = persist.query(PERSIST_COLLECTION, filt=filt, sort='ts', limit=limit)

    return ({'value': r['val'], 'timestamp': r['ts']} for r in results)


def save_sample(port: core_ports.BasePort, timestamp: int) -> None:
    value = port.get_value()

    if value is None:
        logger.debug('skipping null sample of %s (timestamp = %s)', port, timestamp)
        return

    logger.debug('saving sample of %s (value = %s, timestamp = %s)', port, json_utils.dumps(value), timestamp)

    record = {
        'pid': port.get_id(),
        'val': value,
        'ts': timestamp
    }

    persist.insert(PERSIST_COLLECTION, record)


def remove_samples(
    port: core_ports.BasePort,
    from_timestamp: Optional[int] = None,
    to_timestamp: Optional[int] = None,
    background: bool = False
) -> Optional[int]:
    filt = {
        'pid': port.get_id()
    }

    if from_timestamp is not None:
        filt.setdefault('ts', {})['ge'] = from_timestamp

    if to_timestamp is not None:
        filt.setdefault('ts', {})['lt'] = to_timestamp

    if background:
        loop = asyncio.get_event_loop()
        loop.run_in_executor(None, persist.remove, PERSIST_COLLECTION, filt)

    else:
        return persist.remove(PERSIST_COLLECTION, filt)


def reset() -> None:
    logger.debug('clearing persisted data')
    persist.remove(PERSIST_COLLECTION)


async def init() -> None:
    global _history_event_handler
    global _sampling_task
    global _janitor_task

    _history_event_handler = HistoryEventHandler()
    core_events.register_handler(_history_event_handler)

    _sampling_task = asyncio.create_task(sampling_task())
    _janitor_task = asyncio.create_task(janitor_task())

    persist.ensure_index(PERSIST_COLLECTION, 'ts')


async def cleanup() -> None:
    if _sampling_task:
        _sampling_task.cancel()
        await _sampling_task

    if _janitor_task:
        _janitor_task.cancel()
        await _janitor_task
