import time

from datetime import datetime, timedelta
from unittest.mock import MagicMock

import pytest

from qtoggleserver.core import events as core_events
from qtoggleserver.core import main as core_main
from qtoggleserver.core import ports as core_ports
from qtoggleserver.core.expressions import DEP_ASAP, DEP_DAY, DEP_HOUR, DEP_MINUTE, DEP_MONTH, DEP_SECOND, DEP_YEAR
from qtoggleserver.core.main import _eval_changed_expressions, force_eval_expressions, pause, read_ports, resume
from qtoggleserver.slaves import events as slaves_events
from tests.unit.qtoggleserver.mock.ports import MockNumberPort


def _make_mock_slave(name: str) -> MagicMock:
    slave = MagicMock()
    slave.get_name.return_value = name
    return slave


def _ts(dt: datetime) -> int:
    return int(dt.timestamp())


class TestGetChangedTimeDeps:
    @pytest.fixture(autouse=True)
    def reset_time_globals(self):
        """Reset all _last_* module globals to 0 before and after each test."""
        for attr in (
            "_last_time",
            "_last_minute",
            "_last_hour",
            "_last_day",
            "_last_week",
            "_last_month",
            "_last_year",
        ):
            setattr(core_main, attr, 0)
        yield
        for attr in (
            "_last_time",
            "_last_minute",
            "_last_hour",
            "_last_day",
            "_last_week",
            "_last_month",
            "_last_year",
        ):
            setattr(core_main, attr, 0)

    def test_same_second_returns_asap_only(self):
        """Calling with the same now_int twice should return second_changed=False and only DEP_ASAP."""
        t = _ts(datetime(2024, 3, 15, 10, 30, 30))
        core_main._get_changed_time_deps(t)  # prime
        second_changed, changed = core_main._get_changed_time_deps(t)
        assert second_changed is False
        assert changed == {DEP_ASAP}

    def test_second_changes(self):
        """A new second within the same minute should add DEP_SECOND."""
        t0 = _ts(datetime(2024, 3, 15, 10, 30, 30))
        t1 = _ts(datetime(2024, 3, 15, 10, 30, 31))
        core_main._get_changed_time_deps(t0)
        second_changed, changed = core_main._get_changed_time_deps(t1)
        assert second_changed is True
        assert changed == {DEP_ASAP, DEP_SECOND}

    def test_minute_changes(self):
        """A new minute within the same hour should add DEP_SECOND and DEP_MINUTE."""
        t0 = _ts(datetime(2024, 3, 15, 10, 30, 30))
        t1 = _ts(datetime(2024, 3, 15, 10, 31, 0))
        core_main._get_changed_time_deps(t0)
        second_changed, changed = core_main._get_changed_time_deps(t1)
        assert second_changed is True
        assert changed == {DEP_ASAP, DEP_SECOND, DEP_MINUTE}

    def test_hour_changes(self):
        """A new hour within the same day should add DEP_SECOND, DEP_MINUTE and DEP_HOUR."""
        t0 = _ts(datetime(2024, 3, 15, 10, 30, 30))
        t1 = _ts(datetime(2024, 3, 15, 11, 0, 0))
        core_main._get_changed_time_deps(t0)
        second_changed, changed = core_main._get_changed_time_deps(t1)
        assert second_changed is True
        assert changed == {DEP_ASAP, DEP_SECOND, DEP_MINUTE, DEP_HOUR}

    def test_day_changes(self):
        """A new day within the same month should add DEP_SECOND through DEP_DAY."""
        t0 = _ts(datetime(2024, 3, 15, 10, 30, 30))
        t1 = _ts(datetime(2024, 3, 16, 10, 30, 0))
        core_main._get_changed_time_deps(t0)
        second_changed, changed = core_main._get_changed_time_deps(t1)
        assert second_changed is True
        assert changed == {DEP_ASAP, DEP_SECOND, DEP_MINUTE, DEP_HOUR, DEP_DAY}

    def test_month_changes(self):
        """A new month within the same year should add DEP_SECOND through DEP_MONTH."""
        t0 = _ts(datetime(2024, 1, 31, 10, 30, 30))
        t1 = _ts(datetime(2024, 2, 1, 10, 30, 0))
        core_main._get_changed_time_deps(t0)
        second_changed, changed = core_main._get_changed_time_deps(t1)
        assert second_changed is True
        assert changed == {DEP_ASAP, DEP_SECOND, DEP_MINUTE, DEP_HOUR, DEP_DAY, DEP_MONTH}

    def test_year_changes(self):
        """A new year should add all time deps including DEP_YEAR."""
        t0 = _ts(datetime(2023, 12, 31, 10, 30, 30))
        t1 = _ts(datetime(2024, 1, 1, 10, 30, 0))
        core_main._get_changed_time_deps(t0)
        second_changed, changed = core_main._get_changed_time_deps(t1)
        assert second_changed is True
        assert changed == {DEP_ASAP, DEP_SECOND, DEP_MINUTE, DEP_HOUR, DEP_DAY, DEP_MONTH, DEP_YEAR}

    def test_globals_updated(self):
        """After a call, all relevant _last_* globals should reflect the new time."""
        t = _ts(datetime(2024, 3, 15, 10, 30, 30))
        dt = datetime.fromtimestamp(t)
        core_main._get_changed_time_deps(t)
        assert core_main._last_time == t
        assert core_main._last_minute == t // 60
        assert core_main._last_hour == t // 3600
        assert core_main._last_day == dt.day
        assert core_main._last_month == dt.month
        assert core_main._last_year == dt.year


