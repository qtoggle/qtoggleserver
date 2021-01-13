
from __future__ import annotations

import asyncio
import logging
import time

from typing import Dict, Iterable, Optional, List

from qtoggleserver import persist
from qtoggleserver import system
from qtoggleserver.conf import settings
from qtoggleserver.core import events as core_events
from qtoggleserver.core import ports as core_ports
from qtoggleserver.core.typing import GenericJSONDict, PortValue
from qtoggleserver.utils import json as json_utils


PERSIST_COLLECTION = 'value_history'

_CACHE_TIMESTAMP_MIN_AGE = 3600 * 1000  # Don't cache samples newer than this number of milliseconds ago

logger = logging.getLogger(__name__)

_history_event_handler: Optional[HistoryEventHandler] = None
_sampling_task: Optional[asyncio.Task] = None
_janitor_task: Optional[asyncio.Task] = None

# Samples cached by port_id and timestamp
_samples_cache: Dict[str, Dict[int, PortValue]] = {}


class HistoryEventHandler(core_events.Handler):
    FIRE_AND_FORGET = True

    async def handle_event(self, event: core_events.Event) -> None:
        if not isinstance(event, core_events.ValueChange):
            return  # We're only interested in port value changes

        if not system.date.has_real_date_time():
            return  # Don't record history unless we've got real date/time

        port = event.get_port()
        history_interval = await port.get_history_interval()
        if history_interval != -1:
            return  # Only consider ports with history interval set to special -1 (on value change)

        now_ms = int(time.time() * 1000)

        await save_sample(port, now_ms)
        port.set_history_last_timestamp(now_ms)


async def sampling_task() -> None:
    while True:
        try:
            await asyncio.sleep(1)

            if not system.date.has_real_date_time():
                continue  # Don't record history unless we've got real date/time

            now_ms = int(time.time() * 1000)
            for port in core_ports.get_all():
                if not port.is_enabled():
                    continue

                history_last_timestamp = port.get_history_last_timestamp()
                history_interval = await port.get_history_interval()
                if history_interval <= 0:  # Disabled or on value change
                    continue

                if now_ms - history_last_timestamp < history_interval * 1000:
                    continue

                await save_sample(port, now_ms)
                port.set_history_last_timestamp(now_ms)
                await port.save()  # history_last_timestamp must be persisted

        except asyncio.CancelledError:
            logger.debug('sampling task cancelled')
            break

        except Exception as e:
            logger.error('sampling task error: %s', e, exc_info=True)


async def janitor_task() -> None:
    while True:
        try:
            await asyncio.sleep(settings.core.history_janitor_interval)

            if not system.date.has_real_date_time():
                continue

            now = int(time.time())
            for port in core_ports.get_all():
                history_retention = await port.get_history_retention()
                if history_retention <= 0:
                    continue

                to_timestamp = (now - history_retention) * 1000
                logger.debug('removing old samples of %s from history', port)
                await remove_samples(port, from_timestamp=0, to_timestamp=to_timestamp, background=False)

        except asyncio.CancelledError:
            logger.debug('janitor task cancelled')
            break

        except Exception as e:
            logger.error('janitor task error: %s', e, exc_info=True)


def is_enabled() -> bool:
    return persist.is_history_supported() and settings.core.history_support


async def get_samples_slice(
    port: core_ports.BasePort,
    from_timestamp: Optional[int] = None,
    to_timestamp: Optional[int] = None,
    limit: Optional[int] = None,
    sort_desc: bool = False
) -> Iterable[GenericJSONDict]:
    filt = {
        'pid': port.get_id(),
    }

    if from_timestamp is not None:
        filt.setdefault('ts', {})['ge'] = from_timestamp

    if to_timestamp is not None:
        filt.setdefault('ts', {})['lt'] = to_timestamp

    sort = 'ts'
    if sort_desc:
        sort = f'-{sort}'

    results = await persist.query(PERSIST_COLLECTION, filt=filt, sort=sort, limit=limit)

    return ({'value': r['val'], 'timestamp': r['ts']} for r in results)


async def get_samples_by_timestamp(
    port: core_ports.BasePort,
    timestamps: List[int]
) -> Iterable[GenericJSONDict]:
    port_filter = {
        'pid': port.get_id(),
    }

    now_ms = int(time.time() * 1000)
    samples_cache = _samples_cache.setdefault(port.get_id(), {})
    INEXISTENT = {}

    query_tasks = []
    for timestamp in timestamps:
        # Look it up in cache
        sample = samples_cache.get(timestamp, INEXISTENT)
        if sample is INEXISTENT:
            filt = dict(port_filter, ts={'le': timestamp})
            task = persist.query(PERSIST_COLLECTION, filt=filt, sort='-ts', limit=1)

        else:
            task = asyncio.Future()
            task.set_result([sample])

        query_tasks.append(task)

    task_results = await asyncio.gather(*query_tasks)

    samples = []
    for i, task_result in enumerate(task_results):
        timestamp = timestamps[i]

        query_results = list(task_result)
        if query_results:
            sample = query_results[0]
            samples.append(sample)

        else:
            samples.append(None)

        # Add sample to cache if it's old enough
        if now_ms - timestamp > _CACHE_TIMESTAMP_MIN_AGE:
            samples_cache[timestamp] = samples[-1]

    return ({'value': r['val'], 'timestamp': r['ts']} if r is not None else None for r in samples)


async def save_sample(port: core_ports.BasePort, timestamp: int) -> None:
    value = port.get_last_read_value()

    if value is None:
        logger.debug('skipping null sample of %s (timestamp = %s)', port, timestamp)
        return

    logger.debug('saving sample of %s (value = %s, timestamp = %s)', port, json_utils.dumps(value), timestamp)

    record = {
        'pid': port.get_id(),
        'val': value,
        'ts': timestamp
    }

    await persist.insert(PERSIST_COLLECTION, record)


async def remove_samples(
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

    # Invalidate samples cache for this port
    _samples_cache.pop(port.get_id(), None)

    if background:

        def remove_sync() -> None:
            loop = asyncio.new_event_loop()
            loop.run_until_complete(persist.remove(PERSIST_COLLECTION, filt))
            loop.close()

        loop = asyncio.get_event_loop()
        loop.run_in_executor(None, remove_sync)

    else:
        return await persist.remove(PERSIST_COLLECTION, filt)


async def reset() -> None:
    logger.debug('clearing persisted data')
    await persist.remove(PERSIST_COLLECTION)


async def init() -> None:
    global _history_event_handler
    global _sampling_task
    global _janitor_task

    _history_event_handler = HistoryEventHandler()
    core_events.register_handler(_history_event_handler)

    _sampling_task = asyncio.create_task(sampling_task())
    _janitor_task = asyncio.create_task(janitor_task())

    await persist.ensure_index(PERSIST_COLLECTION, 'ts')


async def cleanup() -> None:
    if _sampling_task:
        _sampling_task.cancel()
        await _sampling_task

    if _janitor_task:
        _janitor_task.cancel()
        await _janitor_task
