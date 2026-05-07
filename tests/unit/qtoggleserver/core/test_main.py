import time

from datetime import datetime, timedelta

import pytest

from qtoggleserver.core import main as core_main
from qtoggleserver.core import ports as core_ports
from qtoggleserver.core.expressions import DEP_ASAP, DEP_DAY, DEP_HOUR, DEP_MINUTE, DEP_MONTH, DEP_SECOND, DEP_YEAR
from qtoggleserver.core.main import force_eval_expressions, handle_changes, pause, read_ports, resume
from tests.unit.qtoggleserver.mock.ports import MockNumberPort


class TestReadPorts:
    async def test_change_time_asap(self, freezer, mocker, mock_num_port1, dummy_utc_datetime):
        """Should call `handle_changes` with {DEP_ASAP}, regardless of time changes."""

        freezer.move_to(dummy_utc_datetime)
        await read_ports()
        spy_handle_value_changes = mocker.patch("qtoggleserver.core.main.handle_changes")
        await read_ports()
        spy_handle_value_changes.assert_called_once_with([mock_num_port1], {DEP_ASAP}, {}, int(time.time() * 1000))

    async def test_change_time_second(self, freezer, mocker, mock_num_port1, dummy_utc_datetime):
        """Should call `handle_changes` with {DEP_ASAP, DEP_SECOND} when second changes."""

        freezer.move_to(dummy_utc_datetime)
        await read_ports()

        freezer.move_to(dummy_utc_datetime + timedelta(seconds=1))
        spy_handle_value_changes = mocker.patch("qtoggleserver.core.main.handle_changes")
        await read_ports()
        spy_handle_value_changes.assert_called_once_with(
            [mock_num_port1], {DEP_ASAP, DEP_SECOND}, {}, int(time.time() * 1000)
        )

    async def test_change_time_minute(self, freezer, mocker, mock_num_port1, dummy_utc_datetime):
        """Should call `handle_changes` with {DEP_ASAP, DEP_SECOND, DEP_MINUTE} when minute changes."""

        freezer.move_to(dummy_utc_datetime)
        await read_ports()

        freezer.move_to(dummy_utc_datetime + timedelta(minutes=1))
        spy_handle_value_changes = mocker.patch("qtoggleserver.core.main.handle_changes")
        await read_ports()
        spy_handle_value_changes.assert_called_once_with(
            [mock_num_port1], {DEP_ASAP, DEP_SECOND, DEP_MINUTE}, {}, int(time.time() * 1000)
        )

    async def test_change_time_hour(self, freezer, mocker, mock_num_port1, dummy_utc_datetime):
        """Should call `handle_changes` with {DEP_ASAP, DEP_SECOND, DEP_MINUTE, DEP_HOUR} when hour changes."""

        freezer.move_to(dummy_utc_datetime)
        await read_ports()

        freezer.move_to(dummy_utc_datetime + timedelta(hours=1))
        spy_handle_value_changes = mocker.patch("qtoggleserver.core.main.handle_changes")
        await read_ports()
        spy_handle_value_changes.assert_called_once_with(
            [mock_num_port1], {DEP_ASAP, DEP_SECOND, DEP_MINUTE, DEP_HOUR}, {}, int(time.time() * 1000)
        )

    async def test_change_time_day(self, freezer, mocker, mock_num_port1, dummy_utc_datetime):
        """Should call `handle_changes` with {DEP_ASAP, DEP_SECOND, DEP_MINUTE, DEP_HOUR, DEP_DAY} when day
        changes."""

        freezer.move_to(datetime(2019, 1, 30, 23, 30, 30))
        await read_ports()

        freezer.move_to(datetime(2019, 1, 31, 0, 0, 0))
        spy_handle_value_changes = mocker.patch("qtoggleserver.core.main.handle_changes")
        await read_ports()
        spy_handle_value_changes.assert_called_once_with(
            [mock_num_port1], {DEP_ASAP, DEP_SECOND, DEP_MINUTE, DEP_HOUR, DEP_DAY}, {}, int(time.time() * 1000)
        )

    async def test_change_time_month(self, freezer, mocker, mock_num_port1, dummy_utc_datetime):
        """Should call `handle_changes` with {DEP_ASAP, DEP_SECOND, DEP_MINUTE, DEP_HOUR, DEP_DAY, DEP_MONTH} when
        month changes."""

        freezer.move_to(datetime(2019, 1, 31, 23, 30, 30))
        await read_ports()

        freezer.move_to(datetime(2019, 2, 1, 0, 0, 0))
        spy_handle_value_changes = mocker.patch("qtoggleserver.core.main.handle_changes")
        await read_ports()
        spy_handle_value_changes.assert_called_once_with(
            [mock_num_port1],
            {DEP_ASAP, DEP_SECOND, DEP_MINUTE, DEP_HOUR, DEP_DAY, DEP_MONTH},
            {},
            int(time.time() * 1000),
        )

    async def test_change_time_year(self, freezer, mocker, mock_num_port1, dummy_utc_datetime):
        """Should call `handle_changes` with {DEP_ASAP, DEP_SECOND, DEP_MINUTE, DEP_HOUR, DEP_DAY, DEP_MONTH,
        DEP_YEAR} when year changes."""

        freezer.move_to(datetime(2019, 12, 31, 23, 30, 30))
        await read_ports()

        freezer.move_to(datetime(2020, 1, 1, 0, 0, 0))
        spy_handle_value_changes = mocker.patch("qtoggleserver.core.main.handle_changes")
        await read_ports()
        spy_handle_value_changes.assert_called_once_with(
            [mock_num_port1],
            {DEP_ASAP, DEP_SECOND, DEP_MINUTE, DEP_HOUR, DEP_DAY, DEP_MONTH, DEP_YEAR},
            {},
            int(time.time() * 1000),
        )

    async def test_ports_to_read_specific_ports(
        self, freezer, mocker, mock_num_port1, mock_num_port2, dummy_utc_datetime
    ):
        """Should only read specified ports when `ports_to_read` is provided, while passing all ports to
        handle_changes."""

        freezer.move_to(dummy_utc_datetime)
        await read_ports()
        spy_handle_value_changes = mocker.patch("qtoggleserver.core.main.handle_changes")

        await read_ports(ports_to_read=[mock_num_port2])
        spy_handle_value_changes.assert_called_once_with(
            [mock_num_port1, mock_num_port2], {DEP_ASAP}, {}, int(time.time() * 1000)
        )

    async def test_ports_to_read_skip_time_changes(self, freezer, mocker, mock_num_port1, dummy_utc_datetime):
        """Should not add time dependencies when `ports_to_read` is provided, even if time changes."""

        freezer.move_to(dummy_utc_datetime)
        await read_ports()

        freezer.move_to(dummy_utc_datetime + timedelta(seconds=1))
        spy_handle_value_changes = mocker.patch("qtoggleserver.core.main.handle_changes")

        await read_ports(ports_to_read=[mock_num_port1])
        spy_handle_value_changes.assert_called_once_with([mock_num_port1], {DEP_ASAP}, {}, int(time.time() * 1000))

    async def test_ports_to_read_empty_list(self, freezer, mocker, mock_num_port1, dummy_utc_datetime):
        """Should handle empty ports list gracefully when `ports_to_read` is an empty list."""

        freezer.move_to(dummy_utc_datetime)
        await read_ports()
        spy_handle_value_changes = mocker.patch("qtoggleserver.core.main.handle_changes")

        await read_ports(ports_to_read=[])
        spy_handle_value_changes.assert_called_once_with([mock_num_port1], {DEP_ASAP}, {}, int(time.time() * 1000))


