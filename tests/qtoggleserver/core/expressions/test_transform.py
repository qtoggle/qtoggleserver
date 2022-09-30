
async def test_transform_read(num_mock_port1):
    await num_mock_port1.set_attr('transform_read', 'MUL($, 10)')
    num_mock_port1.set_last_read_value(4)
    num_mock_port1.set_next_value(4)
    assert await num_mock_port1.read_transformed_value() == 40


async def test_transform_write(mocker, num_mock_port1):
    num_mock_port1.set_writable(True)
    mocker.patch.object(num_mock_port1, 'write_value')

    await num_mock_port1.set_attr('transform_write', 'MUL($, 10)')
    num_mock_port1.set_last_read_value(4)
    await num_mock_port1.transform_and_write_value(4)
    num_mock_port1.write_value.assert_called_once_with(40)
