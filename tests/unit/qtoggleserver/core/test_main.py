import time

from datetime import datetime, timedelta

from qtoggleserver.core.expressions import DEP_ASAP, DEP_DAY, DEP_HOUR, DEP_MINUTE, DEP_MONTH, DEP_SECOND, DEP_YEAR
from qtoggleserver.core.main import force_eval_expressions, handle_value_changes, update


class TestUpdate:
    async def test_change_time_asap(self, freezer, mocker, mock_num_port1, dummy_utc_datetime):
        """Should call `handle_value_changes` with {DEP_ASAP}, regardless of time changes."""

        freezer.move_to(dummy_utc_datetime)
        await update()
        spy_handle_value_changes = mocker.patch("qtoggleserver.core.main.handle_value_changes")
        await update()
        spy_handle_value_changes.assert_called_once_with({DEP_ASAP}, {}, int(time.time() * 1000))

    async def test_change_time_second(self, freezer, mocker, mock_num_port1, dummy_utc_datetime):
        """Should call `handle_value_changes` with {DEP_ASAP, DEP_SECOND} when second changes."""

        freezer.move_to(dummy_utc_datetime)
        await update()

        freezer.move_to(dummy_utc_datetime + timedelta(seconds=1))
        spy_handle_value_changes = mocker.patch("qtoggleserver.core.main.handle_value_changes")
        await update()
        spy_handle_value_changes.assert_called_once_with({DEP_ASAP, DEP_SECOND}, {}, int(time.time() * 1000))

    async def test_change_time_minute(self, freezer, mocker, mock_num_port1, dummy_utc_datetime):
        """Should call `handle_value_changes` with {DEP_ASAP, DEP_SECOND, DEP_MINUTE} when minute changes."""

        freezer.move_to(dummy_utc_datetime)
        await update()

        freezer.move_to(dummy_utc_datetime + timedelta(minutes=1))
        spy_handle_value_changes = mocker.patch("qtoggleserver.core.main.handle_value_changes")
        await update()
        spy_handle_value_changes.assert_called_once_with(
            {DEP_ASAP, DEP_SECOND, DEP_MINUTE}, {}, int(time.time() * 1000)
        )

    async def test_change_time_hour(self, freezer, mocker, mock_num_port1, dummy_utc_datetime):
        """Should call `handle_value_changes` with {DEP_ASAP, DEP_SECOND, DEP_MINUTE, DEP_HOUR} when hour changes."""

        freezer.move_to(dummy_utc_datetime)
        await update()

        freezer.move_to(dummy_utc_datetime + timedelta(hours=1))
        spy_handle_value_changes = mocker.patch("qtoggleserver.core.main.handle_value_changes")
        await update()
        spy_handle_value_changes.assert_called_once_with(
            {DEP_ASAP, DEP_SECOND, DEP_MINUTE, DEP_HOUR}, {}, int(time.time() * 1000)
        )

    async def test_change_time_day(self, freezer, mocker, mock_num_port1, dummy_utc_datetime):
        """Should call `handle_value_changes` with {DEP_ASAP, DEP_SECOND, DEP_MINUTE, DEP_HOUR, DEP_DAY} when day
        changes."""

        freezer.move_to(datetime(2019, 1, 30, 23, 30, 30))
        await update()

        freezer.move_to(datetime(2019, 1, 31, 0, 0, 0))
        spy_handle_value_changes = mocker.patch("qtoggleserver.core.main.handle_value_changes")
        await update()
        spy_handle_value_changes.assert_called_once_with(
            {DEP_ASAP, DEP_SECOND, DEP_MINUTE, DEP_HOUR, DEP_DAY}, {}, int(time.time() * 1000)
        )

    async def test_change_time_month(self, freezer, mocker, mock_num_port1, dummy_utc_datetime):
        """Should call `handle_value_changes` with {DEP_ASAP, DEP_SECOND, DEP_MINUTE, DEP_HOUR, DEP_DAY, DEP_MONTH} when
        month changes."""

        freezer.move_to(datetime(2019, 1, 31, 23, 30, 30))
        await update()

        freezer.move_to(datetime(2019, 2, 1, 0, 0, 0))
        spy_handle_value_changes = mocker.patch("qtoggleserver.core.main.handle_value_changes")
        await update()
        spy_handle_value_changes.assert_called_once_with(
            {DEP_ASAP, DEP_SECOND, DEP_MINUTE, DEP_HOUR, DEP_DAY, DEP_MONTH}, {}, int(time.time() * 1000)
        )

    async def test_change_time_year(self, freezer, mocker, mock_num_port1, dummy_utc_datetime):
        """Should call `handle_value_changes` with {DEP_ASAP, DEP_SECOND, DEP_MINUTE, DEP_HOUR, DEP_DAY, DEP_MONTH,
        DEP_YEAR} when year changes."""

        freezer.move_to(datetime(2019, 12, 31, 23, 30, 30))
        await update()

        freezer.move_to(datetime(2020, 1, 1, 0, 0, 0))
        spy_handle_value_changes = mocker.patch("qtoggleserver.core.main.handle_value_changes")
        await update()
        spy_handle_value_changes.assert_called_once_with(
            {DEP_ASAP, DEP_SECOND, DEP_MINUTE, DEP_HOUR, DEP_DAY, DEP_MONTH, DEP_YEAR}, {}, int(time.time() * 1000)
        )


