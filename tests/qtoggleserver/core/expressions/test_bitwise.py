
import pytest

from qtoggleserver.core.expressions import bitwise, Function
from qtoggleserver.core.expressions import InvalidNumberOfArguments


async def test_bitand_simple(literal_three, literal_ten):
    result = await bitwise.BitAndFunction([literal_three, literal_ten]).eval()
    assert result == 2


def test_bitand_parse():
    e = Function.parse(None, 'BITAND(1, 2)', 0)
    assert isinstance(e, bitwise.BitAndFunction)


def test_bitand_num_args():
    with pytest.raises(InvalidNumberOfArguments):
        Function.parse(None, 'BITAND(1)', 0)

    with pytest.raises(InvalidNumberOfArguments):
        Function.parse(None, 'BITAND(1, 2, 3)', 0)


async def test_bitor_simple(literal_three, literal_ten):
    result = await bitwise.BitOrFunction([literal_three, literal_ten]).eval()
    assert result == 11


def test_bitor_parse():
    e = Function.parse(None, 'BITOR(1, 2)', 0)
    assert isinstance(e, bitwise.BitOrFunction)


def test_bitor_num_args():
    with pytest.raises(InvalidNumberOfArguments):
        Function.parse(None, 'BITOR(1)', 0)

    with pytest.raises(InvalidNumberOfArguments):
        Function.parse(None, 'BITOR(1, 2, 3)', 0)


async def test_bitnot_simple(literal_three):
    result = await bitwise.BitNotFunction([literal_three]).eval()
    assert result == -4


def test_bitnot_parse():
    e = Function.parse(None, 'BITNOT(1)', 0)
    assert isinstance(e, bitwise.BitNotFunction)


def test_bitnot_num_args():
    with pytest.raises(InvalidNumberOfArguments):
        Function.parse(None, 'BITNOT()', 0)

    with pytest.raises(InvalidNumberOfArguments):
        Function.parse(None, 'BITNOT(1, 2)', 0)


async def test_bitxor_simple(literal_three, literal_ten):
    result = await bitwise.BitXOrFunction([literal_three, literal_ten]).eval()
    assert result == 9


def test_bitxor_parse():
    e = Function.parse(None, 'BITXOR(1, 2)', 0)
    assert isinstance(e, bitwise.BitXOrFunction)


def test_bitxor_num_args():
    with pytest.raises(InvalidNumberOfArguments):
        Function.parse(None, 'BITXOR(1)', 0)

    with pytest.raises(InvalidNumberOfArguments):
        Function.parse(None, 'BITXOR(1, 2, 3)', 0)


async def test_shl_simple(literal_three, literal_ten):
    result = await bitwise.SHLFunction([literal_three, literal_ten]).eval()
    assert result == 3072


def test_shl_parse():
    e = Function.parse(None, 'SHL(1, 2)', 0)
    assert isinstance(e, bitwise.SHLFunction)


def test_shl_num_args():
    with pytest.raises(InvalidNumberOfArguments):
        Function.parse(None, 'SHL(1)', 0)

    with pytest.raises(InvalidNumberOfArguments):
        Function.parse(None, 'SHL(1, 2, 3)', 0)


async def test_shr_simple(literal_three, literal_ten):
    result = await bitwise.SHRFunction([literal_ten, literal_three]).eval()
    assert result == 1


def test_shr_parse():
    e = Function.parse(None, 'SHR(1, 2)', 0)
    assert isinstance(e, bitwise.SHRFunction)


def test_shr_num_args():
    with pytest.raises(InvalidNumberOfArguments):
        Function.parse(None, 'SHR(1)', 0)

    with pytest.raises(InvalidNumberOfArguments):
        Function.parse(None, 'SHR(1, 2, 3)', 0)