class TestReadPorts:
    async def test_change_time_asap(self, freezer, mocker, mock_num_port1, dummy_utc_datetime):
        """Should call `_eval_changed_expressions` with {DEP_ASAP}, regardless of time changes."""

        freezer.move_to(dummy_utc_datetime)
        await read_ports()
        spy_handle_value_changes = mocker.patch("qtoggleserver.core.main._eval_changed_expressions")
        await read_ports()
        spy_handle_value_changes.assert_called_once_with({DEP_ASAP}, int(time.time() * 1000))

    async def test_change_time_second(self, freezer, mocker, mock_num_port1, dummy_utc_datetime):
        """Should call `_eval_changed_expressions` with {DEP_ASAP, DEP_SECOND} when second changes."""

        freezer.move_to(dummy_utc_datetime)
        await read_ports()

        freezer.move_to(dummy_utc_datetime + timedelta(seconds=1))
        spy_handle_value_changes = mocker.patch("qtoggleserver.core.main._eval_changed_expressions")
        await read_ports()
        spy_handle_value_changes.assert_called_once_with({DEP_ASAP, DEP_SECOND}, int(time.time() * 1000))

    async def test_change_time_minute(self, freezer, mocker, mock_num_port1, dummy_utc_datetime):
        """Should call `_eval_changed_expressions` with {DEP_ASAP, DEP_SECOND, DEP_MINUTE} when minute changes."""

        freezer.move_to(dummy_utc_datetime)
        await read_ports()

        freezer.move_to(dummy_utc_datetime + timedelta(minutes=1))
        spy_handle_value_changes = mocker.patch("qtoggleserver.core.main._eval_changed_expressions")
        await read_ports()
        spy_handle_value_changes.assert_called_once_with({DEP_ASAP, DEP_SECOND, DEP_MINUTE}, int(time.time() * 1000))

    async def test_change_time_hour(self, freezer, mocker, mock_num_port1, dummy_utc_datetime):
        """Should call `_eval_changed_expressions` with {DEP_ASAP, DEP_SECOND, DEP_MINUTE, DEP_HOUR} whenever hour
        changes."""

        freezer.move_to(dummy_utc_datetime)
        await read_ports()

        freezer.move_to(dummy_utc_datetime + timedelta(hours=1))
        spy_handle_value_changes = mocker.patch("qtoggleserver.core.main._eval_changed_expressions")
        await read_ports()
        spy_handle_value_changes.assert_called_once_with(
            {DEP_ASAP, DEP_SECOND, DEP_MINUTE, DEP_HOUR}, int(time.time() * 1000)
        )

    async def test_change_time_day(self, freezer, mocker, mock_num_port1, dummy_utc_datetime):
        """Should call `_eval_changed_expressions` with {DEP_ASAP, DEP_SECOND, DEP_MINUTE, DEP_HOUR, DEP_DAY} when day
        changes."""

        freezer.move_to(datetime(2019, 1, 30, 23, 30, 30))
        await read_ports()

        freezer.move_to(datetime(2019, 1, 31, 0, 0, 0))
        spy_handle_value_changes = mocker.patch("qtoggleserver.core.main._eval_changed_expressions")
        await read_ports()
        spy_handle_value_changes.assert_called_once_with(
            {DEP_ASAP, DEP_SECOND, DEP_MINUTE, DEP_HOUR, DEP_DAY}, int(time.time() * 1000)
        )

    async def test_change_time_month(self, freezer, mocker, mock_num_port1, dummy_utc_datetime):
        """Should call `_eval_changed_expressions` with {DEP_ASAP, DEP_SECOND, DEP_MINUTE, DEP_HOUR, DEP_DAY, DEP_MONTH}
        when month changes."""

        freezer.move_to(datetime(2019, 1, 31, 23, 30, 30))
        await read_ports()

        freezer.move_to(datetime(2019, 2, 1, 0, 0, 0))
        spy_handle_value_changes = mocker.patch("qtoggleserver.core.main._eval_changed_expressions")
        await read_ports()
        spy_handle_value_changes.assert_called_once_with(
            {DEP_ASAP, DEP_SECOND, DEP_MINUTE, DEP_HOUR, DEP_DAY, DEP_MONTH},
            int(time.time() * 1000),
        )

    async def test_change_time_year(self, freezer, mocker, mock_num_port1, dummy_utc_datetime):
        """Should call `_eval_changed_expressions` with {DEP_ASAP, DEP_SECOND, DEP_MINUTE, DEP_HOUR, DEP_DAY, DEP_MONTH,
        DEP_YEAR} when year changes."""

        freezer.move_to(datetime(2019, 12, 31, 23, 30, 30))
        await read_ports()

        freezer.move_to(datetime(2020, 1, 1, 0, 0, 0))
        spy_handle_value_changes = mocker.patch("qtoggleserver.core.main._eval_changed_expressions")
        await read_ports()
        spy_handle_value_changes.assert_called_once_with(
            {DEP_ASAP, DEP_SECOND, DEP_MINUTE, DEP_HOUR, DEP_DAY, DEP_MONTH, DEP_YEAR},
            int(time.time() * 1000),
        )

    async def test_ports_to_read_specific_ports(
        self, freezer, mocker, mock_num_port1, mock_num_port2, dummy_utc_datetime
    ):
        """Should only read specified ports when `ports_to_read` is provided."""

        freezer.move_to(dummy_utc_datetime)
        await read_ports()
        spy_handle_value_changes = mocker.patch("qtoggleserver.core.main._eval_changed_expressions")

        await read_ports(ports_to_read=[mock_num_port2])
        spy_handle_value_changes.assert_called_once_with({DEP_ASAP}, int(time.time() * 1000))

    async def test_ports_to_read_skip_time_changes(self, freezer, mocker, mock_num_port1, dummy_utc_datetime):
        """Should not add time dependencies when `ports_to_read` is provided, even if time changes."""

        freezer.move_to(dummy_utc_datetime)
        await read_ports()

        freezer.move_to(dummy_utc_datetime + timedelta(seconds=1))
        spy_handle_value_changes = mocker.patch("qtoggleserver.core.main._eval_changed_expressions")

        await read_ports(ports_to_read=[mock_num_port1])
        spy_handle_value_changes.assert_called_once_with({DEP_ASAP}, int(time.time() * 1000))

    async def test_ports_to_read_empty_list(self, freezer, mocker, mock_num_port1, dummy_utc_datetime):
        """Should handle empty ports list gracefully when `ports_to_read` is an empty list."""

        freezer.move_to(dummy_utc_datetime)
        await read_ports()
        spy_handle_value_changes = mocker.patch("qtoggleserver.core.main._eval_changed_expressions")

        await read_ports(ports_to_read=[])
        spy_handle_value_changes.assert_called_once_with({DEP_ASAP}, int(time.time() * 1000))


