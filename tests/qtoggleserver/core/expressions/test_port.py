
import pytest

from qtoggleserver.core.expressions import check_loops, parse, port
from qtoggleserver.core.expressions import CircularDependency


def test_port_value_parse(num_mock_port1, num_mock_port2):
    e = parse('nid1', '$nid2')
    assert isinstance(e, port.PortValue)
    assert e.port_id == 'nid2'
    assert e.get_port() == num_mock_port2


def test_port_value_self_parse(num_mock_port1):
    e = parse('nid1', '$')
    assert isinstance(e, port.PortValue)
    assert e.port_id == 'nid1'
    assert e.get_port() == num_mock_port1


def test_port_value_inexistent(num_mock_port1):
    e = parse('nid1', '$nid2')
    assert isinstance(e, port.PortValue)
    assert e.port_id == 'nid2'
    assert e.get_port() is None


async def test_port_value_circular_dependency(num_mock_port1, num_mock_port2):
    num_mock_port1.set_writable(True)
    num_mock_port2.set_writable(True)

    await num_mock_port1.set_attr('expression', 'ADD($nid2, 10)')
    e2 = parse('nid2', 'ADD($nid1, 10)')
    with pytest.raises(CircularDependency):
        await check_loops(num_mock_port2, e2)


async def test_port_value_allow_self_dependency(num_mock_port1):
    num_mock_port1.set_writable(True)
    await num_mock_port1.set_attr('expression', 'ADD($nid1, 10)')


def test_port_ref_parse(num_mock_port1, num_mock_port2):
    e = parse('nid1', '@nid2')
    assert isinstance(e, port.PortRef)
    assert e.port_id == 'nid2'
    assert e.get_port() == num_mock_port2


def test_port_ref_inexistent(num_mock_port1):
    e = parse('nid1', '@nid2')
    assert isinstance(e, port.PortRef)
    assert e.port_id == 'nid2'
    assert e.get_port() is None
