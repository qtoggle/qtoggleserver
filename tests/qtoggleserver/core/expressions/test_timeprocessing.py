
import datetime

import pytest

from qtoggleserver.core.expressions import timeprocessing, Function
from qtoggleserver.core.expressions import InvalidNumberOfArguments, EvalSkipped

from .mock import MockExpression


def test_delay(freezer, dummy_local_datetime, literal_one_thousand):
    freezer.move_to(dummy_local_datetime)
    value_expr = MockExpression(3)
    expr = timeprocessing.DelayFunction([value_expr, literal_one_thousand])
    assert expr.eval() == 3

    freezer.move_to(dummy_local_datetime + datetime.timedelta(milliseconds=100))
    assert expr.eval() == 3

    value_expr.set_value(16)
    freezer.move_to(dummy_local_datetime + datetime.timedelta(milliseconds=500))
    assert expr.eval() == 3

    freezer.move_to(dummy_local_datetime + datetime.timedelta(milliseconds=1499))
    assert expr.eval() == 3

    freezer.move_to(dummy_local_datetime + datetime.timedelta(milliseconds=1501))
    assert expr.eval() == 16

    freezer.move_to(dummy_local_datetime + datetime.timedelta(milliseconds=10000))
    assert expr.eval() == 16


def test_delay_parse():
    e = Function.parse(None, 'DELAY(1, 2)', 0)
    assert isinstance(e, timeprocessing.DelayFunction)


def test_delay_num_args():
    with pytest.raises(InvalidNumberOfArguments):
        Function.parse(None, 'DELAY(1)', 0)

    with pytest.raises(InvalidNumberOfArguments):
        Function.parse(None, 'DELAY(1, 2, 3)', 0)


def test_sample(freezer, dummy_local_datetime, literal_one_thousand):
    freezer.move_to(dummy_local_datetime)
    value_expr = MockExpression(3)
    expr = timeprocessing.SampleFunction([value_expr, literal_one_thousand])
    assert expr.eval() == 3

    freezer.move_to(dummy_local_datetime + datetime.timedelta(milliseconds=100))
    value_expr.set_value(16)
    assert expr.eval() == 3

    freezer.move_to(dummy_local_datetime + datetime.timedelta(milliseconds=500))
    assert expr.eval() == 3

    freezer.move_to(dummy_local_datetime + datetime.timedelta(milliseconds=999))
    assert expr.eval() == 3

    freezer.move_to(dummy_local_datetime + datetime.timedelta(milliseconds=1001))
    assert expr.eval() == 16

    freezer.move_to(dummy_local_datetime + datetime.timedelta(milliseconds=10000))
    assert expr.eval() == 16


def test_sample_parse():
    e = Function.parse(None, 'SAMPLE(1, 2)', 0)
    assert isinstance(e, timeprocessing.SampleFunction)


def test_sample_num_args():
    with pytest.raises(InvalidNumberOfArguments):
        Function.parse(None, 'SAMPLE(1)', 0)

    with pytest.raises(InvalidNumberOfArguments):
        Function.parse(None, 'SAMPLE(1, 2, 3)', 0)


def test_freeze(freezer, dummy_local_datetime):
    freezer.move_to(dummy_local_datetime)
    value_expr = MockExpression(1)
    time_expr = MockExpression(200)
    expr = timeprocessing.FreezeFunction([value_expr, time_expr])
    assert expr.eval() == 1
    time_expr.set_value(50)

    freezer.move_to(dummy_local_datetime + datetime.timedelta(milliseconds=100))
    value_expr.set_value(2)
    assert expr.eval() == 1

    freezer.move_to(dummy_local_datetime + datetime.timedelta(milliseconds=199))
    assert expr.eval() == 1

    freezer.move_to(dummy_local_datetime + datetime.timedelta(milliseconds=201))
    time_expr.set_value(200)
    assert expr.eval() == 2

    freezer.move_to(dummy_local_datetime + datetime.timedelta(milliseconds=500))
    value_expr.set_value(3)
    assert expr.eval() == 3

    freezer.move_to(dummy_local_datetime + datetime.timedelta(milliseconds=600))
    value_expr.set_value(4)
    assert expr.eval() == 3

    freezer.move_to(dummy_local_datetime + datetime.timedelta(milliseconds=699))
    assert expr.eval() == 3

    freezer.move_to(dummy_local_datetime + datetime.timedelta(milliseconds=701))
    assert expr.eval() == 4


