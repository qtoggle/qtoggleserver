
import datetime
import pytest

from qtoggleserver.core.expressions import various, Function
from qtoggleserver.core.expressions import InvalidNumberOfArguments

from .mock import MockExpression


def test_acc():
    value_expr = MockExpression(16)
    acc_expr = MockExpression(13)
    expr = various.AccFunction([value_expr, acc_expr])
    assert expr.eval() == 13

    acc_expr.set_value(-5)
    assert expr.eval() == -5

    value_expr.set_value(26)
    assert expr.eval() == 5

    value_expr.set_value(20)
    acc_expr.set_value(5)
    assert expr.eval() == -1


def test_acc_parse():
    e = Function.parse(None, 'ACC(1, 2)', 0)
    assert isinstance(e, various.AccFunction)


def test_acc_num_args():
    with pytest.raises(InvalidNumberOfArguments):
        Function.parse(None, 'ACC(1)', 0)

    with pytest.raises(InvalidNumberOfArguments):
        Function.parse(None, 'ACC(1, 2, 3)', 0)


def test_accinc():
    value_expr = MockExpression(16)
    acc_expr = MockExpression(13)
    expr = various.AccIncFunction([value_expr, acc_expr])
    assert expr.eval() == 13

    acc_expr.set_value(-5)
    assert expr.eval() == -5

    value_expr.set_value(26)
    assert expr.eval() == 5

    value_expr.set_value(20)
    acc_expr.set_value(5)
    assert expr.eval() == 5


def test_accinc_parse():
    e = Function.parse(None, 'ACCINC(1, 2)', 0)
    assert isinstance(e, various.AccIncFunction)


def test_accinc_num_args():
    with pytest.raises(InvalidNumberOfArguments):
        Function.parse(None, 'ACCINC(1)', 0)

    with pytest.raises(InvalidNumberOfArguments):
        Function.parse(None, 'ACCINC(1, 2, 3)', 0)


def test_hyst_rise(literal_three, literal_sixteen):
    value_expr = MockExpression(1)
    expr = various.HystFunction([value_expr, literal_three, literal_sixteen])
    assert expr.eval() == 0

    value_expr.set_value(2)
    assert expr.eval() == 0

    value_expr.set_value(3)
    assert expr.eval() == 0

    value_expr.set_value(4)
    assert expr.eval() == 0

    value_expr.set_value(16)
    assert expr.eval() == 0

    value_expr.set_value(10)
    assert expr.eval() == 0

    value_expr.set_value(2)
    assert expr.eval() == 0

    value_expr.set_value(17)
    assert expr.eval() == 1

    value_expr.set_value(20)
    assert expr.eval() == 1


def test_hyst_fall(literal_three, literal_sixteen):
    value_expr = MockExpression(20)
    expr = various.HystFunction([value_expr, literal_three, literal_sixteen])
    assert expr.eval() == 1

    value_expr.set_value(17)
    assert expr.eval() == 1

    value_expr.set_value(16)
    assert expr.eval() == 1

    value_expr.set_value(10)
    assert expr.eval() == 1

    value_expr.set_value(4)
    assert expr.eval() == 1

    value_expr.set_value(20)
    assert expr.eval() == 1

    value_expr.set_value(3)
    assert expr.eval() == 1

    value_expr.set_value(2)
    assert expr.eval() == 0

    value_expr.set_value(0)
    assert expr.eval() == 0


def test_hyst_parse():
    e = Function.parse(None, 'HYST(1, 2, 3)', 0)
    assert isinstance(e, various.HystFunction)


def test_hyst_num_args():
    with pytest.raises(InvalidNumberOfArguments):
        Function.parse(None, 'HYST(1, 2)', 0)

    with pytest.raises(InvalidNumberOfArguments):
        Function.parse(None, 'HYST(1, 2, 3, 4)', 0)


