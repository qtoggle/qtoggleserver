
import asyncio

import time
import logging
import queue

from qtoggleserver import settings


logger = logging.getLogger(__name__)

_sessions_by_id = {}


class Session:
    def __init__(self, session_id):
        self.id = session_id
        self.accessed = 0
        self.timeout = 0
        self.access_level = 0
        self.future = None
        self.queue = queue.Queue()

    def reset_and_wait(self, timeout, access_level):
        logger.debug('resetting %s (timeout=%s, access_level=%s)', self, timeout, access_level)

        if self.future:
            logger.debug('%s already has a listening connection, responding', self)
            self.respond()

        future = asyncio.get_running_loop().create_future()

        self.accessed = time.time()
        self.timeout = timeout
        self.access_level = access_level
        self.future = future

        if not self.queue.empty():
            logger.debug('%s has queued events, responding right away', self)
            self.respond()

        return future

    def is_empty(self):
        return self.queue.empty()

    def is_active(self):
        return self.future is not None

    def respond(self):
        events = []
        while not self.queue.empty():
            event = self.queue.get()
            events.append(event)

        if not self.future:
            return

        self.future.set_result(events)
        self.future = None

    def push(self, event):
        while self.queue.qsize() >= settings.core.event_queue_size:
            logger.debug('%s queue full, dropping oldest event', self)
            self.queue.get(block=False)

        self.queue.put(event)

    def __str__(self):
        return 'session {}'.format(self.id)


def get(session_id):
    session = _sessions_by_id.get(session_id)
    if not session:
        session = Session(session_id)
        _sessions_by_id[session_id] = session
        logger.debug('%s created', session)

    return session


def push(event):
    logger.debug('%s triggered', event)

    for session in _sessions_by_id.values():
        if session.access_level < event.REQUIRED_ACCESS:
            continue

        session.push(event)


def respond_non_empty():
    for session in _sessions_by_id.values():
        if session.is_empty():
            continue

        if not session.is_active():
            continue

        session.respond()


def cleanup():
    now = time.time()
    for session_id, session in list(_sessions_by_id.items()):
        if now - session.accessed > session.timeout:
            if session.is_active():
                logger.debug('%s keep-alive', session)
                session.respond()

            else:
                logger.debug('%s expired', session)
                _sessions_by_id.pop(session_id)