def test_freeze_parse():
    e = Function.parse(None, 'FREEZE(1, 2)', 0)
    assert isinstance(e, timeprocessing.FreezeFunction)


def test_freeze_num_args():
    with pytest.raises(InvalidNumberOfArguments):
        Function.parse(None, 'FREEZE(1)', 0)

    with pytest.raises(InvalidNumberOfArguments):
        Function.parse(None, 'FREEZE(1, 2, 3)', 0)


def test_held_fulfilled(freezer, dummy_local_datetime, literal_sixteen):
    freezer.move_to(dummy_local_datetime)
    value_expr = MockExpression(16)
    time_expr = MockExpression(200)
    expr = timeprocessing.HeldFunction([value_expr, literal_sixteen, time_expr])
    assert expr.eval() == 0
    time_expr.set_value(500)

    freezer.move_to(dummy_local_datetime + datetime.timedelta(milliseconds=499))
    assert expr.eval() == 0

    freezer.move_to(dummy_local_datetime + datetime.timedelta(milliseconds=501))
    assert expr.eval() == 1


def test_held_not_fulfilled(freezer, dummy_local_datetime, literal_sixteen):
    freezer.move_to(dummy_local_datetime)
    value_expr = MockExpression(16)
    time_expr = MockExpression(200)
    expr = timeprocessing.HeldFunction([value_expr, literal_sixteen, time_expr])
    assert expr.eval() == 0

    freezer.move_to(dummy_local_datetime + datetime.timedelta(milliseconds=100))
    value_expr.set_value(15)
    assert expr.eval() == 0

    freezer.move_to(dummy_local_datetime + datetime.timedelta(milliseconds=201))
    assert expr.eval() == 0


def test_held_different_value(freezer, dummy_local_datetime, literal_sixteen):
    freezer.move_to(dummy_local_datetime)
    value_expr = MockExpression(15)
    time_expr = MockExpression(200)
    expr = timeprocessing.HeldFunction([value_expr, literal_sixteen, time_expr])
    assert expr.eval() == 0

    freezer.move_to(dummy_local_datetime + datetime.timedelta(milliseconds=501))
    assert expr.eval() == 0


def test_held_parse():
    e = Function.parse(None, 'HELD(1, 2, 3)', 0)
    assert isinstance(e, timeprocessing.HeldFunction)


def test_held_num_args():
    with pytest.raises(InvalidNumberOfArguments):
        Function.parse(None, 'HELD(1, 2)', 0)

    with pytest.raises(InvalidNumberOfArguments):
        Function.parse(None, 'HELD(1, 2, 3, 4)', 0)


def test_deriv(freezer, dummy_local_datetime):
    freezer.move_to(dummy_local_datetime)
    value_expr = MockExpression(0)
    time_expr = MockExpression(100)
    expr = timeprocessing.DerivFunction([value_expr, time_expr])
    assert round(expr.eval(), 1) == 0

    freezer.move_to(dummy_local_datetime + datetime.timedelta(milliseconds=200))
    value_expr.set_value(1)
    assert round(expr.eval(), 1) == 5

    freezer.move_to(dummy_local_datetime + datetime.timedelta(milliseconds=300))
    with pytest.raises(EvalSkipped):
        expr.eval()

    freezer.move_to(dummy_local_datetime + datetime.timedelta(milliseconds=400))
    value_expr.set_value(2)
    assert round(expr.eval(), 1) == 5

    freezer.move_to(dummy_local_datetime + datetime.timedelta(milliseconds=800))
    value_expr.set_value(5)
    time_expr.set_value(200)
    assert round(expr.eval(), 1) == 7.5

    freezer.move_to(dummy_local_datetime + datetime.timedelta(milliseconds=1000))
    value_expr.set_value(1)
    time_expr.set_value(100)
    assert round(expr.eval(), 1) == -20

    freezer.move_to(dummy_local_datetime + datetime.timedelta(milliseconds=1200))
    assert round(expr.eval(), 1) == 0


