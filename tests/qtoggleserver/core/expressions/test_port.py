import asyncio

import pytest

from qtoggleserver.core.expressions import ROLE_VALUE, CircularDependency, check_loops, parse, port


def test_port_value_parse(num_mock_port1, num_mock_port2):
    e = parse('nid1', '$nid2', role=ROLE_VALUE)
    assert isinstance(e, port.PortValue)
    assert e.port_id == 'nid2'
    assert e.get_port() == num_mock_port2


def test_port_value_self_parse(num_mock_port1):
    e = parse('nid1', '$', role=ROLE_VALUE)
    assert isinstance(e, port.PortValue)
    assert e.port_id == 'nid1'
    assert e.get_port() == num_mock_port1


def test_port_value_inexistent(num_mock_port1):
    e = parse('nid1', '$nid2', role=ROLE_VALUE)
    assert isinstance(e, port.PortValue)
    assert e.port_id == 'nid2'
    assert e.get_port() is None


async def test_port_value_circular_dependency(num_mock_port1, num_mock_port2):
    num_mock_port1.set_writable(True)
    num_mock_port2.set_writable(True)

    await num_mock_port1.set_attr('expression', 'ADD($nid2, 10)')
    e2 = parse('nid2', 'ADD($nid1, 10)', role=ROLE_VALUE)
    with pytest.raises(CircularDependency):
        await check_loops(num_mock_port2, e2)


async def test_port_value_self_immediate_value(num_mock_port1):
    num_mock_port1.set_writable(True)
    num_mock_port1.set_last_read_value(15)
    await num_mock_port1.set_attr('expression', 'ADD($, 1)')
    num_mock_port1.set_last_read_value(25)
    await asyncio.sleep(0.1)
    assert num_mock_port1.get_last_written_value() == 26


async def test_port_value_snapshot_value(num_mock_port1):
    num_mock_port1.set_writable(True)
    num_mock_port1.set_last_read_value(15)
    await num_mock_port1.set_attr('expression', 'ADD($nid1, 1)')
    num_mock_port1.set_last_read_value(25)
    await asyncio.sleep(0.1)
    assert num_mock_port1.get_last_written_value() == 16


async def test_port_value_snapshot_value_transform_read(num_mock_port1):
    await num_mock_port1.set_attr('transform_read', 'MUL($, 10)')
    num_mock_port1.set_last_read_value(4)
    num_mock_port1.set_next_value(5)
    assert await num_mock_port1.read_transformed_value() == 50


async def test_port_value_snapshot_value_transform_write(mocker, num_mock_port1):
    num_mock_port1.set_writable(True)
    mocker.patch.object(num_mock_port1, 'write_value')

    await num_mock_port1.set_attr('transform_write', 'MUL($, 10)')
    num_mock_port1.set_last_read_value(4)
    num_mock_port1.set_next_value(5)

    await num_mock_port1.transform_and_write_value(6)
    num_mock_port1.write_value.assert_called_once_with(60)


async def test_port_value_allow_self_dependency(num_mock_port1):
    num_mock_port1.set_writable(True)
    await num_mock_port1.set_attr('expression', 'ADD($nid1, 10)')


def test_port_ref_parse(num_mock_port1, num_mock_port2):
    e = parse('nid1', '@nid2', role=ROLE_VALUE)
    assert isinstance(e, port.PortRef)
    assert e.port_id == 'nid2'
    assert e.get_port() == num_mock_port2


def test_port_ref_inexistent(num_mock_port1):
    e = parse('nid1', '@nid2', role=ROLE_VALUE)
    assert isinstance(e, port.PortRef)
    assert e.port_id == 'nid2'
    assert e.get_port() is None
