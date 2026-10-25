import asyncio
import logging

import pytest

from qtoggleserver.conf import settings
from qtoggleserver.core import expressions
from qtoggleserver.core.expressions.exceptions import ValueUnavailable
from qtoggleserver.core.ports import PortDisabled, PortWriteError, WriteRequest


class TestPortGetLastValue:
    def test_pending(self, mock_num_port1, mocker):
        """Should return the pending value, since it's not None."""

        mocker.patch.object(mock_num_port1, "get_pending_value", return_value=100)
        mock_num_port1._last_written_value = None
        mock_num_port1._last_read_value = None
        assert mock_num_port1.get_last_value() == 100

        mock_num_port1._last_written_value = (200, 2000)
        mock_num_port1._last_read_value = (300, 1000)
        assert mock_num_port1.get_last_value() == 100

    def test_last_written(self, mock_num_port1, mocker):
        """Should return the last written value."""

        mocker.patch.object(mock_num_port1, "get_pending_value", return_value=None)
        mock_num_port1._last_written_value = (200, 2000)
        mock_num_port1._last_read_value = None
        assert mock_num_port1.get_last_value() == 200

        mock_num_port1._last_read_value = (300, 1000)  # older timestamp
        assert mock_num_port1.get_last_value() == 200

    def test_last_read(self, mock_num_port1, mocker):
        """Should return the last read value."""

        mocker.patch.object(mock_num_port1, "get_pending_value", return_value=None)
        mock_num_port1._last_written_value = None
        mock_num_port1._last_read_value = (300, 2000)
        assert mock_num_port1.get_last_value() == 300

        mock_num_port1._last_written_value = (200, 1000)  # newer timestamp
        assert mock_num_port1.get_last_value() == 300


class TestPortPushWrite:
    def test(self, mock_num_port1, mocker):
        """Should append the value to the write queue and mark the port for saving."""

        mocker.patch.object(mock_num_port1, "save_asap")
        mock_num_port1._write_queue.clear()

        mock_num_port1.push_write(100)

        assert list(mock_num_port1._write_queue) == [WriteRequest(100)]
        mock_num_port1.save_asap.assert_called_once()

    def test_multiple(self, mock_num_port1, mocker):
        """Should append every pushed value to the write queue, in order."""

        mocker.patch.object(mock_num_port1, "save_asap")
        mock_num_port1._write_queue.clear()

        mock_num_port1.push_write(100)
        mock_num_port1.push_write(200)

        assert list(mock_num_port1._write_queue) == [WriteRequest(100), WriteRequest(200)]
        assert mock_num_port1.save_asap.call_count == 2

    def test_with_future(self, mock_num_port1, mocker):
        """Should attach the given future to the queued write request."""

        mocker.patch.object(mock_num_port1, "save_asap")
        mock_num_port1._write_queue.clear()
        future = asyncio.get_event_loop().create_future()

        mock_num_port1.push_write(100, future=future)

        assert list(mock_num_port1._write_queue) == [WriteRequest(100, future)]

    def test_evicts_oldest_when_full(self, mock_num_port1, mocker):
        """Should fail the future of the oldest request when it gets evicted because the queue is full."""

        mocker.patch.object(mock_num_port1, "save_asap")
        mock_num_port1._write_queue.clear()
        evicted_future = asyncio.get_event_loop().create_future()
        mock_num_port1.push_write(1, future=evicted_future)
        for value in range(2, mock_num_port1._write_queue.maxlen + 1):
            mock_num_port1.push_write(value)

        mock_num_port1.push_write(999)

        assert isinstance(evicted_future.exception(), PortWriteError)
        assert list(mock_num_port1._write_queue)[0].value == 2  # noqa: RUF015
        assert list(mock_num_port1._write_queue)[-1].value == 999


class TestPortWriteQueueOrder:
    async def test_writes_in_push_order(self, mock_num_port1, mocker):
        """Should write queued values oldest first, and leave the port holding the newest one."""

        written = []

        async def record(value):
            written.append(value)

        mocker.patch.object(mock_num_port1, "write_value", new=record)
        mock_num_port1._write_queue.clear()

        for value in (1, 2, 3):
            mock_num_port1.push_write(value)

        assert mock_num_port1.get_pending_value() == 3

        await asyncio.sleep(5 * settings.core.tick_interval / 1000)

        assert written == [1, 2, 3]
        assert mock_num_port1.get_last_written_value() == 3

    async def test_writes_persisted_queue_in_order(self, mock_num_port1, mocker):
        """Should write a queue restored from persisted data in the order it was persisted."""

        written = []

        async def record(value):
            written.append(value)

        mocker.patch.object(mock_num_port1, "write_value", new=record)
        mock_num_port1._write_queue.clear()

        await mock_num_port1.from_persisted({"write_queue": [1, 2, 3]})
        await asyncio.sleep(5 * settings.core.tick_interval / 1000)

        assert written == [1, 2, 3]


class TestPortAdaptValueType:
    @pytest.mark.parametrize(
        "value, expected",
        [
            (21.299999999999997, 21.3),
            (0.30000000000000004, 0.3),
            (21.3, 21.3),
            (1e-20, 1e-20),
            (123456789012.345, 123456789012.345),
            (5, 5.0),
        ],
    )
    def test_float_drops_noise(self, value, expected, mock_num_port1):
        assert mock_num_port1.adapt_value_type(value) == expected

    @pytest.mark.parametrize("value, expected", [(28.999999999999996, 29), (2.9, 2), (-2.9, -2), (7, 7)])
    def test_integer_truncates_without_noise(self, value, expected, mock_num_port1, mocker):
        mocker.patch.object(mock_num_port1, "is_integer", return_value=True)
        assert mock_num_port1.adapt_value_type(value) == expected

    async def test_transform_round_trip(self, mock_num_port1, mocker):
        """A value written with `DIV($, 10)` and read back with `MUL($, 10)` should read as the written value."""

        written = []
        mocker.patch.object(mock_num_port1, "write_value", side_effect=lambda v: written.append(v))
        mock_num_port1._transform_write = expressions.parse("nid1", "DIV($, 10)", role=expressions.Role.TRANSFORM_WRITE)
        mock_num_port1._transform_read = expressions.parse("nid1", "MUL($, 10)", role=expressions.Role.TRANSFORM_READ)

        await mock_num_port1.transform_and_write_value(21.3)
        mock_num_port1.set_next_value(written[0])

        assert await mock_num_port1.read_transformed_value() == 21.3

    def test_integer_keeps_large_int_exact(self, mock_num_port1, mocker):
        mocker.patch.object(mock_num_port1, "is_integer", return_value=True)
        assert mock_num_port1.adapt_value_type(2**60) == 2**60

    def test_boolean(self, mock_bool_port1):
        assert mock_bool_port1.adapt_value_type(1) is True

    def test_none(self, mock_num_port1):
        assert mock_num_port1.adapt_value_type(None) is None


