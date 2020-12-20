
import pytest

from qtoggleserver.core.expressions import arithmetic, Function
from qtoggleserver.core.expressions import InvalidNumberOfArguments, ExpressionArithmeticError


def test_add_simple(literal_one, literal_two):
    result = arithmetic.AddFunction([literal_one, literal_two]).eval()
    assert result == 3


def test_add_multiple(literal_one, literal_two, literal_minus_one, literal_ten):
    result = arithmetic.AddFunction([literal_one, literal_two, literal_minus_one, literal_ten]).eval()
    assert result == 12


def test_add_boolean(literal_one, literal_true):
    result = arithmetic.AddFunction([literal_one, literal_true]).eval()
    assert result == 2


def test_add_parse():
    e = Function.parse(None, 'ADD(1, 2)', 0)
    assert isinstance(e, arithmetic.AddFunction)


def test_add_num_args():
    with pytest.raises(InvalidNumberOfArguments):
        Function.parse(None, 'ADD(1)', 0)


def test_sub_simple(literal_one, literal_two):
    result = arithmetic.SubFunction([literal_one, literal_two]).eval()
    assert result == -1


def test_sub_boolean(literal_two, literal_true):
    result = arithmetic.SubFunction([literal_two, literal_true]).eval()
    assert result == 1


def test_sub_parse():
    e = Function.parse(None, 'SUB(1, 2)', 0)
    assert isinstance(e, arithmetic.SubFunction)


def test_sub_num_args():
    with pytest.raises(InvalidNumberOfArguments):
        Function.parse(None, 'SUB(1)', 0)

    with pytest.raises(InvalidNumberOfArguments):
        Function.parse(None, 'SUB(1, 2, 3)', 0)


def test_mul_simple(literal_two, literal_ten):
    result = arithmetic.MulFunction([literal_two, literal_ten]).eval()
    assert result == 20


def test_mul_multiple(literal_two, literal_ten, literal_minus_one):
    result = arithmetic.MulFunction([literal_two, literal_ten, literal_minus_one]).eval()
    assert result == -20


def test_mul_boolean(literal_two, literal_true):
    result = arithmetic.MulFunction([literal_two, literal_true]).eval()
    assert result == 2


def test_mul_parse():
    e = Function.parse(None, 'MUL(1, 2)', 0)
    assert isinstance(e, arithmetic.MulFunction)


def test_mul_num_args():
    with pytest.raises(InvalidNumberOfArguments):
        Function.parse(None, 'MUL(1)', 0)


def test_div_integer(literal_ten, literal_two):
    result = arithmetic.DivFunction([literal_ten, literal_two]).eval()
    assert result == 5


def test_div_float(literal_two, literal_ten):
    result = arithmetic.DivFunction([literal_two, literal_ten]).eval()
    assert result == 0.2


def test_div_boolean(literal_ten, literal_true, literal_false):
    result = arithmetic.DivFunction([literal_ten, literal_true]).eval()
    assert result == 10

    with pytest.raises(ExpressionArithmeticError):
        arithmetic.DivFunction([literal_ten, literal_false]).eval()


def test_div_parse():
    e = Function.parse(None, 'DIV(1, 2)', 0)
    assert isinstance(e, arithmetic.DivFunction)


def test_div_num_args():
    with pytest.raises(InvalidNumberOfArguments):
        Function.parse(None, 'DIV(1)', 0)

    with pytest.raises(InvalidNumberOfArguments):
        Function.parse(None, 'DIV(1, 2, 3)', 0)


def test_mod_integer(literal_ten, literal_two):
    result = arithmetic.ModFunction([literal_ten, literal_two]).eval()
    assert result == 0


def test_mod_float(literal_three, literal_two):
    result = arithmetic.ModFunction([literal_three, literal_two]).eval()
    assert result == 1


def test_mod_boolean(literal_ten, literal_true, literal_false):
    result = arithmetic.ModFunction([literal_ten, literal_true]).eval()
    assert result == 0

    with pytest.raises(ExpressionArithmeticError):
        arithmetic.ModFunction([literal_ten, literal_false]).eval()


def test_mod_parse():
    e = Function.parse(None, 'MOD(1, 2)', 0)
    assert isinstance(e, arithmetic.ModFunction)


def test_mod_num_args():
    with pytest.raises(InvalidNumberOfArguments):
        Function.parse(None, 'MOD(1)', 0)

    with pytest.raises(InvalidNumberOfArguments):
        Function.parse(None, 'MOD(1, 2, 3)', 0)


def test_pow_integer(literal_ten, literal_two):
    result = arithmetic.PowFunction([literal_ten, literal_two]).eval()
    assert result == 100


def test_pow_sqrt(literal_sixteen, literal_zero_point_five):
    result = arithmetic.PowFunction([literal_sixteen, literal_zero_point_five]).eval()
    assert result == 4


def test_pow_boolean(literal_ten, literal_true, literal_false):
    result = arithmetic.PowFunction([literal_ten, literal_true]).eval()
    assert result == 10

    result = arithmetic.PowFunction([literal_ten, literal_false]).eval()
    assert result == 1


def test_pow_parse():
    e = Function.parse(None, 'POW(1, 2)', 0)
    assert isinstance(e, arithmetic.PowFunction)


def test_pow_num_args():
    with pytest.raises(InvalidNumberOfArguments):
        Function.parse(None, 'POW(1)', 0)

    with pytest.raises(InvalidNumberOfArguments):
        Function.parse(None, 'POW(1, 2, 3)', 0)
