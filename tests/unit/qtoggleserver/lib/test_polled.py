import asyncio

import pytest

from qtoggleserver.lib.polled import PolledPeripheral, PolledPort


class MockPolledPort(PolledPort):
    TYPE = "boolean"

    def __init__(self, peripheral, port_id, **kwargs) -> None:
        self._read_value = False
        super().__init__(id=port_id, peripheral=peripheral, **kwargs)

    async def read_value(self):
        return self._read_value

    async def write_value(self, value):
        self._read_value = value


class MockPolledPeripheral(PolledPeripheral):
    def __init__(self, poll_after_write=False, trigger_update_after_poll=False, **kwargs) -> None:
        if poll_after_write:
            self.POLL_AFTER_WRITE = True
        if trigger_update_after_poll:
            self.TRIGGER_UPDATE_AFTER_POLL = True
        self._poll_count = 0
        super().__init__(**kwargs)

    async def poll(self):
        self._poll_count += 1
        await asyncio.sleep(0.01)  # Simulate some polling work

    async def make_port_args(self):
        return []


class TestPolledPortPollAfterWrite:
    async def test_poll_called_after_write_when_enabled(self, mocker):
        """Should call poll() after write when POLL_AFTER_WRITE is True."""
        peripheral = MockPolledPeripheral(name="test", poll_after_write=True, dummy_param="value")
        port = MockPolledPort(peripheral, "port1")

        spy_poll = mocker.patch.object(peripheral, "poll", new_callable=mocker.AsyncMock)

        await port._write_value_safe(True)

        spy_poll.assert_called_once()

    async def test_poll_not_called_after_write_when_disabled(self, mocker):
        """Should NOT call poll() after write when POLL_AFTER_WRITE is False (default)."""
        peripheral = MockPolledPeripheral(name="test", poll_after_write=False, dummy_param="value")
        port = MockPolledPort(peripheral, "port1")

        spy_poll = mocker.patch.object(peripheral, "poll", new_callable=mocker.AsyncMock)

        await port._write_value_safe(True)

        spy_poll.assert_not_called()

    async def test_write_completes_before_poll(self, mocker):
        """Should complete write_value() before calling poll()."""
        peripheral = MockPolledPeripheral(name="test", poll_after_write=True, dummy_param="value")
        port = MockPolledPort(peripheral, "port1")

        write_completed = False
        poll_called_after_write = False

        original_write = port.write_value
        original_poll = peripheral.poll

        async def mock_write(value):
            nonlocal write_completed
            await original_write(value)
            write_completed = True

        async def mock_poll():
            nonlocal poll_called_after_write
            poll_called_after_write = write_completed
            await original_poll()

        mocker.patch.object(port, "write_value", side_effect=mock_write)
        mocker.patch.object(peripheral, "poll", side_effect=mock_poll)

        await port._write_value_safe(True)

        assert write_completed
        assert poll_called_after_write

    async def test_last_written_value_set_before_poll(self, mocker):
        """Should set _last_written_value before calling poll()."""
        peripheral = MockPolledPeripheral(name="test", poll_after_write=True, dummy_param="value")
        port = MockPolledPort(peripheral, "port1")

        last_written_set = False

        original_poll = peripheral.poll

        async def mock_poll():
            nonlocal last_written_set
            last_written_set = port._last_written_value is not None
            await original_poll()

        mocker.patch.object(peripheral, "poll", side_effect=mock_poll)

        await port._write_value_safe(True)

        assert last_written_set

    async def test_poll_exception_propagates(self, mocker):
        """Poll exception should propagate to caller."""
        peripheral = MockPolledPeripheral(name="test", poll_after_write=True, dummy_param="value")
        port = MockPolledPort(peripheral, "port1")

        mocker.patch.object(peripheral, "poll", side_effect=RuntimeError("Poll failed"))

        with pytest.raises(RuntimeError, match="Poll failed"):
            await port._write_value_safe(True)

    async def test_write_exception_skips_poll(self, mocker):
        """If write_value() fails, poll should not be called."""
        peripheral = MockPolledPeripheral(name="test", poll_after_write=True, dummy_param="value")
        port = MockPolledPort(peripheral, "port1")

        mocker.patch.object(port, "write_value", side_effect=RuntimeError("Write failed"))
        spy_poll = mocker.patch.object(peripheral, "poll", new_callable=mocker.AsyncMock)

        with pytest.raises(RuntimeError, match="Write failed"):
            await port._write_value_safe(True)

        spy_poll.assert_not_called()

    async def test_multiple_writes_trigger_multiple_polls(self, mocker):
        """Multiple writes should trigger multiple polls when enabled."""
        peripheral = MockPolledPeripheral(name="test", poll_after_write=True, dummy_param="value")
        port = MockPolledPort(peripheral, "port1")

        spy_poll = mocker.patch.object(peripheral, "poll", new_callable=mocker.AsyncMock)

        await port._write_value_safe(True)
        await port._write_value_safe(False)
        await port._write_value_safe(True)

        assert spy_poll.call_count == 3

    async def test_get_peripheral_returns_typed_peripheral(self):
        """get_peripheral() should return properly typed PolledPeripheral."""
        peripheral = MockPolledPeripheral(name="test", poll_after_write=False, dummy_param="value")
        port = MockPolledPort(peripheral, "port1")

        result = port.get_peripheral()

        assert isinstance(result, PolledPeripheral)
        assert result is peripheral

    async def test_poll_called_with_correct_peripheral_instance(self, mocker):
        """poll() should be called on the correct peripheral instance."""
        peripheral1 = MockPolledPeripheral(name="test1", poll_after_write=True, dummy_param="value1")
        peripheral2 = MockPolledPeripheral(name="test2", poll_after_write=True, dummy_param="value2")

        port1 = MockPolledPort(peripheral1, "port1")
        MockPolledPort(peripheral2, "port2")

        spy_poll1 = mocker.patch.object(peripheral1, "poll", new_callable=mocker.AsyncMock)
        spy_poll2 = mocker.patch.object(peripheral2, "poll", new_callable=mocker.AsyncMock)

        await port1._write_value_safe(True)

        spy_poll1.assert_called_once()
        spy_poll2.assert_not_called()

    async def test_concurrent_writes_call_poll_sequentially(self, mocker):
        """Concurrent writes should be serialized and each should trigger poll."""
        peripheral = MockPolledPeripheral(name="test", poll_after_write=True, dummy_param="value")
        port = MockPolledPort(peripheral, "port1")

        poll_call_count = 0
        poll_calls = []

        original_poll = peripheral.poll

        async def mock_poll():
            nonlocal poll_call_count
            poll_calls.append(asyncio.current_task().get_name())
            poll_call_count += 1
            await original_poll()

        mocker.patch.object(peripheral, "poll", side_effect=mock_poll)

        # Launch concurrent writes
        tasks = [
            asyncio.create_task(port._write_value_safe(True)),
            asyncio.create_task(port._write_value_safe(False)),
            asyncio.create_task(port._write_value_safe(True)),
        ]

        await asyncio.gather(*tasks)

        assert poll_call_count == 3