class TestPortPushWriteAndWait:
    async def test_resolves_on_success(self, mock_num_port1, mocker):
        """Should return once the pushed value has actually been written, without raising."""

        mock_num_port1._write_queue.clear()
        mocker.patch.object(mock_num_port1, "transform_and_write_value", new=mocker.AsyncMock())

        await mock_num_port1.push_write_and_wait(100)

        mock_num_port1.transform_and_write_value.assert_called_once_with(100)

    async def test_raises_on_failure(self, mock_num_port1, mocker):
        """Should propagate any exception raised while writing the value."""

        mock_num_port1._write_queue.clear()
        mocker.patch.object(
            mock_num_port1, "transform_and_write_value", new=mocker.AsyncMock(side_effect=ValueError("nope"))
        )

        try:
            await mock_num_port1.push_write_and_wait(100)
            assert False, "expected ValueError to be raised"
        except ValueError as e:
            assert str(e) == "nope"

    async def test_logs_failed_write_once(self, mock_num_port1, mocker, caplog):
        mock_num_port1._write_queue.clear()
        mocker.patch.object(mock_num_port1, "write_value", new=mocker.AsyncMock(side_effect=ValueError("nope")))

        with caplog.at_level(logging.ERROR), pytest.raises(ValueError):
            await mock_num_port1.push_write_and_wait(100)

        assert [r.getMessage() for r in caplog.records] == ["failed to write value 100"]

    async def test_logs_failed_write_transform_once(self, mock_num_port1, mocker, caplog):
        mock_num_port1._write_queue.clear()
        mock_num_port1._transform_write = mocker.MagicMock()
        mock_num_port1._transform_write.eval = mocker.AsyncMock(side_effect=ValueError("nope"))

        with caplog.at_level(logging.ERROR), pytest.raises(ValueError):
            await mock_num_port1.push_write_and_wait(100)

        assert [r.getMessage() for r in caplog.records] == ["failed to apply write transform to value 100"]

    async def test_cleanup_fails_pending_futures(self, mock_num_port1, mocker):
        """Should fail the future of the request currently being written, as well as those of any requests still
        sitting in the queue, when the write loop is cancelled (e.g. on port removal). Failed rather than cancelled,
        so that the awaiting API handler can actually catch it."""

        mock_num_port1._write_queue.clear()
        started = asyncio.Event()
        release = asyncio.Event()

        async def blocking_transform(value):
            started.set()
            await release.wait()

        mocker.patch.object(mock_num_port1, "transform_and_write_value", new=blocking_transform)

        future_a = asyncio.get_event_loop().create_future()
        future_b = asyncio.get_event_loop().create_future()
        mock_num_port1.push_write(1, future=future_a)
        mock_num_port1.push_write(2, future=future_b)

        await started.wait()  # one of the two requests is now being (indefinitely) written
        await mock_num_port1.cleanup()

        assert isinstance(future_a.exception(), PortWriteError)
        assert isinstance(future_b.exception(), PortWriteError)
        assert not future_a.cancelled()
        assert not future_b.cancelled()
        # A shared instance would carry the traceback of whichever awaiter raised it first
        assert future_a.exception() is not future_b.exception()


class TestPortDisabledWrites:
    async def test_disable_drops_queued_writes(self, mock_num_port1, mocker):
        """Should drop any queued write when the port gets disabled, since a disabled port can't be written to."""

        mocker.patch.object(mock_num_port1, "transform_and_write_value", new=mocker.AsyncMock())
        mock_num_port1._write_queue.clear()
        mock_num_port1.push_write(100)

        await mock_num_port1.disable()

        assert len(mock_num_port1._write_queue) == 0
        await asyncio.sleep(settings.core.tick_interval / 1000)
        mock_num_port1.transform_and_write_value.assert_not_called()

    async def test_disable_fails_dropped_futures(self, mock_num_port1, mocker):
        """Should fail the futures of the dropped writes, so that no caller is left hanging."""

        mocker.patch.object(mock_num_port1, "transform_and_write_value", new=mocker.AsyncMock())
        mock_num_port1._write_queue.clear()
        future = asyncio.get_event_loop().create_future()
        mock_num_port1.push_write(100, future=future)

        await mock_num_port1.disable()

        assert isinstance(future.exception(), PortDisabled)

    async def test_disable_raises_catchable_error_for_awaiter(self, mock_num_port1, mocker):
        """Should raise PortDisabled, not CancelledError, in a caller awaiting a dropped write. CancelledError is a
        BaseException and would slip through the `except Exception` handlers on the API path."""

        started = asyncio.Event()
        release = asyncio.Event()

        async def blocking_transform(value):
            started.set()
            await release.wait()

        mocker.patch.object(mock_num_port1, "transform_and_write_value", new=blocking_transform)
        mock_num_port1._write_queue.clear()
        mock_num_port1.push_write(1)  # keeps the write loop busy
        await started.wait()

        async def awaiter():
            try:
                await mock_num_port1.push_write_and_wait(100)
            except Exception as e:
                return e

            return None

        task = asyncio.ensure_future(awaiter())
        await asyncio.sleep(0)
        await mock_num_port1.disable()

        # The timeout keeps a regression here a quick failure rather than a hung test run
        assert isinstance(await asyncio.wait_for(asyncio.shield(task), timeout=1), PortDisabled)
        assert not task.cancelled()

    async def test_failed_disable_keeps_queued_writes(self, mock_num_port1, mocker):
        """Should keep the queued writes when disabling fails, since the port stays enabled."""

        mocker.patch.object(mock_num_port1, "handle_disable", new=mocker.AsyncMock(side_effect=ValueError("nope")))
        mock_num_port1._write_queue.clear()
        mock_num_port1.push_write(100)

        try:
            await mock_num_port1.disable()
            assert False, "expected ValueError to be raised"
        except ValueError:
            pass

        assert mock_num_port1.is_enabled()
        assert len(mock_num_port1._write_queue) == 1

    async def test_push_write_refused_while_disabled(self, mock_num_port1, mocker):
        """Should refuse to queue a value for a disabled port, instead of holding it until the port gets enabled."""

        mocker.patch.object(mock_num_port1, "transform_and_write_value", new=mocker.AsyncMock())
        mock_num_port1._write_queue.clear()
        await mock_num_port1.disable()

        future = asyncio.get_event_loop().create_future()
        mock_num_port1.push_write(100, future=future)

        assert len(mock_num_port1._write_queue) == 0
        assert isinstance(future.exception(), PortDisabled)

        await mock_num_port1.enable()
        await asyncio.sleep(2 * settings.core.tick_interval / 1000)
        mock_num_port1.transform_and_write_value.assert_not_called()

    async def test_nothing_written_while_disabling(self, mock_num_port1, mocker):
        """Should neither write nor drop a queued value while `handle_disable()` is suspended. This is the invariant
        the whole change rests on: the port already reports itself as disabled there, so the write loop must leave
        the queue alone and let `disable()` decide what happens to it."""

        written = []

        async def record(value):
            written.append(value)

        mocker.patch.object(mock_num_port1, "write_value", new=record)
        mock_num_port1._write_queue.clear()

        suspended = asyncio.Event()
        release = asyncio.Event()

        async def slow_handle_disable():
            suspended.set()
            await release.wait()

        mocker.patch.object(mock_num_port1, "handle_disable", new=slow_handle_disable)
        mock_num_port1.push_write(100)

        task = asyncio.ensure_future(mock_num_port1.disable())
        await suspended.wait()
        await asyncio.sleep(4 * settings.core.tick_interval / 1000)  # several turns for the write loop

        assert not mock_num_port1.is_enabled()
        assert written == []  # held, not written
        assert len(mock_num_port1._write_queue) == 1  # and not dropped behind `disable()`'s back

        release.set()
        await task

        assert written == []
        assert len(mock_num_port1._write_queue) == 0  # dropped by `disable()`, now that it is done

    async def test_disable_rollback_keeps_queued_write(self, mock_num_port1, mocker):
        """Should keep the queued writes when a suspending `handle_disable()` then fails. The write loop gets a turn
        while the port already reports itself as disabled, and must not drop the queue in that window."""

        written = []

        async def record(value):
            written.append(value)

        mocker.patch.object(mock_num_port1, "transform_and_write_value", new=record)
        mock_num_port1._write_queue.clear()

        async def slow_failing_handle_disable():
            await asyncio.sleep(4 * settings.core.tick_interval / 1000)  # as for a polled or peripheral port
            raise ValueError("nope")

        mocker.patch.object(mock_num_port1, "handle_disable", new=slow_failing_handle_disable)
        future = asyncio.get_event_loop().create_future()
        mock_num_port1.push_write(100, future=future)

        try:
            await mock_num_port1.disable()
            assert False, "expected ValueError to be raised"
        except ValueError:
            pass

        assert mock_num_port1.is_enabled()
        await asyncio.sleep(2 * settings.core.tick_interval / 1000)
        assert written == [100]
        assert future.done() and future.exception() is None

    async def test_disable_keeps_queue_when_re_enabled_meanwhile(self, mock_num_port1, mocker):
        """Should keep the queued writes when the port gets enabled again while `handle_disable()` is suspended,
        instead of failing a live port's writes with PortDisabled."""

        written = []

        async def record(value):
            written.append(value)

        mocker.patch.object(mock_num_port1, "transform_and_write_value", new=record)
        mock_num_port1._write_queue.clear()

        async def slow_reenabling_handle_disable():
            await asyncio.sleep(4 * settings.core.tick_interval / 1000)
            await mock_num_port1.enable()

        mocker.patch.object(mock_num_port1, "handle_disable", new=slow_reenabling_handle_disable)
        future = asyncio.get_event_loop().create_future()
        mock_num_port1.push_write(100, future=future)

        await mock_num_port1.disable()

        assert mock_num_port1.is_enabled()
        await asyncio.sleep(2 * settings.core.tick_interval / 1000)
        assert written == [100]
        assert future.done() and future.exception() is None

    async def test_cancelled_disable_drops_queued_writes(self, mock_num_port1, mocker):
        """Should drop the queued writes when `disable()` is cancelled while `handle_disable()` is suspended. The
        port stays disabled there, so without this the write loop would hold the queue and the awaiter would wait
        forever."""

        mocker.patch.object(mock_num_port1, "transform_and_write_value", new=mocker.AsyncMock())
        mock_num_port1._write_queue.clear()

        async def slow_handle_disable():
            await asyncio.sleep(10)

        mocker.patch.object(mock_num_port1, "handle_disable", new=slow_handle_disable)
        future = asyncio.get_event_loop().create_future()
        mock_num_port1.push_write(100, future=future)

        task = asyncio.ensure_future(mock_num_port1.disable())
        await asyncio.sleep(2 * settings.core.tick_interval / 1000)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

        assert not mock_num_port1.is_enabled()
        assert len(mock_num_port1._write_queue) == 0
        assert isinstance(future.exception(), PortDisabled)

    async def test_failed_enable_does_not_strand_queued_write(self, mock_num_port1, mocker):
        """Should not strand a write queued while `enable()` was running, when that enable then rolls back. The port
        reports itself as enabled until the rollback, so the core loop can push a value in that window."""

        mocker.patch.object(mock_num_port1, "transform_and_write_value", new=mocker.AsyncMock())
        await mock_num_port1.disable()
        mock_num_port1._write_queue.clear()
        future = asyncio.get_event_loop().create_future()

        async def failing_handle_enable():
            mock_num_port1.push_write(100, future=future)
            raise ValueError("nope")

        mocker.patch.object(mock_num_port1, "handle_enable", new=failing_handle_enable)

        try:
            await mock_num_port1.enable()
            assert False, "expected ValueError to be raised"
        except ValueError:
            pass

        assert not mock_num_port1.is_enabled()
        await asyncio.sleep(2 * settings.core.tick_interval / 1000)
        assert isinstance(future.exception(), PortDisabled)
        mock_num_port1.transform_and_write_value.assert_not_called()


