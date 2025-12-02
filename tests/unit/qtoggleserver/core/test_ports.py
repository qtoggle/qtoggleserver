class TestPort:
    def test_get_last_value_pending(self, mock_num_port1):
        """Should return the pending value, since it's not None."""

        mock_num_port1._pending_value = 100
        mock_num_port1._last_written_value = None
        mock_num_port1._last_read_value = None
        assert mock_num_port1.get_last_value() == 100

        mock_num_port1._last_written_value = (200, 2000)
        mock_num_port1._last_read_value = (300, 1000)
        assert mock_num_port1.get_last_value() == 100

    def test_get_last_value_last_written(self, mock_num_port1):
        """Should return the last written value."""

        mock_num_port1._pending_value = None
        mock_num_port1._last_written_value = (200, 2000)
        mock_num_port1._last_read_value = None
        assert mock_num_port1.get_last_value() == 200

        mock_num_port1._last_read_value = (300, 1000)  # older timestamp
        assert mock_num_port1.get_last_value() == 200

    def test_get_last_value_last_read(self, mock_num_port1):
        """Should return the last read value."""

        mock_num_port1._pending_value = None
        mock_num_port1._last_written_value = None
        mock_num_port1._last_read_value = (300, 2000)
        assert mock_num_port1.get_last_value() == 300

        mock_num_port1._last_written_value = (200, 1000)  # newer timestamp
        assert mock_num_port1.get_last_value() == 300

    def test_push_eval(self, mock_num_port1, mock_num_port2, mocker):
        """Should schedule an expression evaluation. Should gather all ports using `core.ports.get_all()` and call
        `get_last_value()` on each of them to build the eval context."""

        mocker.patch("qtoggleserver.core.ports.get_all", return_value=[mock_num_port1, mock_num_port2])
        mocker.patch.object(mock_num_port1, "_make_eval_context", return_value="dummy_eval_context")
        mocker.patch.object(mock_num_port1, "get_last_value", return_value=42)
        mocker.patch.object(mock_num_port2, "get_last_value", return_value=84)
        mocker.patch.object(mock_num_port1._eval_queue, "put_nowait")

        mock_num_port1.push_eval(1234)

        mock_num_port1._make_eval_context.assert_called_once_with({"nid1": 42, "nid2": 84}, 1234)
        mock_num_port1._eval_queue.put_nowait.assert_called_once_with("dummy_eval_context")