class TestPolledPeripheralPollAfterWriteFlag:
    def test_default_poll_after_write_is_false(self):
        """POLL_AFTER_WRITE should default to False."""
        peripheral = MockPolledPeripheral(name="test", dummy_param="value")

        assert peripheral.POLL_AFTER_WRITE is False

    def test_can_override_poll_after_write_in_subclass(self):
        """Subclasses should be able to override POLL_AFTER_WRITE."""

        class CustomPolledPeripheral(MockPolledPeripheral):
            POLL_AFTER_WRITE = True

        peripheral = CustomPolledPeripheral(name="test", dummy_param="value")

        assert peripheral.POLL_AFTER_WRITE is True

    async def test_poll_after_write_respected_per_peripheral_class(self, mocker):
        """Different peripheral classes can have different POLL_AFTER_WRITE settings."""

        class PeripheralWithPoll(MockPolledPeripheral):
            POLL_AFTER_WRITE = True

        class PeripheralWithoutPoll(MockPolledPeripheral):
            POLL_AFTER_WRITE = False

        p1 = PeripheralWithPoll(name="test1", dummy_param="value1")
        p2 = PeripheralWithoutPoll(name="test2", dummy_param="value2")

        port1 = MockPolledPort(p1, "port1")
        port2 = MockPolledPort(p2, "port2")

        spy_poll1 = mocker.patch.object(p1, "poll", new_callable=mocker.AsyncMock)
        spy_poll2 = mocker.patch.object(p2, "poll", new_callable=mocker.AsyncMock)

        await port1._write_value_safe(True)
        await port2._write_value_safe(True)

        spy_poll1.assert_called_once()
        spy_poll2.assert_not_called()