class TestPortWaitForReadValue:
    async def test_returns_true_immediately_if_already_matching(self, mock_num_port1):
        mock_num_port1.set_read_value(100)
        assert await mock_num_port1.wait_for_read_value(100, timeout=1) is True

    async def test_returns_false_immediately_for_nonpositive_timeout_without_match(self, mock_num_port1):
        mock_num_port1.set_read_value(0)
        assert await mock_num_port1.wait_for_read_value(100, timeout=0) is False

    async def test_resolves_when_matching_value_is_later_read(self, mock_num_port1):
        mock_num_port1.set_read_value(0)

        async def delayed_read():
            await asyncio.sleep(0.01)
            mock_num_port1.set_read_value(100)

        task = asyncio.create_task(delayed_read())
        try:
            assert await mock_num_port1.wait_for_read_value(100, timeout=1) is True
        finally:
            await task

    async def test_ignores_non_matching_values(self, mock_num_port1):
        """A read value that doesn't match the target shouldn't resolve the wait."""

        mock_num_port1.set_read_value(0)

        async def delayed_reads():
            await asyncio.sleep(0.01)
            mock_num_port1.set_read_value(50)
            await asyncio.sleep(0.01)
            mock_num_port1.set_read_value(100)

        task = asyncio.create_task(delayed_reads())
        try:
            assert await mock_num_port1.wait_for_read_value(100, timeout=1) is True
        finally:
            await task

    async def test_times_out_without_match(self, mock_num_port1):
        mock_num_port1.set_read_value(0)
        assert await mock_num_port1.wait_for_read_value(100, timeout=0.02) is False

    async def test_cleans_up_waiter_after_resolving(self, mock_num_port1):
        mock_num_port1.set_read_value(0)

        async def delayed_read():
            await asyncio.sleep(0.01)
            mock_num_port1.set_read_value(100)

        task = asyncio.create_task(delayed_read())
        try:
            await mock_num_port1.wait_for_read_value(100, timeout=1)
        finally:
            await task
        assert mock_num_port1._value_match_waiters == []

    async def test_cleans_up_waiter_after_timeout(self, mock_num_port1):
        mock_num_port1.set_read_value(0)
        await mock_num_port1.wait_for_read_value(100, timeout=0.02)
        assert mock_num_port1._value_match_waiters == []


