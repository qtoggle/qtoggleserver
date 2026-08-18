import asyncio

import pytest

from qtoggleserver.utils.sequence import Sequence, SequenceError


class TestSequenceRun:
    async def test_calls_callback_for_each_value_in_order(self, mocker):
        """Should invoke the callback once per value, in order, then the finish callback."""

        callback = mocker.Mock()
        finish_callback = mocker.AsyncMock()

        sequence = Sequence([1, 2, 3], [1, 1, 1], 1, callback, finish_callback)
        sequence.start()
        await sequence._loop_task

        assert callback.call_args_list == [mocker.call(1), mocker.call(2), mocker.call(3)]
        finish_callback.assert_awaited_once()

    async def test_passes_custom_args_and_kwargs_to_callback(self, mocker):
        """Should forward the given callback_args/callback_kwargs to every callback invocation, after the value."""

        callback = mocker.Mock()
        finish_callback = mocker.AsyncMock()

        sequence = Sequence(
            [1, 2],
            [1, 1],
            1,
            callback,
            finish_callback,
            callback_args=("extra", 42),
            callback_kwargs={"flag": True},
        )
        sequence.start()
        await sequence._loop_task

        assert callback.call_args_list == [
            mocker.call(1, "extra", 42, flag=True),
            mocker.call(2, "extra", 42, flag=True),
        ]

    async def test_repeats_given_number_of_times(self, mocker):
        """Should replay the entire list of values `repeat` times before calling the finish callback."""

        callback = mocker.Mock()
        finished = asyncio.Event()

        async def finish_callback():
            finished.set()

        sequence = Sequence([1, 2], [1, 1], 2, callback, finish_callback)
        sequence.start()
        await asyncio.wait_for(finished.wait(), timeout=1)

        assert callback.call_args_list == [mocker.call(1), mocker.call(2), mocker.call(1), mocker.call(2)]

    async def test_infinite_repeat_never_calls_finish_callback(self, mocker):
        """A `repeat` of 0 should keep looping forever and never invoke the finish callback."""

        callback = mocker.Mock()
        finish_callback = mocker.AsyncMock()

        sequence = Sequence([1, 2], [1, 1], 0, callback, finish_callback)
        sequence.start()

        # Let a few passes go by
        while callback.call_count < 6:
            await asyncio.sleep(0.01)

        finish_callback.assert_not_called()

        await sequence.cancel()

    async def test_callback_exception_is_caught_and_logged(self, mocker):
        """A failing callback should not interrupt the sequence."""

        callback = mocker.Mock(side_effect=[ValueError("boom"), None])
        finish_callback = mocker.AsyncMock()
        spy_error = mocker.patch("qtoggleserver.utils.sequence.logger.error")

        sequence = Sequence([1, 2], [1, 1], 1, callback, finish_callback)
        sequence.start()
        await sequence._loop_task

        assert callback.call_args_list == [mocker.call(1), mocker.call(2)]
        spy_error.assert_called_once()
        finish_callback.assert_awaited_once()


class TestSequenceStart:
    async def test_raises_if_already_started(self, mocker):
        """Should raise SequenceError when start() is called while a loop task is already running."""

        sequence = Sequence([1], [1], 1, mocker.Mock(), mocker.AsyncMock())
        sequence.start()

        with pytest.raises(SequenceError):
            sequence.start()

        await sequence.cancel()


class TestSequenceCancel:
    async def test_stops_further_callbacks(self, mocker):
        """Should stop the sequence before it reaches subsequent values once cancelled."""

        callback_ran = asyncio.Event()
        callback = mocker.Mock(side_effect=lambda value: callback_ran.set())
        finish_callback = mocker.AsyncMock()

        sequence = Sequence([1, 2, 3], [1000, 1, 1], 1, callback, finish_callback)
        sequence.start()

        await asyncio.wait_for(callback_ran.wait(), timeout=1)
        await sequence.cancel()

        assert callback.call_count == 1
        finish_callback.assert_not_awaited()

    async def test_noop_when_not_started(self):
        """Should do nothing if there's no loop task running."""

        sequence = Sequence([1], [1], 1, lambda value: None, None)
        await sequence.cancel()  # should not raise