class TestTriggerUpdateAfterPoll:
    async def test_trigger_update_called_after_poll_in_poll_loop_when_enabled(self, mocker):
        """Should call trigger_port_update_fire_and_forget() after successful poll when TRIGGER_UPDATE_AFTER_POLL is
        True.
        """

        peripheral = MockPolledPeripheral(name="test", trigger_update_after_poll=True, dummy_param="value")

        # Mock set_online to prevent it from calling trigger_port_update_fire_and_forget
        mocker.patch.object(peripheral, "set_online")
        spy_trigger = mocker.patch.object(peripheral, "trigger_port_update_fire_and_forget")
        mocker.patch.object(peripheral, "poll", new_callable=mocker.AsyncMock)
        mocker.patch("qtoggleserver.core.main.loop", True)  # Mock main loop initialized

        # Start polling task and let it run one iteration
        peripheral._poll_task = asyncio.create_task(peripheral._poll_loop())
        await asyncio.sleep(0.05)

        # Stop polling
        peripheral._polling = False
        peripheral._poll_wakeup.set()
        try:
            await asyncio.wait_for(peripheral._poll_task, timeout=1.0)
        except asyncio.TimeoutError:
            peripheral._poll_task.cancel()

        # trigger_port_update_fire_and_forget should be called because TRIGGER_UPDATE_AFTER_POLL is True
        spy_trigger.assert_called()

    async def test_trigger_update_not_called_after_poll_in_poll_loop_when_disabled(self, mocker):
        """Should NOT call trigger_port_update_fire_and_forget() from TRIGGER_UPDATE_AFTER_POLL when flag is False."""
        peripheral = MockPolledPeripheral(name="test", trigger_update_after_poll=False, dummy_param="value")

        # Mock set_online to prevent it from calling trigger_port_update_fire_and_forget
        mocker.patch.object(peripheral, "set_online")
        spy_trigger = mocker.patch.object(peripheral, "trigger_port_update_fire_and_forget")
        mocker.patch.object(peripheral, "poll", new_callable=mocker.AsyncMock)
        mocker.patch("qtoggleserver.core.main.loop", True)  # Mock main loop initialized

        # Start polling task and let it run one iteration
        peripheral._poll_task = asyncio.create_task(peripheral._poll_loop())
        await asyncio.sleep(0.05)

        # Stop polling
        peripheral._polling = False
        peripheral._poll_wakeup.set()
        try:
            await asyncio.wait_for(peripheral._poll_task, timeout=1.0)
        except asyncio.TimeoutError:
            peripheral._poll_task.cancel()

        # trigger_port_update_fire_and_forget should not be called because TRIGGER_UPDATE_AFTER_POLL is False
        spy_trigger.assert_not_called()

    async def test_trigger_update_called_after_write_when_both_flags_enabled(self, mocker):
        """Should call trigger_port_update_fire_and_forget() after poll-after-write when both flags are True."""
        peripheral = MockPolledPeripheral(
            name="test", poll_after_write=True, trigger_update_after_poll=True, dummy_param="value"
        )
        port = MockPolledPort(peripheral, "port1")

        spy_trigger = mocker.patch.object(peripheral, "trigger_port_update_fire_and_forget")
        mocker.patch.object(peripheral, "poll", new_callable=mocker.AsyncMock)

        await port._write_value_safe(True)

        spy_trigger.assert_called_once()

    async def test_trigger_update_not_called_after_write_when_only_poll_after_write_enabled(self, mocker):
        """Should NOT call trigger_port_update_fire_and_forget() when only POLL_AFTER_WRITE is True."""
        peripheral = MockPolledPeripheral(
            name="test", poll_after_write=True, trigger_update_after_poll=False, dummy_param="value"
        )
        port = MockPolledPort(peripheral, "port1")

        spy_trigger = mocker.patch.object(peripheral, "trigger_port_update_fire_and_forget")
        mocker.patch.object(peripheral, "poll", new_callable=mocker.AsyncMock)

        await port._write_value_safe(True)

        spy_trigger.assert_not_called()

    async def test_trigger_update_not_called_after_write_when_only_trigger_update_enabled(self, mocker):
        """Should NOT call trigger_port_update_fire_and_forget() after write when POLL_AFTER_WRITE is False."""
        peripheral = MockPolledPeripheral(
            name="test", poll_after_write=False, trigger_update_after_poll=True, dummy_param="value"
        )
        port = MockPolledPort(peripheral, "port1")

        spy_trigger = mocker.patch.object(peripheral, "trigger_port_update_fire_and_forget")
        spy_poll = mocker.patch.object(peripheral, "poll", new_callable=mocker.AsyncMock)

        await port._write_value_safe(True)

        # Neither poll nor trigger should be called (no poll-after-write)
        spy_poll.assert_not_called()
        spy_trigger.assert_not_called()

    async def test_trigger_update_happens_after_poll_completes(self, mocker):
        """trigger_port_update_fire_and_forget() should be called after poll() completes."""
        peripheral = MockPolledPeripheral(
            name="test", poll_after_write=True, trigger_update_after_poll=True, dummy_param="value"
        )
        port = MockPolledPort(peripheral, "port1")

        poll_completed = False
        trigger_called_after_poll = False

        original_poll = peripheral.poll

        async def mock_poll():
            nonlocal poll_completed
            await original_poll()
            poll_completed = True

        def mock_trigger():
            nonlocal trigger_called_after_poll
            trigger_called_after_poll = poll_completed

        mocker.patch.object(peripheral, "poll", side_effect=mock_poll)
        mocker.patch.object(peripheral, "trigger_port_update_fire_and_forget", side_effect=mock_trigger)

        await port._write_value_safe(True)

        assert poll_completed
        assert trigger_called_after_poll

    async def test_trigger_update_not_called_when_poll_fails(self, mocker):
        """Should NOT call trigger_port_update_fire_and_forget() when poll() raises exception."""
        peripheral = MockPolledPeripheral(
            name="test", poll_after_write=True, trigger_update_after_poll=True, dummy_param="value"
        )
        port = MockPolledPort(peripheral, "port1")

        spy_trigger = mocker.patch.object(peripheral, "trigger_port_update_fire_and_forget")
        mocker.patch.object(peripheral, "poll", side_effect=RuntimeError("Poll failed"))

        with pytest.raises(RuntimeError, match="Poll failed"):
            await port._write_value_safe(True)

        spy_trigger.assert_not_called()

    async def test_multiple_writes_trigger_multiple_updates(self, mocker):
        """Multiple writes should trigger multiple port updates when both flags are enabled."""
        peripheral = MockPolledPeripheral(
            name="test", poll_after_write=True, trigger_update_after_poll=True, dummy_param="value"
        )
        port = MockPolledPort(peripheral, "port1")

        spy_trigger = mocker.patch.object(peripheral, "trigger_port_update_fire_and_forget")
        mocker.patch.object(peripheral, "poll", new_callable=mocker.AsyncMock)

        await port._write_value_safe(True)
        await port._write_value_safe(False)
        await port._write_value_safe(True)

        assert spy_trigger.call_count == 3