class TestPortSetSequence:
    async def test_pushes_each_value_via_push_write(self, mock_num_port1, mocker):
        """Should install a sequence that pushes each value to the write queue via push_write."""

        spy = mocker.spy(mock_num_port1, "push_write")

        await mock_num_port1.set_sequence([1, 2, 3], [1, 1, 1], 1)
        loop_task = mock_num_port1._sequence._loop_task
        await loop_task

        assert spy.call_args_list == [mocker.call(1), mocker.call(2), mocker.call(3)]

    async def test_clears_sequence_and_saves_when_finished(self, mock_num_port1, mocker):
        """Should clear the sequence and mark the port for saving once the sequence finishes."""

        mocker.patch.object(mock_num_port1, "save_asap")

        await mock_num_port1.set_sequence([1], [1], 1)
        loop_task = mock_num_port1._sequence._loop_task
        await loop_task

        assert mock_num_port1._sequence is None
        mock_num_port1.save_asap.assert_called()

    async def test_cancels_previous_sequence(self, mock_num_port1, mocker):
        """Should cancel any currently running sequence before installing a new one."""

        await mock_num_port1.set_sequence([1, 2], [1000, 1000], 1)
        old_sequence = mock_num_port1._sequence
        spy_cancel = mocker.spy(old_sequence, "cancel")

        await mock_num_port1.set_sequence([3], [1], 1)

        spy_cancel.assert_called_once()
        assert mock_num_port1._sequence is not old_sequence

        await mock_num_port1._sequence.cancel()

    async def test_empty_values_only_cancels(self, mock_num_port1, mocker):
        """Should cancel any existing sequence and not install a new one when values is empty."""

        await mock_num_port1.set_sequence([1, 2], [1000, 1000], 1)
        old_sequence = mock_num_port1._sequence
        spy_cancel = mocker.spy(old_sequence, "cancel")

        await mock_num_port1.set_sequence([], [], 1)

        spy_cancel.assert_called_once()
        assert mock_num_port1._sequence is None


class TestPortEvalAndPushWrite:
    async def test(self, mock_num_port1, mock_num_port2, mocker):
        """Should evaluate the expression with the provided eval context and push the result to the write queue."""

        mock_eval_context = mocker.Mock()
        mock_expression = mocker.Mock()
        mock_expression.eval = mocker.AsyncMock(return_value=99)
        mocker.patch.object(mock_num_port1, "get_expression", return_value=mock_expression)

        mocker.patch.object(mock_num_port1, "adapt_value_type", return_value=100)
        mocker.patch.object(mock_num_port1, "get_last_value", return_value=None)
        mocker.patch.object(mock_num_port1, "push_write")

        await mock_num_port1.eval_and_push_write(mock_eval_context)

        mock_expression.eval.assert_called_once_with(mock_eval_context)
        mock_num_port1.adapt_value_type.assert_called_once_with(mock_expression.eval.return_value)
        mock_num_port1.push_write.assert_called_once_with(100)

    async def test_same_as_last_value_not_written(self, mock_num_port1, mocker):
        """Should not push anything to the write queue if the evaluated value equals the last value."""

        mock_eval_context = mocker.Mock()
        mock_expression = mocker.Mock()
        mock_expression.eval = mocker.AsyncMock(return_value=99)
        mocker.patch.object(mock_num_port1, "get_expression", return_value=mock_expression)

        mocker.patch.object(mock_num_port1, "adapt_value_type", return_value=100)
        mocker.patch.object(mock_num_port1, "get_last_value", return_value=100)
        mocker.patch.object(mock_num_port1, "push_write")

        await mock_num_port1.eval_and_push_write(mock_eval_context)
        mock_num_port1.push_write.assert_not_called()

    async def test_unavailable_not_written(self, mock_num_port1, mocker):
        """Should not push anything to the write queue if the expression evaluation raises due to value being
        unavailable."""

        mock_eval_context = mocker.Mock()
        mock_num_port1._expression = mocker.Mock()
        mock_num_port1._expression.eval = mocker.AsyncMock(side_effect=ValueUnavailable)
        mocker.patch.object(mock_num_port1, "push_write")

        await mock_num_port1.eval_and_push_write(mock_eval_context)
        mock_num_port1.push_write.assert_not_called()


class TestPortGetPendingValue:
    def test_no_pending_value(self, mock_num_port1):
        """Should return `None` if there's no writing value and writing queue is empty."""

        mock_num_port1._writing_value = None
        assert mock_num_port1.get_pending_value() is None

    def test_with_queue(self, mock_num_port1):
        """Should return the most recent value from writing queue."""

        mock_num_port1._writing_value = 1
        mock_num_port1._write_queue.append(WriteRequest(2))
        mock_num_port1._write_queue.append(WriteRequest(3))
        mock_num_port1._write_queue.append(WriteRequest(4))
        assert mock_num_port1.get_pending_value() == 4

    def test_empty_queue(self, mock_num_port1):
        """Should return the currently writing value, since writing queue is empty."""

        mock_num_port1._writing_value = 1
        assert mock_num_port1.get_pending_value() == 1


class TestPortEnableDisable:
    async def test_enable_invalidates_attrs(self, mock_num_port1):
        """Should invalidate the whole attributes cache, since other attributes may be derived from `enabled`."""

        await mock_num_port1.disable()
        mock_num_port1._attrs_cache["display_name"] = "stale"

        await mock_num_port1.enable()

        assert "display_name" not in mock_num_port1._attrs_cache

    async def test_disable_invalidates_attrs(self, mock_num_port1):
        """Should invalidate the whole attributes cache, since other attributes may be derived from `enabled`."""

        await mock_num_port1.enable()
        mock_num_port1._attrs_cache["display_name"] = "stale"

        await mock_num_port1.disable()

        assert "display_name" not in mock_num_port1._attrs_cache