def test_deriv_parse():
    e = Function.parse(None, 'DERIV(1, 2)', 0)
    assert isinstance(e, timeprocessing.DerivFunction)


def test_deriv_num_args():
    with pytest.raises(InvalidNumberOfArguments):
        Function.parse(None, 'DERIV(1)', 0)

    with pytest.raises(InvalidNumberOfArguments):
        Function.parse(None, 'DERIV(1, 2, 3)', 0)


def test_integ(freezer, dummy_local_datetime):
    freezer.move_to(dummy_local_datetime)
    acc_expr = MockExpression(0)
    value_expr = MockExpression(0)
    time_expr = MockExpression(100)
    expr = timeprocessing.IntegFunction([value_expr, acc_expr, time_expr])
    assert round(expr.eval(), 1) == 0

    freezer.move_to(dummy_local_datetime + datetime.timedelta(milliseconds=200))
    value_expr.set_value(10)
    assert round(expr.eval(), 1) == 1

    freezer.move_to(dummy_local_datetime + datetime.timedelta(milliseconds=300))
    with pytest.raises(EvalSkipped):
        expr.eval()

    freezer.move_to(dummy_local_datetime + datetime.timedelta(milliseconds=400))
    acc_expr.set_value(1)
    assert round(expr.eval(), 1) == 3

    freezer.move_to(dummy_local_datetime + datetime.timedelta(milliseconds=800))
    value_expr.set_value(15)
    acc_expr.set_value(3)
    time_expr.set_value(200)
    assert round(expr.eval(), 1) == 8

    freezer.move_to(dummy_local_datetime + datetime.timedelta(milliseconds=1000))
    value_expr.set_value(-20)
    acc_expr.set_value(8)
    time_expr.set_value(100)
    assert round(expr.eval(), 1) == 7.5

    freezer.move_to(dummy_local_datetime + datetime.timedelta(milliseconds=1200))
    value_expr.set_value(0)
    acc_expr.set_value(7.5)
    assert round(expr.eval(), 1) == 5.5


def test_integ_parse():
    e = Function.parse(None, 'INTEG(1, 2, 3)', 0)
    assert isinstance(e, timeprocessing.IntegFunction)


def test_integ_num_args():
    with pytest.raises(InvalidNumberOfArguments):
        Function.parse(None, 'INTEG(1, 2)', 0)

    with pytest.raises(InvalidNumberOfArguments):
        Function.parse(None, 'INTEG(1, 2, 3, 4)', 0)


def test_fmavg(freezer, dummy_local_datetime):
    freezer.move_to(dummy_local_datetime)
    value_expr = MockExpression(0)
    width_expr = MockExpression(4)
    time_expr = MockExpression(100)
    expr = timeprocessing.FMAvgFunction([value_expr, width_expr, time_expr])
    assert expr.eval() == 0

    freezer.move_to(dummy_local_datetime + datetime.timedelta(milliseconds=101))
    value_expr.set_value(8)
    assert expr.eval() == 4

    freezer.move_to(dummy_local_datetime + datetime.timedelta(milliseconds=200))
    value_expr.set_value(4)
    with pytest.raises(EvalSkipped):
        expr.eval()

    freezer.move_to(dummy_local_datetime + datetime.timedelta(milliseconds=202))
    assert expr.eval() == 4

    freezer.move_to(dummy_local_datetime + datetime.timedelta(milliseconds=301))
    value_expr.set_value(-2)
    with pytest.raises(EvalSkipped):
        expr.eval()

    freezer.move_to(dummy_local_datetime + datetime.timedelta(milliseconds=303))
    assert expr.eval() == 2.5

    freezer.move_to(dummy_local_datetime + datetime.timedelta(milliseconds=402))
    value_expr.set_value(6)
    with pytest.raises(EvalSkipped):
        expr.eval()

    freezer.move_to(dummy_local_datetime + datetime.timedelta(milliseconds=504))
    assert expr.eval() == 4

    freezer.move_to(dummy_local_datetime + datetime.timedelta(milliseconds=603))
    value_expr.set_value(11)
    width_expr.set_value(3)
    with pytest.raises(EvalSkipped):
        expr.eval()

    freezer.move_to(dummy_local_datetime + datetime.timedelta(milliseconds=605))
    assert expr.eval() == 5

    freezer.move_to(dummy_local_datetime + datetime.timedelta(milliseconds=804))
    value_expr.set_value(-8)
    time_expr.set_value(200)
    with pytest.raises(EvalSkipped):
        expr.eval()

    freezer.move_to(dummy_local_datetime + datetime.timedelta(milliseconds=806))
    assert expr.eval() == 3