class TestTriggerUpdateAfterPollFlag:
    def test_default_trigger_update_after_poll_is_false(self):
        """TRIGGER_UPDATE_AFTER_POLL should default to False."""
        peripheral = MockPolledPeripheral(name="test", dummy_param="value")

        assert peripheral.TRIGGER_UPDATE_AFTER_POLL is False

    def test_can_override_trigger_update_after_poll_in_subclass(self):
        """Subclasses should be able to override TRIGGER_UPDATE_AFTER_POLL."""

        class CustomPolledPeripheral(MockPolledPeripheral):
            TRIGGER_UPDATE_AFTER_POLL = True

        peripheral = CustomPolledPeripheral(name="test", dummy_param="value")

        assert peripheral.TRIGGER_UPDATE_AFTER_POLL is True

    async def test_trigger_update_after_poll_respected_per_peripheral_class(self, mocker):
        """Different peripheral classes can have different TRIGGER_UPDATE_AFTER_POLL settings."""

        class PeripheralWithTrigger(MockPolledPeripheral):
            POLL_AFTER_WRITE = True
            TRIGGER_UPDATE_AFTER_POLL = True

        class PeripheralWithoutTrigger(MockPolledPeripheral):
            POLL_AFTER_WRITE = True
            TRIGGER_UPDATE_AFTER_POLL = False

        p1 = PeripheralWithTrigger(name="test1", dummy_param="value1")
        p2 = PeripheralWithoutTrigger(name="test2", dummy_param="value2")

        port1 = MockPolledPort(p1, "port1")
        port2 = MockPolledPort(p2, "port2")

        spy_trigger1 = mocker.patch.object(p1, "trigger_port_update_fire_and_forget")
        spy_trigger2 = mocker.patch.object(p2, "trigger_port_update_fire_and_forget")
        mocker.patch.object(p1, "poll", new_callable=mocker.AsyncMock)
        mocker.patch.object(p2, "poll", new_callable=mocker.AsyncMock)

        await port1._write_value_safe(True)
        await port2._write_value_safe(True)

        spy_trigger1.assert_called_once()
        spy_trigger2.assert_not_called()

    async def test_both_flags_independent(self, mocker):
        """POLL_AFTER_WRITE and TRIGGER_UPDATE_AFTER_POLL should work independently."""

        # Test all four combinations
        combinations = [
            (False, False, 0, 0),  # Neither enabled: no poll, no trigger
            (True, False, 1, 0),  # Only poll: poll but no trigger
            (False, True, 0, 0),  # Only trigger: no poll (so no trigger either)
            (True, True, 1, 1),  # Both: poll and trigger
        ]

        for poll_after_write, trigger_update, expected_polls, expected_triggers in combinations:
            peripheral = MockPolledPeripheral(
                name="test",
                poll_after_write=poll_after_write,
                trigger_update_after_poll=trigger_update,
                dummy_param="value",
            )
            port = MockPolledPort(peripheral, "port1")

            spy_poll = mocker.patch.object(peripheral, "poll", new_callable=mocker.AsyncMock)
            spy_trigger = mocker.patch.object(peripheral, "trigger_port_update_fire_and_forget")

            await port._write_value_safe(True)

            assert spy_poll.call_count == expected_polls, (
                f"Failed for poll_after_write={poll_after_write}, trigger_update={trigger_update}"
            )
            assert spy_trigger.call_count == expected_triggers, (
                f"Failed for poll_after_write={poll_after_write}, trigger_update={trigger_update}"
            )

            spy_poll.reset_mock()
            spy_trigger.reset_mock()
