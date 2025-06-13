import pytest

from qtoggleserver.core.expressions import ROLE_VALUE, Function, comparison
from qtoggleserver.core.expressions.exceptions import InvalidNumberOfArguments


async def test_if_boolean(literal_false, literal_true, literal_one, literal_two, dummy_eval_context):
    result = await comparison.IfFunction([literal_false, literal_one, literal_two], role=ROLE_VALUE).eval(
        dummy_eval_context
    )
    assert result == 2

    result = await comparison.IfFunction([literal_true, literal_one, literal_two], role=ROLE_VALUE).eval(
        dummy_eval_context
    )
    assert result == 1


async def test_if_number(literal_zero, literal_one, literal_two, dummy_eval_context):
    result = await comparison.IfFunction([literal_zero, literal_one, literal_two], role=ROLE_VALUE).eval(
        dummy_eval_context
    )
    assert result == 2

    result = await comparison.IfFunction([literal_two, literal_one, literal_two], role=ROLE_VALUE).eval(
        dummy_eval_context
    )
    assert result == 1


async def test_if_unavailable(literal_false, literal_true, literal_ten, literal_unavailable, dummy_eval_context):
    result = await comparison.IfFunction([literal_false, literal_unavailable, literal_ten], role=ROLE_VALUE).eval(
        dummy_eval_context
    )
    assert result == 10

    result = await comparison.IfFunction([literal_true, literal_ten, literal_unavailable], role=ROLE_VALUE).eval(
        dummy_eval_context
    )
    assert result == 10


def test_if_parse():
    e = Function.parse(None, "IF(1, 2, 3)", ROLE_VALUE, 0)
    assert isinstance(e, comparison.IfFunction)


def test_if_num_args():
    with pytest.raises(InvalidNumberOfArguments):
        Function.parse(None, "IF(1, 2)", ROLE_VALUE, 0)

    with pytest.raises(InvalidNumberOfArguments):
        Function.parse(None, "IF(1, 2, 3, 4)", ROLE_VALUE, 0)


async def test_eq_boolean(literal_false, literal_true, dummy_eval_context):
    result = await comparison.EqFunction([literal_false, literal_true], role=ROLE_VALUE).eval(dummy_eval_context)
    assert result == 0

    result = await comparison.EqFunction([literal_false, literal_false], role=ROLE_VALUE).eval(dummy_eval_context)
    assert result == 1


async def test_eq_number(literal_one, literal_two, dummy_eval_context):
    result = await comparison.EqFunction([literal_one, literal_two], role=ROLE_VALUE).eval(dummy_eval_context)
    assert result == 0

    result = await comparison.EqFunction([literal_two, literal_two], role=ROLE_VALUE).eval(dummy_eval_context)
    assert result == 1


def test_eq_parse():
    e = Function.parse(None, "EQ(1, 2)", ROLE_VALUE, 0)
    assert isinstance(e, comparison.EqFunction)


def test_eq_num_args():
    with pytest.raises(InvalidNumberOfArguments):
        Function.parse(None, "EQ(1)", ROLE_VALUE, 0)

    with pytest.raises(InvalidNumberOfArguments):
        Function.parse(None, "EQ(1, 2, 3)", ROLE_VALUE, 0)


async def test_gt_boolean(literal_false, literal_true, dummy_eval_context):
    result = await comparison.GTFunction([literal_true, literal_false], role=ROLE_VALUE).eval(dummy_eval_context)
    assert result == 1

    result = await comparison.GTFunction([literal_false, literal_false], role=ROLE_VALUE).eval(dummy_eval_context)
    assert result == 0


async def test_gt_number(literal_one, literal_two, dummy_eval_context):
    result = await comparison.GTFunction([literal_two, literal_one], role=ROLE_VALUE).eval(dummy_eval_context)
    assert result == 1

    result = await comparison.GTFunction([literal_one, literal_two], role=ROLE_VALUE).eval(dummy_eval_context)
    assert result == 0

    result = await comparison.GTFunction([literal_two, literal_two], role=ROLE_VALUE).eval(dummy_eval_context)
    assert result == 0


def test_gt_parse():
    e = Function.parse(None, "GT(1, 2)", ROLE_VALUE, 0)
    assert isinstance(e, comparison.GTFunction)


def test_gt_num_args():
    with pytest.raises(InvalidNumberOfArguments):
        Function.parse(None, "GT(1)", ROLE_VALUE, 0)

    with pytest.raises(InvalidNumberOfArguments):
        Function.parse(None, "GT(1, 2, 3)", ROLE_VALUE, 0)