def test_fmavg_parse():
    e = Function.parse(None, 'FMAVG(1, 2, 3)', 0)
    assert isinstance(e, timeprocessing.FMAvgFunction)


def test_fmavg_num_args():
    with pytest.raises(InvalidNumberOfArguments):
        Function.parse(None, 'FMAVG(1, 2)', 0)

    with pytest.raises(InvalidNumberOfArguments):
        Function.parse(None, 'FMAVG(1, 2, 3, 4)', 0)


def test_fmedian(freezer, dummy_local_datetime):
    freezer.move_to(dummy_local_datetime)
    value_expr = MockExpression(0)
    width_expr = MockExpression(4)
    time_expr = MockExpression(100)
    expr = timeprocessing.FMedianFunction([value_expr, width_expr, time_expr])
    assert expr.eval() == 0

    freezer.move_to(dummy_local_datetime + datetime.timedelta(milliseconds=101))
    value_expr.set_value(8)
    assert expr.eval() == 8

    freezer.move_to(dummy_local_datetime + datetime.timedelta(milliseconds=200))
    value_expr.set_value(4)
    with pytest.raises(EvalSkipped):
        expr.eval()

    freezer.move_to(dummy_local_datetime + datetime.timedelta(milliseconds=202))
    assert expr.eval() == 4

    freezer.move_to(dummy_local_datetime + datetime.timedelta(milliseconds=301))
    value_expr.set_value(-2)
    with pytest.raises(EvalSkipped):
        expr.eval()

    freezer.move_to(dummy_local_datetime + datetime.timedelta(milliseconds=303))
    assert expr.eval() == 4

    freezer.move_to(dummy_local_datetime + datetime.timedelta(milliseconds=402))
    value_expr.set_value(6)
    with pytest.raises(EvalSkipped):
        expr.eval()

    freezer.move_to(dummy_local_datetime + datetime.timedelta(milliseconds=504))
    assert expr.eval() == 6

    freezer.move_to(dummy_local_datetime + datetime.timedelta(milliseconds=603))
    value_expr.set_value(11)
    width_expr.set_value(3)
    with pytest.raises(EvalSkipped):
        expr.eval()

    freezer.move_to(dummy_local_datetime + datetime.timedelta(milliseconds=605))
    assert expr.eval() == 6

    freezer.move_to(dummy_local_datetime + datetime.timedelta(milliseconds=804))
    value_expr.set_value(-8)
    time_expr.set_value(200)
    with pytest.raises(EvalSkipped):
        expr.eval()

    freezer.move_to(dummy_local_datetime + datetime.timedelta(milliseconds=806))
    assert expr.eval() == 6


def test_fmedian_parse():
    e = Function.parse(None, 'FMEDIAN(1, 2, 3)', 0)
    assert isinstance(e, timeprocessing.FMedianFunction)


def test_fmedian_num_args():
    with pytest.raises(InvalidNumberOfArguments):
        Function.parse(None, 'FMEDIAN(1, 2)', 0)

    with pytest.raises(InvalidNumberOfArguments):
        Function.parse(None, 'FMEDIAN(1, 2, 3, 4)', 0)
