import asyncio

from collections import deque

import pytest

from qtoggleserver.core.sessions import Session


class MockEvent:
    """A simple event stub with configurable duplicate behavior."""

    REQUIRED_ACCESS = 0

    def __init__(self, name: str, duplicate_of: "MockEvent | list[MockEvent] | None" = None) -> None:
        self.name = name
        if duplicate_of is None:
            self._duplicate_of: list[MockEvent] = []
        elif isinstance(duplicate_of, list):
            self._duplicate_of = duplicate_of
        else:
            self._duplicate_of = [duplicate_of]

    def is_duplicate(self, other: "MockEvent") -> bool:
        return other in self._duplicate_of or self in other._duplicate_of

    def __repr__(self) -> str:
        return f"MockEvent({self.name!r})"


@pytest.fixture
def session() -> Session:
    return Session("test-session")


class TestSessionIsEmpty:
    def test_empty_on_creation(self, session):
        """Should be empty when first created."""

        assert session.is_empty()

    def test_not_empty_after_push(self, session):
        """Should not be empty after an event is pushed."""

        session.push(MockEvent("e1"))
        assert not session.is_empty()

    def test_empty_after_respond(self, session):
        """Should be empty after responding (queue is cleared)."""

        session.push(MockEvent("e1"))
        session.respond()
        assert session.is_empty()


class TestSessionIsActive:
    async def test_inactive_on_creation(self, session):
        """Should be inactive when first created (no future set)."""

        assert not session.is_active()

    async def test_active_after_reset_and_wait(self, session):
        """Should be active after reset_and_wait is called."""

        future = session.reset_and_wait(timeout=30, access_level=0)
        assert session.is_active()
        future.cancel()

    async def test_inactive_after_respond(self, session):
        """Should become inactive after responding."""

        future = session.reset_and_wait(timeout=30, access_level=0)
        session.respond()
        assert not session.is_active()
        assert future.done()


class TestSessionResetAndWait:
    async def test_returns_future(self, session):
        """Should return an asyncio.Future."""

        future = session.reset_and_wait(timeout=30, access_level=0)
        assert isinstance(future, asyncio.Future)
        future.cancel()

    async def test_sets_timeout_and_access_level(self, session):
        """Should store the provided timeout and access_level on the session."""

        future = session.reset_and_wait(timeout=60, access_level=3)
        assert session.timeout == 60
        assert session.access_level == 3
        future.cancel()

    async def test_existing_future_is_resolved(self, session):
        """Should resolve the existing future when reset_and_wait is called again."""

        future1 = session.reset_and_wait(timeout=30, access_level=0)
        future2 = session.reset_and_wait(timeout=30, access_level=0)
        assert future1.done()
        assert not future2.done()
        future2.cancel()

    async def test_queued_events_trigger_immediate_respond(self, session):
        """Should respond immediately if there are queued events at reset_and_wait time."""

        session.push(MockEvent("e1"))
        future = session.reset_and_wait(timeout=30, access_level=0)
        assert future.done()
        assert session.is_empty()


class TestSessionRespond:
    async def test_clears_queue(self, session):
        """Should clear the queue after responding."""

        session.push(MockEvent("e1"))
        session.push(MockEvent("e2"))
        session.respond()
        assert session.is_empty()

    async def test_resolves_future_with_events(self, session):
        """Should resolve the future with the queued events in oldest-first order."""

        e1 = MockEvent("e1")
        e2 = MockEvent("e2")
        e3 = MockEvent("e3")
        session.push(e1)
        session.push(e2)
        session.push(e3)

        future = session.reset_and_wait(timeout=30, access_level=0)
        # reset_and_wait responds immediately since the queue is already populated
        result = list(future.result())
        assert result == [e1, e2, e3]

    async def test_no_future_does_not_raise(self, session):
        """Should not raise if respond is called with no active future."""

        session.push(MockEvent("e1"))
        session.respond()  # no future, should be a no-op


class TestSessionPush:
    def test_event_is_queued(self, session):
        """Should add the event to the queue."""

        e = MockEvent("e1")
        session.push(e)
        assert e in session.queue

    def test_multiple_events_newest_first(self, session):
        """Should queue events with the newest at the front."""

        e1 = MockEvent("e1")
        e2 = MockEvent("e2")
        session.push(e1)
        session.push(e2)
        assert list(session.queue) == [e2, e1]

    def test_duplicate_is_dropped(self, session):
        """Should remove the existing event when a duplicate is pushed."""

        e1 = MockEvent("e1")
        e2 = MockEvent("e2", duplicate_of=e1)
        session.push(e1)
        session.push(e2)
        assert len(session.queue) == 1
        assert e2 in session.queue
        assert e1 not in session.queue

    def test_multiple_duplicates_all_dropped(self, session):
        """Should remove all existing events that the new event considers duplicates of."""

        e1 = MockEvent("e1")
        e2 = MockEvent("e2")
        e3 = MockEvent("e3", duplicate_of=[e1, e2])
        session.push(e1)
        session.push(e2)
        session.push(e3)
        assert len(session.queue) == 1
        assert e3 in session.queue
        assert e1 not in session.queue
        assert e2 not in session.queue

    def test_non_duplicate_is_not_dropped(self, session):
        """Should keep a non-duplicate event in the queue when a new event is pushed."""

        e1 = MockEvent("e1")
        e2 = MockEvent("e2")
        session.push(e1)
        session.push(e2)
        assert e1 in session.queue
        assert e2 in session.queue

    def test_queue_size_limit_drops_oldest(self, session, mocker):
        """Should drop the oldest event when the queue is full."""

        mocker.patch("qtoggleserver.core.sessions.settings.core.event_queue_size", 3)
        e1 = MockEvent("e1")
        e2 = MockEvent("e2")
        e3 = MockEvent("e3")
        e4 = MockEvent("e4")
        session.push(e1)
        session.push(e2)
        session.push(e3)
        session.push(e4)
        assert len(session.queue) == 3
        assert e1 not in session.queue  # e1 is the oldest, dropped first
        assert e4 in session.queue

    def test_queue_uses_deque(self, session):
        """Queue should be a deque instance."""

        assert isinstance(session.queue, deque)