async def test_gte_boolean(literal_false, literal_true, dummy_eval_context):
    result = await comparison.GTEFunction([literal_true, literal_false], role=ROLE_VALUE).eval(dummy_eval_context)
    assert result == 1

    result = await comparison.GTEFunction([literal_false, literal_false], role=ROLE_VALUE).eval(dummy_eval_context)
    assert result == 1

    result = await comparison.GTEFunction([literal_false, literal_true], role=ROLE_VALUE).eval(dummy_eval_context)
    assert result == 0


async def test_gte_number(literal_one, literal_two, dummy_eval_context):
    result = await comparison.GTEFunction([literal_two, literal_one], role=ROLE_VALUE).eval(dummy_eval_context)
    assert result == 1

    result = await comparison.GTEFunction([literal_one, literal_two], role=ROLE_VALUE).eval(dummy_eval_context)
    assert result == 0

    result = await comparison.GTEFunction([literal_two, literal_two], role=ROLE_VALUE).eval(dummy_eval_context)
    assert result == 1


def test_gte_parse():
    e = Function.parse(None, "GTE(1, 2)", ROLE_VALUE, 0)
    assert isinstance(e, comparison.GTEFunction)


def test_gte_num_args():
    with pytest.raises(InvalidNumberOfArguments):
        Function.parse(None, "GTE(1)", ROLE_VALUE, 0)

    with pytest.raises(InvalidNumberOfArguments):
        Function.parse(None, "GTE(1, 2, 3)", ROLE_VALUE, 0)


async def test_lt_boolean(literal_false, literal_true, dummy_eval_context):
    result = await comparison.LTFunction([literal_false, literal_true], role=ROLE_VALUE).eval(dummy_eval_context)
    assert result == 1

    result = await comparison.LTFunction([literal_false, literal_false], role=ROLE_VALUE).eval(dummy_eval_context)
    assert result == 0


async def test_lt_number(literal_one, literal_two, dummy_eval_context):
    result = await comparison.LTFunction([literal_one, literal_two], role=ROLE_VALUE).eval(dummy_eval_context)
    assert result == 1

    result = await comparison.LTFunction([literal_two, literal_one], role=ROLE_VALUE).eval(dummy_eval_context)
    assert result == 0

    result = await comparison.LTFunction([literal_two, literal_two], role=ROLE_VALUE).eval(dummy_eval_context)
    assert result == 0


def test_lt_parse():
    e = Function.parse(None, "LT(1, 2)", ROLE_VALUE, 0)
    assert isinstance(e, comparison.LTFunction)


def test_lt_num_args():
    with pytest.raises(InvalidNumberOfArguments):
        Function.parse(None, "LT(1)", ROLE_VALUE, 0)

    with pytest.raises(InvalidNumberOfArguments):
        Function.parse(None, "LT(1, 2, 3)", ROLE_VALUE, 0)


async def test_lte_boolean(literal_false, literal_true, dummy_eval_context):
    result = await comparison.LTEFunction([literal_false, literal_true], role=ROLE_VALUE).eval(dummy_eval_context)
    assert result == 1

    result = await comparison.LTEFunction([literal_false, literal_false], role=ROLE_VALUE).eval(dummy_eval_context)
    assert result == 1

    result = await comparison.LTEFunction([literal_true, literal_false], role=ROLE_VALUE).eval(dummy_eval_context)
    assert result == 0


async def test_lte_number(literal_one, literal_two, dummy_eval_context):
    result = await comparison.LTEFunction([literal_one, literal_two], role=ROLE_VALUE).eval(dummy_eval_context)
    assert result == 1

    result = await comparison.LTEFunction([literal_two, literal_one], role=ROLE_VALUE).eval(dummy_eval_context)
    assert result == 0

    result = await comparison.LTEFunction([literal_two, literal_two], role=ROLE_VALUE).eval(dummy_eval_context)
    assert result == 1


def test_lte_parse():
    e = Function.parse(None, "LTE(1, 2)", ROLE_VALUE, 0)
    assert isinstance(e, comparison.LTEFunction)


def test_lte_num_args():
    with pytest.raises(InvalidNumberOfArguments):
        Function.parse(None, "LTE(1)", ROLE_VALUE, 0)

    with pytest.raises(InvalidNumberOfArguments):
        Function.parse(None, "LTE(1, 2, 3)", ROLE_VALUE, 0)
