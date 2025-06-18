import pytest

from qtoggleserver.core.expressions import ROLE_VALUE, Function, arithmetic
from qtoggleserver.core.expressions.exceptions import ExpressionArithmeticError, InvalidNumberOfArguments


async def test_add_simple(literal_one, literal_two, dummy_eval_context):
    result = await arithmetic.AddFunction([literal_one, literal_two], role=ROLE_VALUE).eval(context=dummy_eval_context)
    assert result == 3


async def test_add_multiple(literal_one, literal_two, literal_minus_one, literal_ten, dummy_eval_context):
    expr = arithmetic.AddFunction([literal_one, literal_two, literal_minus_one, literal_ten], role=ROLE_VALUE)
    result = await expr.eval(context=dummy_eval_context)
    assert result == 12


async def test_add_boolean(literal_one, literal_true, dummy_eval_context):
    result = await arithmetic.AddFunction([literal_one, literal_true], role=ROLE_VALUE).eval(context=dummy_eval_context)
    assert result == 2


def test_add_parse():
    e = Function.parse(None, "ADD(1, 2)", ROLE_VALUE, 0)
    assert isinstance(e, arithmetic.AddFunction)


def test_add_num_args():
    with pytest.raises(InvalidNumberOfArguments):
        Function.parse(None, "ADD(1)", ROLE_VALUE, 0)


async def test_sub_simple(literal_one, literal_two, dummy_eval_context):
    result = await arithmetic.SubFunction([literal_one, literal_two], role=ROLE_VALUE).eval(context=dummy_eval_context)
    assert result == -1


async def test_sub_boolean(literal_two, literal_true, dummy_eval_context):
    result = await arithmetic.SubFunction([literal_two, literal_true], role=ROLE_VALUE).eval(context=dummy_eval_context)
    assert result == 1


def test_sub_parse():
    e = Function.parse(None, "SUB(1, 2)", ROLE_VALUE, 0)
    assert isinstance(e, arithmetic.SubFunction)


def test_sub_num_args():
    with pytest.raises(InvalidNumberOfArguments):
        Function.parse(None, "SUB(1)", ROLE_VALUE, 0)

    with pytest.raises(InvalidNumberOfArguments):
        Function.parse(None, "SUB(1, 2, 3)", ROLE_VALUE, 0)


async def test_mul_simple(literal_two, literal_ten, dummy_eval_context):
    result = await arithmetic.MulFunction([literal_two, literal_ten], role=ROLE_VALUE).eval(context=dummy_eval_context)
    assert result == 20


async def test_mul_multiple(literal_two, literal_ten, literal_minus_one, dummy_eval_context):
    expr = arithmetic.MulFunction([literal_two, literal_ten, literal_minus_one], role=ROLE_VALUE)
    result = await expr.eval(context=dummy_eval_context)
    assert result == -20


async def test_mul_boolean(literal_two, literal_true, dummy_eval_context):
    result = await arithmetic.MulFunction([literal_two, literal_true], role=ROLE_VALUE).eval(context=dummy_eval_context)
    assert result == 2


def test_mul_parse():
    e = Function.parse(None, "MUL(1, 2)", ROLE_VALUE, 0)
    assert isinstance(e, arithmetic.MulFunction)


def test_mul_num_args():
    with pytest.raises(InvalidNumberOfArguments):
        Function.parse(None, "MUL(1)", ROLE_VALUE, 0)


async def test_div_integer(literal_ten, literal_two, dummy_eval_context):
    result = await arithmetic.DivFunction([literal_ten, literal_two], role=ROLE_VALUE).eval(context=dummy_eval_context)
    assert result == 5


async def test_div_float(literal_two, literal_ten, dummy_eval_context):
    result = await arithmetic.DivFunction([literal_two, literal_ten], role=ROLE_VALUE).eval(context=dummy_eval_context)
    assert result == 0.2


async def test_div_boolean(literal_ten, literal_true, literal_false, dummy_eval_context):
    result = await arithmetic.DivFunction([literal_ten, literal_true], role=ROLE_VALUE).eval(context=dummy_eval_context)
    assert result == 10

    with pytest.raises(ExpressionArithmeticError):
        await arithmetic.DivFunction([literal_ten, literal_false], role=ROLE_VALUE).eval(context=dummy_eval_context)


def test_div_parse():
    e = Function.parse(None, "DIV(1, 2)", ROLE_VALUE, 0)
    assert isinstance(e, arithmetic.DivFunction)


def test_div_num_args():
    with pytest.raises(InvalidNumberOfArguments):
        Function.parse(None, "DIV(1)", ROLE_VALUE, 0)

    with pytest.raises(InvalidNumberOfArguments):
        Function.parse(None, "DIV(1, 2, 3)", ROLE_VALUE, 0)


async def test_mod_integer(literal_ten, literal_two, dummy_eval_context):
    result = await arithmetic.ModFunction([literal_ten, literal_two], role=ROLE_VALUE).eval(context=dummy_eval_context)
    assert result == 0


async def test_mod_float(literal_three, literal_two, dummy_eval_context):
    result = await arithmetic.ModFunction([literal_three, literal_two], role=ROLE_VALUE).eval(
        context=dummy_eval_context
    )
    assert result == 1


async def test_mod_boolean(literal_ten, literal_true, literal_false, dummy_eval_context):
    result = await arithmetic.ModFunction([literal_ten, literal_true], role=ROLE_VALUE).eval(context=dummy_eval_context)
    assert result == 0

    with pytest.raises(ExpressionArithmeticError):
        await arithmetic.ModFunction([literal_ten, literal_false], role=ROLE_VALUE).eval(context=dummy_eval_context)


def test_mod_parse():
    e = Function.parse(None, "MOD(1, 2)", ROLE_VALUE, 0)
    assert isinstance(e, arithmetic.ModFunction)


def test_mod_num_args():
    with pytest.raises(InvalidNumberOfArguments):
        Function.parse(None, "MOD(1)", ROLE_VALUE, 0)

    with pytest.raises(InvalidNumberOfArguments):
        Function.parse(None, "MOD(1, 2, 3)", ROLE_VALUE, 0)


async def test_pow_integer(literal_ten, literal_two, dummy_eval_context):
    result = await arithmetic.PowFunction([literal_ten, literal_two], role=ROLE_VALUE).eval(context=dummy_eval_context)
    assert result == 100


async def test_pow_sqrt(literal_sixteen, literal_zero_point_five, dummy_eval_context):
    result = await arithmetic.PowFunction([literal_sixteen, literal_zero_point_five], role=ROLE_VALUE).eval(
        context=dummy_eval_context
    )
    assert result == 4


async def test_pow_boolean(literal_ten, literal_true, literal_false, dummy_eval_context):
    result = await arithmetic.PowFunction([literal_ten, literal_true], role=ROLE_VALUE).eval(context=dummy_eval_context)
    assert result == 10

    result = await arithmetic.PowFunction([literal_ten, literal_false], role=ROLE_VALUE).eval(
        context=dummy_eval_context
    )
    assert result == 1


def test_pow_parse():
    e = Function.parse(None, "POW(1, 2)", ROLE_VALUE, 0)
    assert isinstance(e, arithmetic.PowFunction)


def test_pow_num_args():
    with pytest.raises(InvalidNumberOfArguments):
        Function.parse(None, "POW(1)", ROLE_VALUE, 0)

    with pytest.raises(InvalidNumberOfArguments):
        Function.parse(None, "POW(1, 2, 3)", ROLE_VALUE, 0)