class TestHandleChanges:
    async def test_self_port_value_trigger_eval(self, mocker, mock_num_port1):
        """Should trigger a port's expression evaluation if the expression depends on itself through `$`."""

        mock_num_port1.set_writable(True)
        mock_num_port1.set_expression("MUL($, 2)")
        mocker.patch.object(mock_num_port1, "eval_and_push_write")

        await handle_changes(
            [mock_num_port1], changed_set={mock_num_port1}, value_pairs={mock_num_port1: (10, 20)}, now_ms=0
        )
        mock_num_port1.eval_and_push_write.assert_called_once()

    async def test_own_port_value_trigger_eval(self, mocker, mock_num_port1):
        """Should trigger a port's expression evaluation if the expression depends on itself through `$<own_id>`."""

        mock_num_port1.set_writable(True)
        mock_num_port1.set_expression("MUL($nid1, 2)")
        mocker.patch.object(mock_num_port1, "eval_and_push_write")

        await handle_changes(
            [mock_num_port1], changed_set={mock_num_port1}, value_pairs={mock_num_port1: (10, 20)}, now_ms=0
        )
        mock_num_port1.eval_and_push_write.assert_called_once()

    async def test_disabled_port_no_trigger_eval(self, mocker, mock_num_port1):
        """Should not trigger a port's expression evaluation if the port is disabled."""

        mock_num_port1.set_writable(True)
        mock_num_port1.set_expression("TIMEMS()")
        force_eval_expressions(mock_num_port1)

        (mocker.patch.object(mock_num_port1, "eval_and_push_write"),)
        (mocker.patch.object(mock_num_port1, "is_enabled", return_value=False),)

        await handle_changes([mock_num_port1], changed_set=set(), value_pairs={}, now_ms=0)
        mock_num_port1.eval_and_push_write.assert_not_called()

    async def test_asap_trigger_eval(self, mocker, mock_num_port1):
        """Should trigger a port's expression evaluation if the expression depends on ASAP."""

        mock_num_port1.set_writable(True)
        mock_num_port1.set_expression("TIMEMS()")
        mocker.patch.object(mock_num_port1, "eval_and_push_write")

        await handle_changes([mock_num_port1], changed_set={DEP_ASAP}, value_pairs={}, now_ms=0)
        mock_num_port1.eval_and_push_write.assert_called_once()

    async def test_asap_eval_paused_no_trigger_eval(self, mocker, mock_num_port1):
        """Should not trigger a port's expression evaluation if the expression depends on ASAP but is paused."""

        mock_num_port1.set_writable(True)
        mock_num_port1.set_expression("TIMEMS()")
        e = mock_num_port1.get_expression()
        mocker.patch.object(mock_num_port1, "eval_and_push_write")

        e.pause_asap_eval(1000)
        await handle_changes([mock_num_port1], changed_set={DEP_ASAP}, value_pairs={}, now_ms=999)
        mock_num_port1.eval_and_push_write.assert_not_called()

    async def test_asap_eval_not_paused_trigger_eval(self, mocker, mock_num_port1):
        """Should trigger a port's expression evaluation if the expression depends on ASAP and pause expired."""

        mock_num_port1.set_writable(True)
        mock_num_port1.set_expression("TIMEMS()")
        e = mock_num_port1.get_expression()
        mocker.patch.object(mock_num_port1, "eval_and_push_write")

        e.pause_asap_eval(1000)
        await handle_changes([mock_num_port1], changed_set={DEP_ASAP}, value_pairs={}, now_ms=1000)
        mock_num_port1.eval_and_push_write.assert_called_once()

    async def test_removed_port_not_evaluated(self, mocker, mock_num_port2):
        """Should not evaluate a removed port even when a dep it used to depend on changes."""

        port = await core_ports.load_one(MockNumberPort, {"port_id": "nid_temp", "value": None})
        await port.enable()
        port.set_expression("MUL($nid2, 2)")
        mocker.patch.object(port, "eval_and_push_write")

        await port.remove(persisted_data=False)

        await handle_changes(
            list(core_ports.get_all()),
            changed_set={mock_num_port2},
            value_pairs={mock_num_port2: (1, 2)},
            now_ms=0,
        )
        port.eval_and_push_write.assert_not_called()

    async def test_expression_set_triggers_eval_via_deps(self, mocker, mock_num_port1, mock_num_port2):
        """Should evaluate a port via the deps map after its expression is set and a dep changes."""

        mock_num_port2.set_expression("MUL($nid1, 2)")
        mocker.patch.object(mock_num_port2, "eval_and_push_write")

        await handle_changes(
            [mock_num_port1, mock_num_port2],
            changed_set={mock_num_port1},
            value_pairs={mock_num_port1: (1, 2)},
            now_ms=0,
        )
        mock_num_port2.eval_and_push_write.assert_called_once()

    async def test_expression_cleared_stops_eval(self, mocker, mock_num_port1, mock_num_port2):
        """Should not evaluate a port after its expression is cleared, even when a former dep changes."""

        mock_num_port1.set_expression("MUL($nid2, 2)")
        mock_num_port1.set_writable(True)
        await mock_num_port1.attr_set_expression("")
        mocker.patch.object(mock_num_port1, "eval_and_push_write")

        await handle_changes(
            [mock_num_port1, mock_num_port2],
            changed_set={mock_num_port2},
            value_pairs={mock_num_port2: (1, 2)},
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
        """Should evaluate a forced port even when changed_set contains no dep that port's expression uses."""

        mock_num_port1.set_expression("MUL($nid2, 2)")
        mocker.patch.object(mock_num_port1, "eval_and_push_write")

        force_eval_expressions(mock_num_port1)

        await handle_changes([mock_num_port1], changed_set={DEP_ASAP}, value_pairs={}, now_ms=0)
        mock_num_port1.eval_and_push_write.assert_called_once()

    async def test_force_all_evaluates_all_expression_ports(self, mocker, mock_num_port1, mock_num_port2):
        """Should evaluate all expression ports when force_eval_expressions() is called with no argument."""

        mock_num_port1.set_expression("MUL($nid2, 2)")
        mock_num_port2.set_expression("ADD($nid1, 1)")
        mocker.patch.object(mock_num_port1, "eval_and_push_write")
        mocker.patch.object(mock_num_port2, "eval_and_push_write")

        force_eval_expressions()

        await handle_changes([mock_num_port1, mock_num_port2], changed_set=set(), value_pairs={}, now_ms=0)
        mock_num_port1.eval_and_push_write.assert_called_once()
        mock_num_port2.eval_and_push_write.assert_called_once()

    async def test_force_state_consumed_after_handle_changes(self, mocker, mock_num_port1, mock_num_port2):
        """Should not re-evaluate a forced port on a subsequent handle_changes call without re-forcing."""

        mock_num_port1.set_expression("MUL($nid2, 2)")
        mocker.patch.object(mock_num_port1, "eval_and_push_write")

        force_eval_expressions(mock_num_port1)

        await handle_changes([mock_num_port1], changed_set={DEP_ASAP}, value_pairs={}, now_ms=0)
        await handle_changes([mock_num_port1], changed_set={DEP_ASAP}, value_pairs={}, now_ms=0)
        mock_num_port1.eval_and_push_write.assert_called_once()

    async def test_forced_port_bypasses_asap_pause(self, mocker, mock_num_port1):
        """Should evaluate a forced port even when its only dep is ASAP but ASAP eval is paused."""

        mock_num_port1.set_expression("TIMEMS()")
        e = mock_num_port1.get_expression()
        mocker.patch.object(mock_num_port1, "eval_and_push_write")

        e.pause_asap_eval(1000)
        force_eval_expressions(mock_num_port1)

        await handle_changes([mock_num_port1], changed_set={DEP_ASAP}, value_pairs={}, now_ms=999)
        mock_num_port1.eval_and_push_write.assert_called_once()

    async def test_forced_port_without_expression_not_evaluated(self, mocker, mock_num_port1):
        """Should not evaluate a forced port that has no expression set."""

        mocker.patch.object(mock_num_port1, "eval_and_push_write")

        force_eval_expressions(mock_num_port1)

        await handle_changes([mock_num_port1], changed_set={DEP_ASAP}, value_pairs={}, now_ms=0)
        mock_num_port1.eval_and_push_write.assert_not_called()


class TestPauseResume:
    @pytest.fixture(autouse=True)
    def reset_paused(self):
        """Ensure _paused is False before each test and restored after."""
        core_main._paused = False
        yield
        core_main._paused = False

    async def test_resume_allows_read_ports(self, freezer, mocker, mock_num_port1, dummy_utc_datetime):
        """Should allow read_ports() to call handle_changes after resume()."""

        freezer.move_to(dummy_utc_datetime)
        await read_ports()  # prime last-time state
        spy = mocker.patch("qtoggleserver.core.main.handle_changes")
        resume()
        await read_ports()
        spy.assert_called_once()

    async def test_pause_skips_read_ports(self, mocker, mock_num_port1):
        """Should skip handle_changes call in read_ports() after pause()."""

        spy = mocker.patch("qtoggleserver.core.main.handle_changes")
        pause()
        await read_ports()
        spy.assert_not_called()

    async def test_resume_from_paused_state(self, freezer, mocker, mock_num_port1, dummy_utc_datetime):
        """Should resume after an explicit pause, allowing read_ports() to proceed."""

        freezer.move_to(dummy_utc_datetime)
        await read_ports()  # prime last-time state
        pause()
        resume()
        spy = mocker.patch("qtoggleserver.core.main.handle_changes")
        await read_ports()
        spy.assert_called_once()

    async def test_resume_idempotent(self, freezer, mocker, mock_num_port1, dummy_utc_datetime):
        """Calling resume() multiple times should keep read_ports() running normally."""

        freezer.move_to(dummy_utc_datetime)
        await read_ports()  # prime last-time state
        resume()
        resume()
        spy = mocker.patch("qtoggleserver.core.main.handle_changes")
        await read_ports()
        spy.assert_called_once()

    async def test_pause_idempotent(self, mocker, mock_num_port1):
        """Calling pause() multiple times should keep read_ports() skipped."""

        spy = mocker.patch("qtoggleserver.core.main.handle_changes")
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
        spy = mocker.patch("qtoggleserver.core.main.handle_changes")
        await read_ports()
        spy.assert_called_once()
