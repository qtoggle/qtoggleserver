from __future__ import annotations

import asyncio
import logging
import time

from typing import Optional

from qtoggleserver.conf import settings
from qtoggleserver.core import events as core_events
from qtoggleserver.utils import logging as logging_utils


SESSION_EXPIRY_FACTOR = 10

logger = logging.getLogger(__name__)

_sessions_by_id: dict[str, Session] = {}
_sessions_event_handler: Optional[SessionsEventHandler] = None


class Session(logging_utils.LoggableMixin):
    def __init__(self, session_id: str) -> None:
        logging_utils.LoggableMixin.__init__(self, session_id, logger)

        self.id: str = session_id
        self.accessed: int = 0
        self.timeout: int = 0
        self.access_level: int = 0
        self.future: Optional[asyncio.Future] = None
        self.queue: list[core_events.Event] = []

    def reset_and_wait(self, timeout: int, access_level: int) -> asyncio.Future:
        self.debug('resetting (timeout=%s, access_level=%s)', timeout, access_level)

        if self.future:
            self.debug('already has a listening connection, responding')
            self.respond()

        future = asyncio.get_running_loop().create_future()

        self.accessed = time.time()
        self.timeout = timeout
        self.access_level = access_level
        self.future = future

        if self.queue:
            self.debug('has queued events, responding right away')
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

        self.debug('serving %d events', len(events))
        self.future.set_result(reversed(events))
        self.future = None

    def push(self, event: core_events.Event) -> None:
        # Deduplicate events
        while True:
            duplicates = [e for e in self.queue if event.is_duplicate(e)]
            if not duplicates:
                break

            for d in duplicates:
                self.queue.remove(d)
                self.debug('dropping duplicate event %s', d)

        # Ensure max queue size
        while len(self.queue) >= settings.core.event_queue_size:
            # This is a debug and not a warning because we often expect event drops from queues belonging to sessions
            # that are no longer active and will simply no longer consume the events
            self.debug('queue full, dropping oldest event')
            self.queue.pop()

        self.queue.insert(0, event)

    def __str__(self) -> str:
        return f'session {self.id}'


class SessionsEventHandler(core_events.Handler):
    FIRE_AND_FORGET = False

    def __init__(self, sessions_by_id: dict[str, Session]) -> None:
        self._sessions_by_id: dict[str, Session] = sessions_by_id

        super().__init__()

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
        session.debug('created')

    return session


def update() -> None:
    now = time.time()
    for session_id, session in list(_sessions_by_id.items()):
        if not session.is_empty() and session.is_active():
            session.respond()
            continue

        if now - session.accessed > session.timeout and session.is_active():
            session.debug('keep-alive')
            session.respond()
        elif now - session.accessed > session.timeout * SESSION_EXPIRY_FACTOR and not session.is_active():
            session.debug('expired')
            _sessions_by_id.pop(session_id)


async def init() -> None:
    global _sessions_event_handler

    _sessions_event_handler = SessionsEventHandler(_sessions_by_id)
    core_events.register_handler(_sessions_event_handler)


async def cleanup() -> None:
    pass