class TestPortGetAttr:
    async def test_unknown_attribute(self, mock_num_port1):
        """Should return `None` for an unsupported/unknown attribute."""

        assert await mock_num_port1.get_attr("unknown_attribute") is None

    async def test_cache(self, mock_num_port1, mocker):
        """Should return value from cache first, before trying any other sources."""

        class TempMockPort(type(mock_num_port1)):
            async def attr_get_display_name(self) -> str:
                return ""

            async def attr_get_default_display_name(self) -> str:
                raise AssertionError("Should not be called")

        mock_num_port2 = TempMockPort("tmp", None)
        mock_num_port2._display_name = "value1"
        mock_num_port2._attrs_cache["display_name"] = "value2"
        mocker.patch.object(mock_num_port2, "attr_get_display_name", return_value="value3")
        mocker.patch.object(mock_num_port2, "attr_get_value", return_value="value4")
        assert await mock_num_port2.get_attr("display_name") == "value2"
        mock_num_port2.attr_get_display_name.assert_not_called()
        mock_num_port2.attr_get_value.assert_not_called()

    async def test_call_attr_getter(self, mock_num_port1, mocker):
        """Should call the attribute getter method instead of returning the private property."""

        class TempMockPort(type(mock_num_port1)):
            async def attr_get_display_name(self) -> str:
                return ""

            def attr_get_sync_getter(self) -> str:
                return ""

            async def attr_is_boolean_getter(self) -> bool:
                return True

            def attr_is_sync_boolean_getter(self) -> bool:
                return True

            async def attr_get_default_display_name(self) -> str:
                raise AssertionError("Should not be called")

            def attr_get_default_sync_getter(self) -> str:
                raise AssertionError("Should not be called")

            async def attr_is_default_boolean_getter(self) -> bool:
                raise AssertionError("Should not be called")

            def attr_is_default_sync_boolean_getter(self) -> bool:
                raise AssertionError("Should not be called")

        mock_num_port2 = TempMockPort("tmp", None)
        mock_num_port2._display_name = "value1"
        mocker.patch.object(mock_num_port2, "attr_get_display_name", return_value="value2")
        mock_num_port2.invalidate_attrs()
        assert await mock_num_port2.get_attr("display_name") == "value2"
        mock_num_port2.attr_get_display_name.assert_called_once_with()

        mock_num_port2._sync_getter = "value1"
        mocker.patch.object(mock_num_port2, "attr_get_sync_getter", return_value="value2")
        mock_num_port2.invalidate_attrs()
        assert await mock_num_port2.get_attr("sync_getter") == "value2"
        mock_num_port2.attr_get_sync_getter.assert_called_once_with()

        mock_num_port2._boolean_getter = False
        mocker.patch.object(mock_num_port2, "attr_is_boolean_getter", return_value=True)
        mock_num_port2.invalidate_attrs()
        assert await mock_num_port2.get_attr("boolean_getter") is True
        mock_num_port2.attr_is_boolean_getter.assert_called_once_with()

        mock_num_port2._sync_boolean_getter = False
        mocker.patch.object(mock_num_port2, "attr_is_sync_boolean_getter", return_value=True)
        mock_num_port2.invalidate_attrs()
        assert await mock_num_port2.get_attr("sync_boolean_getter") is True
        mock_num_port2.attr_is_sync_boolean_getter.assert_called_once_with()

    async def test_read_property(self, mock_num_port1, mocker):
        """Should return the value stored in the private property, when no getter is defined and attribute is not
        cached."""

        class TempMockPort(type(mock_num_port1)):
            async def attr_get_default_display_name(self) -> str:
                raise AssertionError("Should not be called")

        mock_num_port2 = TempMockPort("tmp", None)
        mock_num_port2._display_name = "value1"
        mock_num_port2.invalidate_attrs()
        mocker.patch.object(mock_num_port2, "attr_get_value", return_value="value2")
        assert await mock_num_port2.get_attr("display_name") == "value1"
        mock_num_port2.attr_get_value.assert_not_called()

    async def test_call_attr_default_getter(self, mock_num_port1, mocker):
        """Should call the attribute *default* getter method, in the absence of any other source."""

        class TempMockPort(type(mock_num_port1)):
            async def attr_get_default_display_name(self) -> str:
                return ""

            def attr_get_default_sync_getter(self) -> str:
                return ""

            async def attr_is_default_boolean_getter(self) -> bool:
                return True

            def attr_is_default_sync_boolean_getter(self) -> bool:
                return True

        mock_num_port2 = TempMockPort("tmp", None)
        mock_num_port2._display_name = None
        mocker.patch.object(mock_num_port2, "attr_get_default_display_name", return_value="value2")
        mock_num_port2.invalidate_attrs()
        assert await mock_num_port2.get_attr("display_name") == "value2"
        mock_num_port2.attr_get_default_display_name.assert_called_once_with()

        mocker.patch.object(mock_num_port2, "attr_get_default_sync_getter", return_value="value2")
        assert await mock_num_port2.get_attr("sync_getter") == "value2"
        mock_num_port2.attr_get_default_sync_getter.assert_called_once_with()

        mocker.patch.object(mock_num_port2, "attr_is_default_boolean_getter", return_value=True)
        assert await mock_num_port2.get_attr("boolean_getter") is True
        mock_num_port2.attr_is_default_boolean_getter.assert_called_once_with()

        mocker.patch.object(mock_num_port2, "attr_is_default_sync_boolean_getter", return_value=True)
        assert await mock_num_port2.get_attr("sync_boolean_getter") is True
        mock_num_port2.attr_is_default_sync_boolean_getter.assert_called_once_with()


class TestPortSetAttr:
    async def test_unknown_attribute(self, mock_num_port1, mocker):
        """Should silently do nothing for an unsupported/unknown attribute."""

        mocker.patch.object(mock_num_port1, "attr_set_value")
        mock_num_port1.attr_set_value.assert_not_called()
        assert not hasattr(mock_num_port1, "_unknown_attribute")

    async def test_unchanged_value(self, mock_num_port1, mocker):
        """Should not do anything if supplied value is the same as existent one."""

        await mock_num_port1.set_attr("display_name", "some name")  # initial value
        mocker.patch.object(mock_num_port1, "attr_set_value")
        await mock_num_port1.set_attr("display_name", "some name")  # same value, repeated
        mock_num_port1.attr_set_value.assert_not_called()

        class TempMockPort(type(mock_num_port1)):
            async def attr_set_display_name(self, value: str) -> None:
                self._display_name = value

        mock_num_port2 = TempMockPort("tmp", None)
        await mock_num_port2.set_attr("display_name", "some name")  # initial value
        mocker.patch.object(mock_num_port2, "attr_set_display_name")
        await mock_num_port2.set_attr("display_name", "some name")  # same value
        mock_num_port2.attr_set_display_name.assert_not_called()

    async def test_unmodifiable(self, mock_num_port1):
        """Should not fail for an unmodifiable attribute, as the modifiable flag is handled elsewhere."""

        await mock_num_port1.set_attr("type", "inexistent-type")

    async def test_call_setter(self, mock_num_port1, mocker):
        """Should call the attribute setter method instead of changing the private property or calling
        `attr_set_value()`."""

        class TempMockPort(type(mock_num_port1)):
            async def attr_set_my_attribute(self, value: str) -> None:
                pass

        mock_num_port2 = TempMockPort("tmp", None)
        mock_num_port2._my_attribute = "value1"
        mocker.patch.object(mock_num_port2, "attr_set_value")
        mocker.patch.object(mock_num_port2, "attr_set_my_attribute")
        await mock_num_port2.set_attr("my_attribute", "value2")
        mock_num_port2.attr_set_value.assert_not_called()
        assert mock_num_port2._my_attribute == "value1"
        mock_num_port2.attr_set_my_attribute.assert_called_once_with("value2")

    async def test_assign_property(self, mock_num_port1, mocker):
        """Should assign private property instead of calling `attr_set_value()`."""

        mock_num_port1._my_attribute = "value1"
        mocker.patch.object(mock_num_port1, "attr_set_value")
        await mock_num_port1.set_attr("my_attribute", "value2")
        mock_num_port1.attr_set_value.assert_not_called()
        assert mock_num_port1._my_attribute == "value2"

    async def test_call_attr_set_value(self, mock_num_port1, mocker):
        """Should call `attr_set_value()`, since there's no dedicated attribute setter, nor a private property."""

        class TempMockPort(type(mock_num_port1)):
            async def attr_get_my_attribute(self) -> str:
                return "value1"

        mock_num_port2 = TempMockPort("tmp", None)
        mocker.patch.object(mock_num_port2, "attr_set_value")
        await mock_num_port2.set_attr("my_attribute", "value2")
        mock_num_port2.attr_set_value.assert_called_once_with("my_attribute", "value2")

    async def test_invalidate_cache(self, mock_num_port1, mocker):
        """Should invalidate attribute cache as well as attribute definitions cache."""

        mock_num_port1._my_attribute = "value1"
        mocker.patch.object(mock_num_port1, "invalidate_attrdefs")
        await mock_num_port1.set_attr("my_attribute", "value2")
        mock_num_port1.invalidate_attrdefs.assert_called_once()

    async def test_call_handle_attr_change(self, mock_num_port1, mocker):
        """Should call the `handle_attr_change` method."""

        mock_num_port1._my_attribute = "value1"
        mocker.patch.object(mock_num_port1, "handle_attr_change")
        await mock_num_port1.set_attr("my_attribute", "value2")
        await asyncio.sleep(0.1)
        mock_num_port1.handle_attr_change.assert_called_once_with("my_attribute", "value2")