class TestHandleChanges:
    async def test_self_port_value_trigger_eval(self, mocker, mock_num_port1):
        """Should trigger a port's expression evaluation if the expression depends on itself through `$`."""

        mock_num_port1.set_writable(True)
        mock_num_port1.set_expression("MUL($, 2)")
        mocker.patch.object(mock_num_port1, "eval_and_push_write")

        await _eval_changed_expressions(
            changes={"$nid1"},
            now_ms=0,
        )
        mock_num_port1.eval_and_push_write.assert_called_once()

    async def test_own_port_value_trigger_eval(self, mocker, mock_num_port1):
        """Should trigger a port's expression evaluation if the expression depends on itself through `$<own_id>`."""

        mock_num_port1.set_writable(True)
        mock_num_port1.set_expression("MUL($nid1, 2)")
        mocker.patch.object(mock_num_port1, "eval_and_push_write")

        await _eval_changed_expressions(
            changes={"$nid1"},
            now_ms=0,
        )
        mock_num_port1.eval_and_push_write.assert_called_once()

    async def test_disabled_port_no_trigger_eval(self, mocker, mock_num_port1):
        """Should not trigger a port's expression evaluation if the port is disabled."""

        mock_num_port1.set_writable(True)
        mock_num_port1.set_expression("TIMEMS()")
        force_eval_expressions(mock_num_port1)

        (mocker.patch.object(mock_num_port1, "eval_and_push_write"),)
        (mocker.patch.object(mock_num_port1, "is_enabled", return_value=False),)

        await _eval_changed_expressions(changes=set(), now_ms=0)
        mock_num_port1.eval_and_push_write.assert_not_called()

    async def test_asap_trigger_eval(self, mocker, mock_num_port1):
        """Should trigger a port's expression evaluation if the expression depends on ASAP."""

        mock_num_port1.set_writable(True)
        mock_num_port1.set_expression("TIMEMS()")
        mocker.patch.object(mock_num_port1, "eval_and_push_write")

        await _eval_changed_expressions(changes={DEP_ASAP}, now_ms=0)
        mock_num_port1.eval_and_push_write.assert_called_once()

    async def test_asap_eval_paused_no_trigger_eval(self, mocker, mock_num_port1):
        """Should not trigger a port's expression evaluation if the expression depends on ASAP but is paused."""

        mock_num_port1.set_writable(True)
        mock_num_port1.set_expression("TIMEMS()")
        e = mock_num_port1.get_expression()
        mocker.patch.object(mock_num_port1, "eval_and_push_write")

        e.pause_asap_eval(1000)
        await _eval_changed_expressions(changes={DEP_ASAP}, now_ms=999)
        mock_num_port1.eval_and_push_write.assert_not_called()

    async def test_asap_eval_not_paused_trigger_eval(self, mocker, mock_num_port1):
        """Should trigger a port's expression evaluation if the expression depends on ASAP and pause expired."""

        mock_num_port1.set_writable(True)
        mock_num_port1.set_expression("TIMEMS()")
        e = mock_num_port1.get_expression()
        mocker.patch.object(mock_num_port1, "eval_and_push_write")

        e.pause_asap_eval(1000)
        await _eval_changed_expressions(changes={DEP_ASAP}, now_ms=1000)
        mock_num_port1.eval_and_push_write.assert_called_once()

    async def test_removed_port_not_evaluated(self, mocker, mock_num_port2):
        """Should not evaluate a removed port even when a dep it used to depend on changes."""

        port = await core_ports.load_one(MockNumberPort, {"port_id": "nid_temp", "value": None})
        await port.enable()
        port.set_expression("MUL($nid2, 2)")
        mocker.patch.object(port, "eval_and_push_write")

        await port.remove(persisted_data=False)

        await _eval_changed_expressions(
            changes={"$nid2"},
            now_ms=0,
        )
        port.eval_and_push_write.assert_not_called()

    async def test_expression_set_triggers_eval_via_deps(self, mocker, mock_num_port1, mock_num_port2):
        """Should evaluate a port via the deps map after its expression is set and a dep changes."""

        mock_num_port2.set_expression("MUL($nid1, 2)")
        mocker.patch.object(mock_num_port2, "eval_and_push_write")

        await _eval_changed_expressions(
            changes={"$nid1"},
            now_ms=0,
        )
        mock_num_port2.eval_and_push_write.assert_called_once()

    async def test_expression_cleared_stops_eval(self, mocker, mock_num_port1, mock_num_port2):
        """Should not evaluate a port after its expression is cleared, even when a former dep changes."""

        mock_num_port1.set_expression("MUL($nid2, 2)")
        mock_num_port1.set_writable(True)
        await mock_num_port1.attr_set_expression("")
        mocker.patch.object(mock_num_port1, "eval_and_push_write")

        await _eval_changed_expressions(
            changes={"$nid2"},
            now_ms=0,
        )
        mock_num_port1.eval_and_push_write.assert_not_called()