def test_sequence(
    freezer,
    dummy_local_datetime,
    literal_two,
    literal_three,
    literal_sixteen,
    literal_one_hundred,
    literal_two_hundreds
):
    freezer.move_to(dummy_local_datetime)
    expr = various.SequenceFunction([
        literal_three,
        literal_one_hundred,
        literal_sixteen,
        literal_two_hundreds,
        literal_two,
        literal_one_hundred
    ])
    assert expr.eval() == 3

    freezer.move_to(dummy_local_datetime + datetime.timedelta(milliseconds=99))
    assert expr.eval() == 3

    freezer.move_to(dummy_local_datetime + datetime.timedelta(milliseconds=101))
    assert expr.eval() == 16

    freezer.move_to(dummy_local_datetime + datetime.timedelta(milliseconds=200))
    assert expr.eval() == 16

    freezer.move_to(dummy_local_datetime + datetime.timedelta(milliseconds=299))
    assert expr.eval() == 16

    freezer.move_to(dummy_local_datetime + datetime.timedelta(milliseconds=301))
    assert expr.eval() == 2

    freezer.move_to(dummy_local_datetime + datetime.timedelta(milliseconds=399))
    assert expr.eval() == 2

    freezer.move_to(dummy_local_datetime + datetime.timedelta(milliseconds=401))
    assert expr.eval() == 3


def test_sequence_parse():
    e = Function.parse(None, 'SEQUENCE(1, 2, 3, 4)', 0)
    assert isinstance(e, various.SequenceFunction)


def test_sequence_num_args():
    with pytest.raises(InvalidNumberOfArguments):
        Function.parse(None, 'SEQUENCE(1)', 0)


def test_lut(
    freezer,
    literal_two,
    literal_three,
    literal_sixteen,
    literal_one_hundred,
    literal_two_hundreds,
    literal_one_thousand
):
    value_expr = MockExpression(0)
    expr = various.LUTFunction([
        value_expr,
        literal_three,
        literal_two_hundreds,
        literal_sixteen,
        literal_one_thousand,
        literal_two,
        literal_one_hundred
    ])
    assert expr.eval() == 100

    value_expr.set_value(2)
    assert expr.eval() == 100

    value_expr.set_value(2.4)
    assert expr.eval() == 100

    value_expr.set_value(2.6)
    assert expr.eval() == 200

    value_expr.set_value(3)
    assert expr.eval() == 200

    value_expr.set_value(5)
    assert expr.eval() == 200

    value_expr.set_value(9.4)
    assert expr.eval() == 200

    value_expr.set_value(9.6)
    assert expr.eval() == 1000

    value_expr.set_value(100)
    assert expr.eval() == 1000


def test_lut_parse():
    e = Function.parse(None, 'LUT(1, 2, 3, 4, 5)', 0)
    assert isinstance(e, various.LUTFunction)


def test_lut_num_args():
    with pytest.raises(InvalidNumberOfArguments):
        Function.parse(None, 'LUT(1)', 0)

    with pytest.raises(InvalidNumberOfArguments):
        Function.parse(None, 'LUT(1, 2)', 0)

    with pytest.raises(InvalidNumberOfArguments):
        Function.parse(None, 'LUT(1, 2, 3, 4)', 0)


def test_lutli(
    freezer,
    literal_two,
    literal_three,
    literal_sixteen,
    literal_one_hundred,
    literal_two_hundreds,
    literal_one_thousand
):
    value_expr = MockExpression(0)
    expr = various.LUTLIFunction([
        value_expr,
        literal_three,
        literal_two_hundreds,
        literal_sixteen,
        literal_one_thousand,
        literal_two,
        literal_one_hundred
    ])
    assert expr.eval() == 100

    value_expr.set_value(2)
    assert expr.eval() == 100

    value_expr.set_value(2.4)
    assert expr.eval() == 140

    value_expr.set_value(2.6)
    assert expr.eval() == 160

    value_expr.set_value(3)
    assert expr.eval() == 200

    value_expr.set_value(5)
    assert round(expr.eval(), 2) == 323.08

    value_expr.set_value(9.4)
    assert round(expr.eval(), 2) == 593.85

    value_expr.set_value(9.6)
    assert round(expr.eval(), 2) == 606.15

    value_expr.set_value(16)
    assert round(expr.eval(), 2) == 1000

    value_expr.set_value(100)
    assert round(expr.eval(), 2) == 1000


def test_lutli_parse():
    e = Function.parse(None, 'LUTLI(1, 2, 3, 4, 5)', 0)
    assert isinstance(e, various.LUTLIFunction)


def test_lutli_num_args():
    with pytest.raises(InvalidNumberOfArguments):
        Function.parse(None, 'LUTLI(1)', 0)

    with pytest.raises(InvalidNumberOfArguments):
        Function.parse(None, 'LUTLI(1, 2)', 0)

    with pytest.raises(InvalidNumberOfArguments):
        Function.parse(None, 'LUTLI(1, 2, 3, 4)', 0)