class TestPortToJSON:
    async def test_definitions_filtered(self, mock_num_port1, mocker):
        """Should strip private (`_`-prefixed) fields and `pattern` from additional attrdefs in the result."""

        mocker.patch.object(
            mock_num_port1,
            "get_additional_attrdefs",
            return_value={
                "extra_attr": {
                    "type": "string",
                    "modifiable": True,
                    "pattern": "^.*$",
                    "_internal": "should_be_removed",
                },
            },
        )
        mock_num_port1._to_json_attrdefs_cache = None

        result = await mock_num_port1.to_json()

        assert "definitions" in result
        assert result["definitions"] == {
            "extra_attr": {
                "type": "string",
                "modifiable": True,
            },
        }

    async def test_additional_attrdefs_cached(self, mock_num_port1, mocker):
        """Should compute filtered additional attrdefs only once; subsequent calls reuse the cached object."""

        mocker.patch.object(
            mock_num_port1,
            "get_additional_attrdefs",
            return_value={
                "extra_attr": {
                    "type": "string",
                    "modifiable": True,
                    "pattern": "^.*$",
                },
            },
        )
        mock_num_port1._to_json_attrdefs_cache = None

        result1 = await mock_num_port1.to_json()
        result2 = await mock_num_port1.to_json()

        assert result1["definitions"] is result2["definitions"]
        mock_num_port1.get_additional_attrdefs.assert_called_once()

    async def test_invalidate_attrdefs_clears_cache(self, mock_num_port1, mocker):
        """Should recompute additional attrdefs after `invalidate_attrdefs()` is called."""

        call_count = 0
        attrdefs_versions = [
            {"extra_attr": {"type": "string", "modifiable": True}},
            {"extra_attr": {"type": "number", "modifiable": False}},
        ]

        async def get_additional_attrdefs():
            nonlocal call_count
            r = attrdefs_versions[min(call_count, 1)]
            call_count += 1
            return r

        mocker.patch.object(mock_num_port1, "get_additional_attrdefs", side_effect=get_additional_attrdefs)
        mock_num_port1._to_json_attrdefs_cache = None

        result1 = await mock_num_port1.to_json()
        mock_num_port1.invalidate_attrdefs()
        result2 = await mock_num_port1.to_json()

        assert result1["definitions"]["extra_attr"]["type"] == "string"
        assert result2["definitions"]["extra_attr"]["type"] == "number"
        assert result1["definitions"] is not result2["definitions"]


class TestLoadIter:
    async def test_yields_each_port_after_load(self, mocker):
        """Should yield each port after it's loaded (after port.load() is called)."""
        from qtoggleserver.core import ports as core_ports
        from tests.unit.qtoggleserver.mock.ports import MockBooleanPort, MockNumberPort

        mocker.patch("asyncio.Lock")

        port_args = [
            {"driver": MockBooleanPort, "port_id": "test_bool1", "value": True},
            {"driver": MockNumberPort, "port_id": "test_num1", "value": 42},
            {"driver": MockBooleanPort, "port_id": "test_bool2", "value": False},
        ]

        # Track when ports are loaded and yielded
        loaded_ports = []
        load_calls = []

        original_load = MockBooleanPort.load

        async def mock_load(self):
            load_calls.append(self.get_id())
            return await original_load(self)

        mocker.patch.object(MockBooleanPort, "load", side_effect=mock_load, autospec=True)
        mocker.patch.object(MockNumberPort, "load", side_effect=mock_load, autospec=True)

        async for port in core_ports.load_iter(port_args, trigger_add=False):
            loaded_ports.append(port.get_id())
            # At this point, port.load() should have been called for this port
            assert port.get_id() in load_calls

        # Verify all ports were yielded in order
        assert loaded_ports == ["test_bool1", "test_num1", "test_bool2"]

        # Clean up
        for port_id in ["test_bool1", "test_num1", "test_bool2"]:
            port = core_ports.get(port_id)
            if port:
                await port.remove(persisted_data=False)

    async def test_handles_port_mapping(self, mocker):
        """Should properly handle port ID mapping and yield with mapped IDs."""
        from qtoggleserver.conf import settings
        from qtoggleserver.core import ports as core_ports
        from tests.unit.qtoggleserver.mock.ports import MockNumberPort

        mocker.patch("asyncio.Lock")

        # Set up port mapping
        original_mappings = settings.port_mappings.copy()
        settings.port_mappings["test_map1"] = "mapped1"

        port_args = [
            {"driver": MockNumberPort, "port_id": "test_map1", "value": 100},
        ]

        yielded_ports = []
        async for port in core_ports.load_iter(port_args, trigger_add=False):
            yielded_ports.append(port)

        # Should yield with mapped ID
        assert len(yielded_ports) == 1
        assert yielded_ports[0].get_id() == "mapped1"

        # Clean up
        settings.port_mappings = original_mappings
        port = core_ports.get("mapped1")
        if port:
            await port.remove(persisted_data=False)

    async def test_trigger_add_called_when_enabled(self, mocker):
        """Should call trigger_add on each port when trigger_add=True."""
        from qtoggleserver.core import ports as core_ports
        from tests.unit.qtoggleserver.mock.ports import MockBooleanPort

        mocker.patch("asyncio.Lock")

        port_args = [
            {"driver": MockBooleanPort, "port_id": "test_trigger1", "value": True},
            {"driver": MockBooleanPort, "port_id": "test_trigger2", "value": False},
        ]

        trigger_add_calls = []

        async def mock_trigger_add(self):
            trigger_add_calls.append(self.get_id())

        mocker.patch.object(MockBooleanPort, "trigger_add", side_effect=mock_trigger_add, autospec=True)

        async for port in core_ports.load_iter(port_args, trigger_add=True):
            pass

        # trigger_add should be called for both ports
        assert trigger_add_calls == ["test_trigger1", "test_trigger2"]

        # Clean up
        for port_id in ["test_trigger1", "test_trigger2"]:
            port = core_ports.get(port_id)
            if port:
                await port.remove(persisted_data=False)

    async def test_trigger_add_not_called_when_disabled(self, mocker):
        """Should not call trigger_add on each port when trigger_add=False."""
        from qtoggleserver.core import ports as core_ports
        from tests.unit.qtoggleserver.mock.ports import MockBooleanPort

        mocker.patch("asyncio.Lock")

        port_args = [
            {"driver": MockBooleanPort, "port_id": "test_notrigger1", "value": True},
        ]

        trigger_add_mock = mocker.patch.object(MockBooleanPort, "trigger_add", autospec=True)

        async for port in core_ports.load_iter(port_args, trigger_add=False):
            pass

        # trigger_add should NOT be called
        trigger_add_mock.assert_not_called()

        # Clean up
        port = core_ports.get("test_notrigger1")
        if port:
            await port.remove(persisted_data=False)

    async def test_load_failure_not_yielded_and_removed(self, mocker):
        """A port that fails `load()` should not be yielded, added, or trigger add events."""
        from qtoggleserver.core import ports as core_ports
        from tests.unit.qtoggleserver.mock.ports import MockBooleanPort

        mocker.patch("asyncio.Lock")

        port_args = [
            {"driver": MockBooleanPort, "port_id": "test_load_ok", "value": True},
            {"driver": MockBooleanPort, "port_id": "test_load_fail", "value": False},
        ]

        original_load = MockBooleanPort.load
        trigger_add_calls: list[str] = []

        async def mock_load(self):
            if self.get_id() == "test_load_fail":
                raise RuntimeError("load failed")
            return await original_load(self)

        async def mock_trigger_add(self):
            trigger_add_calls.append(self.get_id())

        mocker.patch.object(MockBooleanPort, "load", side_effect=mock_load, autospec=True)
        mocker.patch.object(MockBooleanPort, "trigger_add", side_effect=mock_trigger_add, autospec=True)

        yielded_ids = []
        error = None
        try:
            async for port in core_ports.load_iter(port_args, trigger_add=True):
                yielded_ids.append(port.get_id())
        except core_ports.PortLoadErrors as ple:
            error = ple

        assert error is not None
        assert isinstance(error.errors[1], RuntimeError)
        assert yielded_ids == ["test_load_ok"]
        assert core_ports.get("test_load_fail") is None
        assert "test_load_fail" not in trigger_add_calls
        assert trigger_add_calls == ["test_load_ok"]

        port = core_ports.get("test_load_ok")
        if port:
            await port.remove(persisted_data=False)

    async def test_mixed_errors_still_loads_valid_ports(self, mocker):
        """Missing driver errors should be reported while valid ports still load."""
        from qtoggleserver.core import ports as core_ports
        from tests.unit.qtoggleserver.mock.ports import MockBooleanPort

        mocker.patch("asyncio.Lock")

        port_args = [
            {"port_id": "test_missing_driver", "value": True},
            {"driver": MockBooleanPort, "port_id": "test_after_error", "value": False},
        ]

        yielded_ids = []
        error = None
        try:
            async for port in core_ports.load_iter(port_args, trigger_add=False):
                yielded_ids.append(port.get_id())
        except core_ports.PortLoadErrors as ple:
            error = ple

        assert error is not None
        assert isinstance(error.errors[0], core_ports.PortLoadError)
        assert str(error.errors[0]) == "Missing port driver"
        assert yielded_ids == ["test_after_error"]

        port = core_ports.get("test_after_error")
        if port:
            await port.remove(persisted_data=False)