class TestForceEvalExpressions:
    @pytest.fixture(autouse=True)
    def reset_force_eval(self):
        """Ensure force-eval state is clean before and after each test."""
        core_main._force_eval_all_expressions = False
        core_main._force_eval_expression_ports.clear()
        yield
        core_main._force_eval_all_expressions = False
        core_main._force_eval_expression_ports.clear()

    async def test_forced_port_evaluated_without_matching_dep(self, mocker, mock_num_port1, mock_num_port2):
        """Should evaluate a forced port even when changed_set_str contains no dep that port's expression uses."""

        mock_num_port1.set_expression("MUL($nid2, 2)")
        mocker.patch.object(mock_num_port1, "eval_and_push_write")

        force_eval_expressions(mock_num_port1)

        await _eval_changed_expressions(changes={DEP_ASAP}, now_ms=0)
        mock_num_port1.eval_and_push_write.assert_called_once()

    async def test_force_all_evaluates_all_expression_ports(self, mocker, mock_num_port1, mock_num_port2):
        """Should evaluate all expression ports when force_eval_expressions() is called with no argument."""

        mock_num_port1.set_expression("MUL($nid2, 2)")
        mock_num_port2.set_expression("ADD($nid1, 1)")
        mocker.patch.object(mock_num_port1, "eval_and_push_write")
        mocker.patch.object(mock_num_port2, "eval_and_push_write")

        force_eval_expressions()

        await _eval_changed_expressions(changes=set(), now_ms=0)
        mock_num_port1.eval_and_push_write.assert_called_once()
        mock_num_port2.eval_and_push_write.assert_called_once()

    async def test_force_state_consumed_after_eval_changed_expressions(self, mocker, mock_num_port1, mock_num_port2):
        """Should not re-evaluate a forced port on a subsequent _eval_changed_expressions call without re-forcing."""

        mock_num_port1.set_expression("MUL($nid2, 2)")
        mocker.patch.object(mock_num_port1, "eval_and_push_write")

        force_eval_expressions(mock_num_port1)

        await _eval_changed_expressions(changes={DEP_ASAP}, now_ms=0)
        await _eval_changed_expressions(changes={DEP_ASAP}, now_ms=0)
        mock_num_port1.eval_and_push_write.assert_called_once()

    async def test_forced_port_bypasses_asap_pause(self, mocker, mock_num_port1):
        """Should evaluate a forced port even when its only dep is ASAP but ASAP eval is paused."""

        mock_num_port1.set_expression("TIMEMS()")
        e = mock_num_port1.get_expression()
        mocker.patch.object(mock_num_port1, "eval_and_push_write")

        e.pause_asap_eval(1000)
        force_eval_expressions(mock_num_port1)

        await _eval_changed_expressions(changes={DEP_ASAP}, now_ms=999)
        mock_num_port1.eval_and_push_write.assert_called_once()

    async def test_forced_port_without_expression_not_evaluated(self, mocker, mock_num_port1):
        """Should not evaluate a forced port that has no expression set."""

        mocker.patch.object(mock_num_port1, "eval_and_push_write")

        force_eval_expressions(mock_num_port1)

        await _eval_changed_expressions(changes={DEP_ASAP}, now_ms=0)
        mock_num_port1.eval_and_push_write.assert_not_called()