class TestHandleValueChanges:
    async def test_self_port_value_trigger_eval(self, mocker, mock_num_port1):
        """Should trigger a port's expression evaluation if the expression depends on itself through `$`."""

        mock_num_port1.set_writable(True)
        mock_num_port1.set_expression("MUL($, 2)")
        mocker.patch.object(mock_num_port1, "eval_and_push_write")

        await handle_value_changes(changed_set={mock_num_port1}, value_pairs={mock_num_port1: (10, 20)}, now_ms=0)
        mock_num_port1.eval_and_push_write.assert_called_once()

    async def test_own_port_value_trigger_eval(self, mocker, mock_num_port1):
        """Should trigger a port's expression evaluation if the expression depends on itself through `$<own_id>`."""

        mock_num_port1.set_writable(True)
        mock_num_port1.set_expression("MUL($nid1, 2)")
        mocker.patch.object(mock_num_port1, "eval_and_push_write")

        await handle_value_changes(changed_set={mock_num_port1}, value_pairs={mock_num_port1: (10, 20)}, now_ms=0)
        mock_num_port1.eval_and_push_write.assert_called_once()

    async def test_disabled_port_no_trigger_eval(self, mocker, mock_num_port1):
        """Should not trigger a port's expression evaluation if the port is disabled."""

        mock_num_port1.set_writable(True)
        mock_num_port1.set_expression("TIMEMS()")
        force_eval_expressions(mock_num_port1)

        (mocker.patch.object(mock_num_port1, "eval_and_push_write"),)
        (mocker.patch.object(mock_num_port1, "is_enabled", return_value=False),)

        await handle_value_changes(changed_set=set(), value_pairs={}, now_ms=0)
        mock_num_port1.eval_and_push_write.assert_not_called()

    async def test_asap_trigger_eval(self, mocker, mock_num_port1):
        """Should trigger a port's expression evaluation if the expression depends on ASAP."""

        mock_num_port1.set_writable(True)
        mock_num_port1.set_expression("TIMEMS()")
        mocker.patch.object(mock_num_port1, "eval_and_push_write")

        await handle_value_changes(changed_set={DEP_ASAP}, value_pairs={}, now_ms=0)
        mock_num_port1.eval_and_push_write.assert_called_once()

    async def test_asap_eval_paused_no_trigger_eval(self, mocker, mock_num_port1):
        """Should not trigger a port's expression evaluation if the expression depends on ASAP but is paused."""

        mock_num_port1.set_writable(True)
        mock_num_port1.set_expression("TIMEMS()")
        e = mock_num_port1.get_expression()
        mocker.patch.object(mock_num_port1, "eval_and_push_write")

        e.pause_asap_eval(1000)
        await handle_value_changes(changed_set={DEP_ASAP}, value_pairs={}, now_ms=999)
        mock_num_port1.eval_and_push_write.assert_not_called()

    async def test_asap_eval_not_paused_trigger_eval(self, mocker, mock_num_port1):
        """Should trigger a port's expression evaluation if the expression depends on ASAP and pause expired."""

        mock_num_port1.set_writable(True)
        mock_num_port1.set_expression("TIMEMS()")
        e = mock_num_port1.get_expression()
        mocker.patch.object(mock_num_port1, "eval_and_push_write")

        e.pause_asap_eval(1000)
        await handle_value_changes(changed_set={DEP_ASAP}, value_pairs={}, now_ms=1000)
        mock_num_port1.eval_and_push_write.assert_called_once()