class TestLoad:
    async def test_basic_call(self, mocker):
        """Should load given port."""
        from qtoggleserver.core import ports as core_ports
        from tests.unit.qtoggleserver.mock.ports import MockBooleanPort

        mocker.patch("asyncio.Lock")

        # This is how existing code uses load()
        port_args = [{"driver": MockBooleanPort, "port_id": "test_compat1", "value": False}]
        ports = await core_ports.load(port_args, trigger_add=False)

        assert isinstance(ports, list)
        assert len(ports) == 1
        assert ports[0].get_id() == "test_compat1"

        # Clean up
        for port in ports:
            await port.remove(persisted_data=False)

    async def test_returns_all_ports_after_completion(self, mocker):
        """Should return all loaded ports in a list after completion."""
        from qtoggleserver.core import ports as core_ports
        from tests.unit.qtoggleserver.mock.ports import MockBooleanPort, MockNumberPort

        mocker.patch("asyncio.Lock")

        port_args = [
            {"driver": MockBooleanPort, "port_id": "test_load1", "value": True},
            {"driver": MockNumberPort, "port_id": "test_load2", "value": 99},
        ]

        ports = await core_ports.load(port_args, trigger_add=False)

        # Should return a list with all ports
        assert len(ports) == 2
        assert ports[0].get_id() == "test_load1"
        assert ports[1].get_id() == "test_load2"

        # Clean up
        for port in ports:
            await port.remove(persisted_data=False)


class TestLoadOne:
    async def test_re_raises_single_wrapped_error(self, mocker):
        """load_one should re-raise the error at index 0 from PortLoadErrors."""
        from qtoggleserver.core import ports as core_ports

        expected_error = RuntimeError("boom")
        mocker.patch("qtoggleserver.core.ports.load", side_effect=core_ports.PortLoadErrors({0: expected_error}))

        try:
            await core_ports.load_one("dummy.Class", {"port_id": "p1"})
            assert False, "Expected load_one to raise"
        except Exception as e:
            assert e is expected_error


class TestPortToPersisted:
    async def test_includes_id_and_history_timestamp(self, mock_num_port1):
        """to_persisted should always include id and history_last_timestamp."""
        mock_num_port1._history_last_timestamp = 123456

        result = await mock_num_port1.to_persisted()

        assert result["id"] == "nid1"
        assert result["history_last_timestamp"] == 123456

    async def test_includes_last_read_value(self, mock_num_port1):
        """to_persisted should include last_read_value."""
        mock_num_port1._last_read_value = (42, 1234567890)

        result = await mock_num_port1.to_persisted()

        assert result["last_read_value"] == 42
        assert "value" not in result

    async def test_last_read_value_none_when_no_last_read_value(self, mock_num_port1):
        """to_persisted should set last_read_value to None when no last_read_value."""
        mock_num_port1._last_read_value = None

        result = await mock_num_port1.to_persisted()

        assert result["last_read_value"] is None

    async def test_includes_modifiable_attrs(self, mock_num_port1, mocker):
        """to_persisted should include all modifiable attributes."""
        mocker.patch.object(mock_num_port1, "get_modifiable_attrs", return_value=["display_name", "unit", "enabled"])

        # Mock get_attr to return test values
        async def mock_get_attr(name):
            if name == "display_name":
                return "Test Port"
            elif name == "unit":
                return "V"
            elif name == "enabled":
                return True
            return None

        mocker.patch.object(mock_num_port1, "get_attr", side_effect=mock_get_attr)

        result = await mock_num_port1.to_persisted()

        assert result["display_name"] == "Test Port"
        assert result["unit"] == "V"
        assert result["enabled"] is True

    async def test_skips_none_attrs(self, mock_num_port1, mocker):
        """to_persisted should skip attributes that are None."""
        mocker.patch.object(mock_num_port1, "get_modifiable_attrs", return_value=["display_name", "unit"])

        # Mock get_attr to return None for 'unit'
        async def mock_get_attr(name):
            if name == "display_name":
                return "Test Port"
            elif name == "unit":
                return None
            return None

        mocker.patch.object(mock_num_port1, "get_attr", side_effect=mock_get_attr)

        result = await mock_num_port1.to_persisted()

        assert result["display_name"] == "Test Port"
        assert "unit" not in result

    async def test_includes_state_fields(self, mock_num_port1, mocker):
        """to_persisted should include state fields."""
        mocker.patch.object(mock_num_port1, "get_modifiable_attrs", return_value=[])
        mock_num_port1._last_read_value = (42, 1111)
        mock_num_port1._last_written_value = (43, 2222)
        mock_num_port1._write_queue.clear()
        mock_num_port1._write_queue.append(WriteRequest(44))
        mock_num_port1._write_queue.append(WriteRequest(45))

        result = await mock_num_port1.to_persisted()

        assert result["last_read_value"] == 42
        assert result["last_read_timestamp"] == 1111
        assert result["last_written_value"] == 43
        assert result["last_written_timestamp"] == 2222
        assert result["write_queue"] == [44, 45]

    async def test_includes_value_being_written(self, mock_num_port1, mocker):
        """to_persisted should keep the value being written first in the write queue, so that a restart during the
        write doesn't lose it."""

        mocker.patch.object(mock_num_port1, "get_modifiable_attrs", return_value=[])
        mock_num_port1._write_queue.clear()
        mock_num_port1._write_queue.append(WriteRequest(45))
        persisted = {}

        async def write_value(value) -> None:
            persisted.update(await mock_num_port1.to_persisted())

        mocker.patch.object(mock_num_port1, "write_value", side_effect=write_value)

        await mock_num_port1.transform_and_write_value(44)

        assert persisted["write_queue"] == [44, 45]
        assert (await mock_num_port1.to_persisted())["write_queue"] == [45]