class TestPauseResume:
    @pytest.fixture(autouse=True)
    def reset_paused(self):
        """Ensure _paused is False before each test and restored after."""
        core_main._paused = False
        yield
        core_main._paused = False

    async def test_resume_allows_read_ports(self, freezer, mocker, mock_num_port1, dummy_utc_datetime):
        """Should allow read_ports() to call _eval_changed_expressions after resume()."""

        freezer.move_to(dummy_utc_datetime)
        await read_ports()  # prime last-time state
        spy = mocker.patch("qtoggleserver.core.main._eval_changed_expressions")
        resume()
        await read_ports()
        spy.assert_called_once()

    async def test_pause_skips_read_ports(self, mocker, mock_num_port1):
        """Should skip _eval_changed_expressions call in read_ports() after pause()."""

        spy = mocker.patch("qtoggleserver.core.main._eval_changed_expressions")
        pause()
        await read_ports()
        spy.assert_not_called()

    async def test_resume_from_paused_state(self, freezer, mocker, mock_num_port1, dummy_utc_datetime):
        """Should resume after an explicit pause, allowing read_ports() to proceed."""

        freezer.move_to(dummy_utc_datetime)
        await read_ports()  # prime last-time state
        pause()
        resume()
        spy = mocker.patch("qtoggleserver.core.main._eval_changed_expressions")
        await read_ports()
        spy.assert_called_once()

    async def test_resume_idempotent(self, freezer, mocker, mock_num_port1, dummy_utc_datetime):
        """Calling resume() multiple times should keep read_ports() running normally."""

        freezer.move_to(dummy_utc_datetime)
        await read_ports()  # prime last-time state
        resume()
        resume()
        spy = mocker.patch("qtoggleserver.core.main._eval_changed_expressions")
        await read_ports()
        spy.assert_called_once()

    async def test_pause_idempotent(self, mocker, mock_num_port1):
        """Calling pause() multiple times should keep read_ports() skipped."""

        spy = mocker.patch("qtoggleserver.core.main._eval_changed_expressions")
        pause()
        pause()
        await read_ports()
        spy.assert_not_called()

    async def test_pause_resume_cycle(self, freezer, mocker, mock_num_port1, dummy_utc_datetime):
        """A full pause -> resume cycle should end with read_ports() executing normally."""

        freezer.move_to(dummy_utc_datetime)
        await read_ports()  # prime last-time state
        pause()
        resume()
        pause()
        resume()
        spy = mocker.patch("qtoggleserver.core.main._eval_changed_expressions")
        await read_ports()
        spy.assert_called_once()


