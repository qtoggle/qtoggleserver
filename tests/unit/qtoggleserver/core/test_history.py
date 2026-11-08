import pytest

from qtoggleserver.core import events as core_events
from qtoggleserver.core import history as core_history


@pytest.fixture
def mock_save_sample(mocker):
    return mocker.patch("qtoggleserver.persist.save_sample")


class TestSaveSample:
    async def test_saved(self, mock_num_port1, mock_save_sample) -> None:
        mock_num_port1.set_read_value(5)

        await core_history.save_sample(mock_num_port1, 1000)

        mock_save_sample.assert_called_once_with("value_history", "nid1", 1000, 5.0)

    async def test_saved_when_online(self, mock_num_port1, mock_save_sample) -> None:
        mock_num_port1.set_read_value(5)
        mock_num_port1.set_online(True)

        await core_history.save_sample(mock_num_port1, 1000)

        mock_save_sample.assert_called_once()

    async def test_skipped_when_offline(self, mock_num_port1, mock_save_sample) -> None:
        mock_num_port1.set_read_value(5)
        mock_num_port1.set_online(False)

        await core_history.save_sample(mock_num_port1, 1000)

        mock_save_sample.assert_not_called()

    async def test_skipped_when_unavailable(self, mock_num_port1, mock_save_sample) -> None:
        await core_history.save_sample(mock_num_port1, 1000)

        mock_save_sample.assert_not_called()


class TestValueChangeSample:
    """Test the samples saved on value change (`history_interval` set to `-1`), which bypass the sampling task."""

    @pytest.fixture(autouse=True)
    def real_date_time(self, mocker) -> None:
        mocker.patch("qtoggleserver.system.date.has_real_date_time", return_value=True)

    async def test_saved_when_online(self, mock_num_port1, mock_save_sample, mocker) -> None:
        mocker.patch.object(mock_num_port1, "get_history_interval", return_value=-1)
        mock_num_port1.set_read_value(5)
        mock_num_port1.set_online(True)

        await core_history.HistoryEventHandler().handle_event(core_events.ValueChange(4, 5, mock_num_port1))

        mock_save_sample.assert_called_once()

    async def test_skipped_when_offline(self, mock_num_port1, mock_save_sample, mocker) -> None:
        mocker.patch.object(mock_num_port1, "get_history_interval", return_value=-1)
        mock_num_port1.set_read_value(5)
        mock_num_port1.set_online(False)

        await core_history.HistoryEventHandler().handle_event(core_events.ValueChange(4, 5, mock_num_port1))

        mock_save_sample.assert_not_called()
