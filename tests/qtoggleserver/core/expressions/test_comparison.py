
import pytest

from qtoggleserver.core.expressions import comparison, Function
from qtoggleserver.core.expressions import InvalidNumberOfArguments


def test_if_boolean(literal_false, literal_true, literal_one, literal_two):
    result = comparison.IfFunction([literal_false, literal_one, literal_two]).eval()
    assert result == 2

    result = comparison.IfFunction([literal_true, literal_one, literal_two]).eval()
    assert result == 1


def test_if_number(literal_zero, literal_one, literal_two):
    result = comparison.IfFunction([literal_zero, literal_one, literal_two]).eval()
    assert result == 2

    result = comparison.IfFunction([literal_two, literal_one, literal_two]).eval()
    assert result == 1


def test_if_parse():
    e = Function.parse(None, 'IF(1, 2, 3)', 0)
    assert isinstance(e, comparison.IfFunction)


def test_if_num_args():
    with pytest.raises(InvalidNumberOfArguments):
        Function.parse(None, 'IF(1, 2)', 0)

    with pytest.raises(InvalidNumberOfArguments):
        Function.parse(None, 'IF(1, 2, 3, 4)', 0)


def test_eq_boolean(literal_false, literal_true):
    result = comparison.EqFunction([literal_false, literal_true]).eval()
    assert result == 0

    result = comparison.EqFunction([literal_false, literal_false]).eval()
    assert result == 1


def test_eq_number(literal_one, literal_two):
    result = comparison.EqFunction([literal_one, literal_two]).eval()
    assert result == 0

    result = comparison.EqFunction([literal_two, literal_two]).eval()
    assert result == 1


def test_eq_parse():
    e = Function.parse(None, 'EQ(1, 2)', 0)
    assert isinstance(e, comparison.EqFunction)


def test_eq_num_args():
    with pytest.raises(InvalidNumberOfArguments):
        Function.parse(None, 'EQ(1)', 0)

    with pytest.raises(InvalidNumberOfArguments):
        Function.parse(None, 'EQ(1, 2, 3)', 0)


def test_gt_boolean(literal_false, literal_true):
    result = comparison.GTFunction([literal_true, literal_false]).eval()
    assert result == 1

    result = comparison.GTFunction([literal_false, literal_false]).eval()
    assert result == 0


def test_gt_number(literal_one, literal_two):
    result = comparison.GTFunction([literal_two, literal_one]).eval()
    assert result == 1

    result = comparison.GTFunction([literal_one, literal_two]).eval()
    assert result == 0

    result = comparison.GTFunction([literal_two, literal_two]).eval()
    assert result == 0


def test_gt_parse():
    e = Function.parse(None, 'GT(1, 2)', 0)
    assert isinstance(e, comparison.GTFunction)


def test_gt_num_args():
    with pytest.raises(InvalidNumberOfArguments):
        Function.parse(None, 'GT(1)', 0)

    with pytest.raises(InvalidNumberOfArguments):
        Function.parse(None, 'GT(1, 2, 3)', 0)


def test_gte_boolean(literal_false, literal_true):
    result = comparison.GTEFunction([literal_true, literal_false]).eval()
    assert result == 1

    result = comparison.GTEFunction([literal_false, literal_false]).eval()
    assert result == 1

    result = comparison.GTEFunction([literal_false, literal_true]).eval()
    assert result == 0


def test_gte_number(literal_one, literal_two):
    result = comparison.GTEFunction([literal_two, literal_one]).eval()
    assert result == 1

    result = comparison.GTEFunction([literal_one, literal_two]).eval()
    assert result == 0

    result = comparison.GTEFunction([literal_two, literal_two]).eval()
    assert result == 1


def test_gte_parse():
    e = Function.parse(None, 'GTE(1, 2)', 0)
    assert isinstance(e, comparison.GTEFunction)


def test_gte_num_args():
    with pytest.raises(InvalidNumberOfArguments):
        Function.parse(None, 'GTE(1)', 0)

    with pytest.raises(InvalidNumberOfArguments):
        Function.parse(None, 'GTE(1, 2, 3)', 0)


def test_lt_boolean(literal_false, literal_true):
    result = comparison.LTFunction([literal_false, literal_true]).eval()
    assert result == 1

    result = comparison.LTFunction([literal_false, literal_false]).eval()
    assert result == 0


def test_lt_number(literal_one, literal_two):
    result = comparison.LTFunction([literal_one, literal_two]).eval()
    assert result == 1

    result = comparison.LTFunction([literal_two, literal_one]).eval()
    assert result == 0

    result = comparison.LTFunction([literal_two, literal_two]).eval()
    assert result == 0


def test_lt_parse():
    e = Function.parse(None, 'LT(1, 2)', 0)
    assert isinstance(e, comparison.LTFunction)


def test_lt_num_args():
    with pytest.raises(InvalidNumberOfArguments):
        Function.parse(None, 'LT(1)', 0)

    with pytest.raises(InvalidNumberOfArguments):
        Function.parse(None, 'LT(1, 2, 3)', 0)


def test_lte_boolean(literal_false, literal_true):
    result = comparison.LTEFunction([literal_false, literal_true]).eval()
    assert result == 1

    result = comparison.LTEFunction([literal_false, literal_false]).eval()
    assert result == 1

    result = comparison.LTEFunction([literal_true, literal_false]).eval()
    assert result == 0


def test_lte_number(literal_one, literal_two):
    result = comparison.LTEFunction([literal_one, literal_two]).eval()
    assert result == 1

    result = comparison.LTEFunction([literal_two, literal_one]).eval()
    assert result == 0

    result = comparison.LTEFunction([literal_two, literal_two]).eval()
    assert result == 1


def test_lte_parse():
    e = Function.parse(None, 'LTE(1, 2)', 0)
    assert isinstance(e, comparison.LTEFunction)


def test_lte_num_args():
    with pytest.raises(InvalidNumberOfArguments):
        Function.parse(None, 'LTE(1)', 0)

    with pytest.raises(InvalidNumberOfArguments):
        Function.parse(None, 'LTE(1, 2, 3)', 0)
