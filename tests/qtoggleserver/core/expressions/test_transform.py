async def test_transform_read(mock_num_port1):
    await mock_num_port1.set_attr("transform_read", "MUL($, 10)")
    mock_num_port1.set_last_read_value(4)
    mock_num_port1.set_next_value(4)
    assert await mock_num_port1.read_transformed_value() == 40


async def test_transform_write(mock_num_port1, mocker):
    mock_num_port1.set_writable(True)
    mocker.patch.object(mock_num_port1, "write_value")

    await mock_num_port1.set_attr("transform_write", "MUL($, 10)")
    mock_num_port1.set_last_read_value(4)
    await mock_num_port1.transform_and_write_value(4)
    mock_num_port1.write_value.assert_called_once_with(40)
