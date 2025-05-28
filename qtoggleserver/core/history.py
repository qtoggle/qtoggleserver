from __future__ import annotations

import asyncio
import logging
import time

from collections.abc import Iterable

from qtoggleserver import persist, system
from qtoggleserver.conf import settings
from qtoggleserver.core import events as core_events
from qtoggleserver.core import ports as core_ports
from qtoggleserver.core.typing import GenericJSONDict, PortValue
from qtoggleserver.utils import json as json_utils


_PERSIST_COLLECTION = "value_history"
_CACHE_TIMESTAMP_MIN_AGE = 3600 * 1000  # don't cache samples newer than this number of milliseconds ago

logger = logging.getLogger(__name__)

_history_event_handler: HistoryEventHandler | None = None
_sampling_task: asyncio.Task | None = None
_janitor_task: asyncio.Task | None = None

# Samples cached by port_id and timestamp
_samples_cache: dict[str, dict[int, PortValue]] = {}

# Used to schedule sample removal with remove_samples(..., background=True)
_pending_remove_samples: list[tuple[core_ports.BasePort, int | None, int | None]] = []


class HistoryEventHandler(core_events.Handler):
    FIRE_AND_FORGET = True

    async def handle_event(self, event: core_events.Event) -> None:
        if not isinstance(event, core_events.ValueChange):
            return  # we're only interested in port value changes

        if not system.date.has_real_date_time():
            return  # don't record history unless we've got real date/time

        port = event.get_port()
        history_interval = await port.get_history_interval()
        if history_interval != -1:
            return  # only consider ports with history interval set to special -1 (on value change)

        now_ms = int(time.time() * 1000)

        await save_sample(port, now_ms)
        port.set_history_last_timestamp(now_ms)


async def sampling_task() -> None:
    while True:
        try:
            await asyncio.sleep(1)

            if not system.date.has_real_date_time():
                continue  # don't record history unless we've got real date/time

            now_ms = int(time.time() * 1000)
            for port in core_ports.get_all():
                if not port.is_enabled():
                    continue

                history_last_timestamp = port.get_history_last_timestamp()
                history_interval = await port.get_history_interval()
                if history_interval <= 0:  # disabled or on value change
                    continue

                if now_ms - history_last_timestamp < history_interval * 1000:
                    continue

                await save_sample(port, now_ms)
                port.set_history_last_timestamp(now_ms)
                port.save_asap()  # history_last_timestamp must be persisted
        except asyncio.CancelledError:
            logger.debug("sampling task cancelled")
            break
        except Exception as e:
            logger.error("sampling task error: %s", e, exc_info=True)


async def janitor_task() -> None:
    global _pending_remove_samples

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
                logger.debug("removing old samples of %s from history", port)
                await remove_samples([port], from_timestamp=0, to_timestamp=to_timestamp)

            # Remove samples that were background-scheduled for removal
            # Group together requests w/o timestamp bounds

            ports = []
            rem_pending_remove_samples = []
            for port, from_timestamp, to_timestamp in _pending_remove_samples:
                if from_timestamp is to_timestamp is None:
                    ports.append(port)
                else:
                    rem_pending_remove_samples.append((port, from_timestamp, to_timestamp))

            if ports:
                port_ids = [p.get_id() for p in ports]
                logger.debug("removing samples of %s from history (background)", ", ".join(port_ids))
                await remove_samples(ports)

            _pending_remove_samples = rem_pending_remove_samples
            while _pending_remove_samples:
                port, from_timestamp, to_timestamp = _pending_remove_samples.pop(0)
                logger.debug("removing samples of %s from history (background)", port)
                await remove_samples([port], from_timestamp=from_timestamp, to_timestamp=to_timestamp)
        except asyncio.CancelledError:
            logger.debug("janitor task cancelled")
            break
        except Exception as e:
            logger.error("janitor task error: %s", e, exc_info=True)


def is_enabled() -> bool:
    return persist.is_samples_supported() and settings.core.history_support


async def get_samples_slice(
    port: core_ports.BasePort,
    from_timestamp: int | None = None,
    to_timestamp: int | None = None,
    limit: int | None = None,
    sort_desc: bool = False,
) -> Iterable[tuple[int, PortValue]]:
    samples = await persist.get_samples_slice(
        _PERSIST_COLLECTION, port.get_id(), from_timestamp, to_timestamp, limit, sort_desc
    )

    # Transform samples according to port type
    type_ = await port.get_type()
    integer = await port.get_attr("integer")
    samples = ((s[0], port.adapt_value_type_sync(type_, integer, s[1])) for s in samples)

    return samples


async def get_samples_by_timestamp(port: core_ports.BasePort, timestamps: list[int]) -> Iterable[GenericJSONDict]:
    now_ms = int(time.time() * 1000)
    samples_cache = _samples_cache.setdefault(port.get_id(), {})
    MISSED = {}

    results = {}
    missed_timestamps = []
    for timestamp in timestamps:
        # Look it up in cache
        sample = samples_cache.get(timestamp, MISSED)
        if sample is MISSED:
            missed_timestamps.append(timestamp)
        else:
            results[timestamp] = sample

    if missed_timestamps:
        samples = await persist.get_samples_by_timestamp(_PERSIST_COLLECTION, port.get_id(), missed_timestamps)
        samples = list(samples)

        # Transform samples according to port type
        type_ = await port.get_type()
        integer = await port.get_attr("integer")
        samples = [port.adapt_value_type_sync(type_, integer, s) for s in samples]

        for i, timestamp in enumerate(missed_timestamps):
            results[timestamp] = samples[i]

            # Add sample to cache if it's old enough
            if now_ms - timestamp > _CACHE_TIMESTAMP_MIN_AGE:
                samples_cache[timestamp] = samples[i]

    return ({"value": v, "timestamp": t} if v is not None else None for t, v in results.items())


async def save_sample(port: core_ports.BasePort, timestamp: int) -> None:
    value = port.get_last_read_value()
    if value is None:
        logger.debug("skipping null sample of %s (timestamp = %s)", port, timestamp)
        return

    logger.debug("saving sample of %s (value = %s, timestamp = %s)", port, json_utils.dumps(value), timestamp)

    await persist.save_sample(_PERSIST_COLLECTION, port.get_id(), timestamp, float(value))


async def remove_samples(
    ports: list[core_ports.BasePort],
    from_timestamp: int | None = None,
    to_timestamp: int | None = None,
    background: bool = False,
) -> int | None:
    # Invalidate samples cache for the ports
    for port in ports:
        _samples_cache.pop(port.get_id(), None)

    if background:
        for port in ports:
            _pending_remove_samples.append((port, from_timestamp, to_timestamp))
    else:
        port_ids = [p.get_id() for p in ports]
        return await persist.remove_samples(_PERSIST_COLLECTION, port_ids, from_timestamp, to_timestamp)


async def reset() -> None:
    logger.debug("clearing persisted data")
    await persist.remove_samples(_PERSIST_COLLECTION)


async def init() -> None:
    global _history_event_handler
    global _sampling_task
    global _janitor_task

    _history_event_handler = HistoryEventHandler()
    core_events.register_handler(_history_event_handler)

    _sampling_task = asyncio.create_task(sampling_task())
    _janitor_task = asyncio.create_task(janitor_task())

    await persist.ensure_index(_PERSIST_COLLECTION)


async def cleanup() -> None:
    if _sampling_task:
        _sampling_task.cancel()
        await _sampling_task

    if _janitor_task:
        _janitor_task.cancel()
        await _janitor_task