class TestAttrChangeHandler:
    @pytest.fixture(autouse=True)
    def reset_pending(self):
        """Clear pending attr changes before and after each test."""
        core_main._attr_change_handler._pending.clear()
        yield
        core_main._attr_change_handler._pending.clear()

    async def test_port_update_adds_attr_dep(self, mock_num_port1):
        """PortUpdate event should add `$port_id:` to _pending_attr_changes."""

        await core_main._attr_change_handler.handle_event(core_events.PortUpdate(mock_num_port1))
        assert core_main._attr_change_handler._pending == {"$nid1:"}

    async def test_port_add_adds_attr_dep(self, mock_num_port1):
        """PortAdd event should add `$port_id:` to _pending_attr_changes."""

        await core_main._attr_change_handler.handle_event(core_events.PortAdd(mock_num_port1))
        assert core_main._attr_change_handler._pending == {"$nid1:"}

    async def test_port_remove_adds_attr_dep(self, mock_num_port1):
        """PortRemove event should add `$port_id:` to _pending_attr_changes."""

        await core_main._attr_change_handler.handle_event(core_events.PortRemove(mock_num_port1))
        assert core_main._attr_change_handler._pending == {"$nid1:"}

    async def test_device_update_adds_device_dep(self):
        """DeviceUpdate event should add `#:` to _pending_attr_changes."""

        await core_main._attr_change_handler.handle_event(core_events.DeviceUpdate())
        assert core_main._attr_change_handler._pending == {"#:"}

    async def test_value_change_ignored(self, mock_num_port1):
        """ValueChange event should not modify _pending_attr_changes."""

        await core_main._attr_change_handler.handle_event(core_events.ValueChange(None, 42, mock_num_port1))
        assert core_main._attr_change_handler._pending == set()

    async def test_multiple_events_accumulate(self, mock_num_port1, mock_num_port2):
        """Multiple port events should accumulate their dep strings."""

        await core_main._attr_change_handler.handle_event(core_events.PortUpdate(mock_num_port1))
        await core_main._attr_change_handler.handle_event(core_events.PortUpdate(mock_num_port2))
        assert core_main._attr_change_handler._pending == {"$nid1:", "$nid2:"}

    async def test_port_and_device_events_accumulate(self, mock_num_port1):
        """Port and device events should both accumulate into _pending_attr_changes."""

        await core_main._attr_change_handler.handle_event(core_events.PortUpdate(mock_num_port1))
        await core_main._attr_change_handler.handle_event(core_events.DeviceUpdate())
        assert core_main._attr_change_handler._pending == {"$nid1:", "#:"}

    async def test_read_ports_drains_pending_attr_changes(self, freezer, mocker, mock_num_port1, dummy_utc_datetime):
        """read_ports() should include pending port-attr deps in the changes set passed to _eval_changed_expressions."""

        freezer.move_to(dummy_utc_datetime)
        await read_ports()  # prime time state

        core_main._attr_change_handler._pending.add("$nid1:")
        spy = mocker.patch("qtoggleserver.core.main._eval_changed_expressions")
        await read_ports()

        call_changes = spy.call_args[0][0]
        assert "$nid1:" in call_changes

    async def test_read_ports_drains_device_dep(self, freezer, mocker, mock_num_port1, dummy_utc_datetime):
        """read_ports() should include `#:` in changes when a DeviceUpdate was pending."""

        freezer.move_to(dummy_utc_datetime)
        await read_ports()  # prime time state

        core_main._attr_change_handler._pending.add("#:")
        spy = mocker.patch("qtoggleserver.core.main._eval_changed_expressions")
        await read_ports()

        call_changes = spy.call_args[0][0]
        assert "#:" in call_changes

    async def test_read_ports_clears_pending_after_drain(self, freezer, mocker, mock_num_port1, dummy_utc_datetime):
        """_pending must be empty after read_ports() drains it."""

        freezer.move_to(dummy_utc_datetime)
        await read_ports()  # prime time state

        core_main._attr_change_handler._pending.add("$nid1:")
        mocker.patch("qtoggleserver.core.main._eval_changed_expressions")
        await read_ports()

        assert core_main._attr_change_handler._pending == set()

    async def test_port_attr_dep_triggers_expression_eval(self, mocker, mock_num_port1, mock_num_port2):
        """A port whose expression references $nid1: should be evaluated when `$nid1:` is in changes."""

        mock_num_port2.set_writable(True)
        mock_num_port2.set_expression("$nid1:enabled")
        mocker.patch.object(mock_num_port2, "eval_and_push_write")

        await _eval_changed_expressions(changes={"$nid1:"}, now_ms=0)

        mock_num_port2.eval_and_push_write.assert_called_once()

    async def test_device_dep_triggers_expression_eval(self, mocker, mock_num_port1):
        """A port whose expression references #:attr should be evaluated when `#:` is in changes."""

        mock_num_port1.set_writable(True)
        mock_num_port1.set_expression("#:name")
        mocker.patch.object(mock_num_port1, "eval_and_push_write")

        await _eval_changed_expressions(changes={"#:"}, now_ms=0)

        mock_num_port1.eval_and_push_write.assert_called_once()

    async def test_slave_device_update_adds_slave_dep(self):
        """SlaveDeviceUpdate event should add `#slave_name:` to _pending_attr_changes."""

        await core_main._attr_change_handler.handle_event(slaves_events.SlaveDeviceUpdate(_make_mock_slave("slave1")))
        assert core_main._attr_change_handler._pending == {"#slave1:"}

    async def test_slave_device_add_adds_slave_dep(self):
        """SlaveDeviceAdd event should add `#slave_name:` to _pending_attr_changes."""

        await core_main._attr_change_handler.handle_event(slaves_events.SlaveDeviceAdd(_make_mock_slave("slave1")))
        assert core_main._attr_change_handler._pending == {"#slave1:"}

    async def test_slave_device_remove_adds_slave_dep(self):
        """SlaveDeviceRemove event should add `#slave_name:` to _pending_attr_changes."""

        await core_main._attr_change_handler.handle_event(slaves_events.SlaveDeviceRemove(_make_mock_slave("slave1")))
        assert core_main._attr_change_handler._pending == {"#slave1:"}

    async def test_multiple_slave_events_accumulate(self):
        """Multiple slave device events should accumulate distinct dep strings."""

        await core_main._attr_change_handler.handle_event(slaves_events.SlaveDeviceUpdate(_make_mock_slave("slave1")))
        await core_main._attr_change_handler.handle_event(slaves_events.SlaveDeviceUpdate(_make_mock_slave("slave2")))
        assert core_main._attr_change_handler._pending == {"#slave1:", "#slave2:"}

    async def test_slave_dep_triggers_expression_eval(self, mocker, mock_num_port1):
        """A port whose expression references #slave1:attr should be evaluated when `#slave1:` is in changes."""

        mock_num_port1.set_writable(True)
        mock_num_port1.set_expression("#slave1:enabled")
        mocker.patch.object(mock_num_port1, "eval_and_push_write")

        await _eval_changed_expressions(changes={"#slave1:"}, now_ms=0)

        mock_num_port1.eval_and_push_write.assert_called_once()