class TestPortFromPersisted:
    async def test_skips_write_queue_when_disabled(self, mock_num_port1, mocker):
        """from_persisted should not restore a write queue for a disabled port, since it has nothing pending."""
        mocker.patch.object(mock_num_port1, "write_value", new=mocker.AsyncMock())
        await mock_num_port1.disable()

        await mock_num_port1.from_persisted({"enabled": False, "write_queue": [56, 78]})

        assert len(mock_num_port1._write_queue) == 0
        assert mock_num_port1.get_pending_value() is None

    async def test_loads_state_fields(self, mock_num_port1, mocker):
        """from_persisted should restore state fields."""
        mocker.patch.object(mock_num_port1, "write_value", new=mocker.AsyncMock())

        data = {
            "last_read_value": 12,
            "last_read_timestamp": 1001,
            "last_written_value": 34,
            "last_written_timestamp": 1002,
            "write_queue": [56, 78],
        }

        await mock_num_port1.from_persisted(data)

        assert mock_num_port1._last_read_value == (12, 1001)
        assert mock_num_port1._last_written_value == (34, 1002)
        assert list(mock_num_port1._write_queue) == [WriteRequest(56), WriteRequest(78)]
        assert mock_num_port1.get_pending_value() == 78
        mock_num_port1.write_value.assert_not_called()


class TestPortWriteRetries:
    """Test that a failed write is retried as set by `write_retry_count` and `write_retry_interval`, and that the
    retry attributes only exist where retries can work."""

    @pytest.fixture
    def writable_port(self, mock_num_port1):
        mock_num_port1.set_writable(True)
        return mock_num_port1

    @staticmethod
    def fail_times(mocker, port, count: int) -> list:
        """Make the port's `write_value()` fail `count` times, then succeed."""

        calls = []

        async def write_value(value) -> None:
            calls.append(value)
            if len(calls) <= count:
                raise PortWriteError("nope")

        mocker.patch.object(port, "write_value", side_effect=write_value)
        return calls

    async def test_no_retry_by_default(self, writable_port, mocker):
        calls = self.fail_times(mocker, writable_port, 1)

        with pytest.raises(PortWriteError):
            await writable_port.transform_and_write_value(5)

        assert calls == [5]
        assert writable_port.get_last_written_value() is None

    async def test_retries_until_written(self, writable_port, mocker):
        await writable_port.set_attr("write_retry_count", 3)
        await writable_port.set_attr("write_retry_interval", 0)
        calls = self.fail_times(mocker, writable_port, 2)

        await writable_port.transform_and_write_value(5)

        assert calls == [5, 5, 5]
        assert writable_port.get_last_written_value() == 5

    async def test_gives_up_after_last_retry(self, writable_port, mocker, caplog):
        await writable_port.set_attr("write_retry_count", 2)
        await writable_port.set_attr("write_retry_interval", 0)
        calls = self.fail_times(mocker, writable_port, 10)

        with caplog.at_level(logging.WARNING), pytest.raises(PortWriteError):
            await writable_port.transform_and_write_value(5)

        assert calls == [5, 5, 5]
        assert writable_port.get_last_written_value() is None
        # A warning for each retry, and one error for the final failure
        assert [r.levelno for r in caplog.records if r.name.endswith("nid1")] == [
            logging.WARNING,
            logging.WARNING,
            logging.ERROR,
        ]

    async def test_waits_interval_and_stays_pending(self, writable_port, mocker):
        await writable_port.set_attr("write_retry_count", 1)
        await writable_port.set_attr("write_retry_interval", 50)
        self.fail_times(mocker, writable_port, 1)

        task = asyncio.create_task(writable_port.transform_and_write_value(5))
        await asyncio.sleep(0.02)
        assert not task.done()
        assert writable_port.get_pending_value() == 5

        await task
        assert writable_port.get_pending_value() is None
        assert writable_port.get_last_written_value() == 5

    async def test_transform_applied_once(self, writable_port, mocker):
        await writable_port.set_attr("write_retry_count", 2)
        await writable_port.set_attr("write_retry_interval", 0)
        await writable_port.set_attr("transform_write", "ADD($, 1)")
        calls = self.fail_times(mocker, writable_port, 2)

        await writable_port.transform_and_write_value(5)

        assert calls == [6, 6, 6]
        assert writable_port.get_last_written_value() == 5

    async def test_disable_stops_retry_wait(self, writable_port, mocker):
        await writable_port.set_attr("write_retry_count", 5)
        await writable_port.set_attr("write_retry_interval", 60000)
        calls = self.fail_times(mocker, writable_port, 10)

        task = asyncio.create_task(writable_port.transform_and_write_value(5))
        await asyncio.sleep(0.01)
        await writable_port.disable()

        with pytest.raises(PortDisabled):
            await asyncio.wait_for(task, timeout=1)
        assert calls == [5]

    async def test_new_count_applies_to_next_attempt(self, writable_port, mocker):
        await writable_port.set_attr("write_retry_count", 5)
        await writable_port.set_attr("write_retry_interval", 50)
        calls = self.fail_times(mocker, writable_port, 10)

        task = asyncio.create_task(writable_port.transform_and_write_value(5))
        await asyncio.sleep(0.02)
        await writable_port.set_attr("write_retry_count", 1)

        with pytest.raises(PortWriteError):
            await task
        assert calls == [5, 5]

    async def test_attrs_only_on_writable_ports(self, mock_num_port1):
        assert "write_retry_count" not in await mock_num_port1.get_attrs()

        mock_num_port1.set_writable(True)

        attrs = await mock_num_port1.get_attrs()
        assert attrs["write_retry_count"] == 0
        assert attrs["write_retry_interval"] == 1000

    async def test_attrs_hidden_without_write_retry(self, writable_port, mocker):
        mocker.patch.object(writable_port, "WRITE_RETRY", False)
        writable_port.invalidate_attrdefs()

        attrs = await writable_port.get_attrs()
        assert "write_retry_count" not in attrs
        assert "write_retry_interval" not in attrs

    async def test_no_retry_without_write_retry(self, writable_port, mocker):
        await writable_port.set_attr("write_retry_count", 3)
        mocker.patch.object(writable_port, "WRITE_RETRY", False)
        calls = self.fail_times(mocker, writable_port, 1)

        with pytest.raises(PortWriteError):
            await writable_port.transform_and_write_value(5)

        assert calls == [5]
