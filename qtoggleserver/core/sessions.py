
from __future__ import annotations

import asyncio
import logging
import time

from typing import Dict, List, Optional

from qtoggleserver.core import events as core_events
from qtoggleserver.conf import settings


logger = logging.getLogger(__name__)

_sessions_by_id: Dict[str, Session] = {}
_sessions_event_handler: Optional[SessionsEventHandler] = None


class Session:
    def __init__(self, session_id: str) -> None:
        self.id: str = session_id
        self.accessed: int = 0
        self.timeout: int = 0
        self.access_level: int = 0
        self.future: Optional[asyncio.Future] = None
        self.queue: List[core_events.Event] = []

    def reset_and_wait(self, timeout: int, access_level: int) -> asyncio.Future:
        logger.debug('resetting %s (timeout=%s, access_level=%s)', self, timeout, access_level)

        if self.future:
            logger.debug('%s already has a listening connection, responding', self)
            self.respond()

        future = asyncio.get_running_loop().create_future()

        self.accessed = time.time()
        self.timeout = timeout
        self.access_level = access_level
        self.future = future

        if self.queue:
            logger.debug('%s has queued events, responding right away', self)
            self.respond()

        return future

    def is_empty(self) -> bool:
        return len(self.queue) == 0

    def is_active(self) -> bool:
        return self.future is not None

    def respond(self) -> None:
        events = list(self.queue)
        self.queue = []
        if not self.future:
            return

        self.future.set_result(events)
        self.future = None

    def push(self, event: core_events.Event) -> None:
        # Deduplicate events
        while True:
            duplicates = [e for e in self.queue if event.is_duplicate(e)]
            if not duplicates:
                break

            for d in duplicates:
                self.queue.remove(d)
                logger.debug('dropping duplicate event %s from %s', d, self)

        # Ensure max queue size
        while len(self.queue) >= settings.core.event_queue_size:
            logger.warning('%s queue full, dropping oldest event', self)
            self.queue.pop()

        self.queue.insert(0, event)

    def __str__(self) -> str:
        return f'session {self.id}'


class SessionsEventHandler(core_events.Handler):
    def __init__(self, sessions_by_id: Dict[str, Session]) -> None:
        self._sessions_by_id: Dict[str, Session] = sessions_by_id

    async def handle_event(self, event: core_events.Event) -> None:
        for session in self._sessions_by_id.values():
            if session.access_level < event.REQUIRED_ACCESS:
                continue

            session.push(event)


def get(session_id: str) -> Session:
    session = _sessions_by_id.get(session_id)
    if not session:
        session = Session(session_id)
        _sessions_by_id[session_id] = session
        logger.debug('%s created', session)

    return session


def update() -> None:
    now = time.time()
    for session_id, session in list(_sessions_by_id.items()):
        if not session.is_empty() and session.is_active():
            session.respond()
            continue

        if now - session.accessed > session.timeout:
            if session.is_active():
                logger.debug('%s keep-alive', session)
                session.respond()

            else:
                logger.debug('%s expired', session)
                _sessions_by_id.pop(session_id)


async def init() -> None:
    global _sessions_event_handler

    _sessions_event_handler = SessionsEventHandler(_sessions_by_id)
    core_events.register_handler(_sessions_event_handler)


async def cleanup() -> None:
    pass
