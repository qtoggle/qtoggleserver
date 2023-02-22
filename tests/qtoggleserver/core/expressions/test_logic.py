import pytest

from qtoggleserver.core.expressions import ROLE_VALUE, Function, InvalidNumberOfArguments, logic


async def test_and_simple(literal_false, literal_true, dummy_eval_context):
    result = await logic.AndFunction([literal_false, literal_true], role=ROLE_VALUE).eval(dummy_eval_context)
    assert result == 0

    result = await logic.AndFunction([literal_false, literal_false], role=ROLE_VALUE).eval(dummy_eval_context)
    assert result == 0

    result = await logic.AndFunction([literal_true, literal_true], role=ROLE_VALUE).eval(dummy_eval_context)
    assert result == 1


async def test_and_multiple(literal_false, literal_true, dummy_eval_context):
    result = await logic.AndFunction(
        [literal_false, literal_true, literal_true], role=ROLE_VALUE
    ).eval(dummy_eval_context)
    assert result == 0

    result = await logic.AndFunction(
        [literal_true, literal_true, literal_true], role=ROLE_VALUE
    ).eval(dummy_eval_context)
    assert result == 1


async def test_and_unavailable(literal_false, literal_true, literal_unavailable, dummy_eval_context):
    result = await logic.AndFunction(
        [literal_true, literal_false, literal_unavailable], role=ROLE_VALUE
    ).eval(dummy_eval_context)
    assert result == 0


async def test_and_number(literal_zero, literal_ten, literal_true, dummy_eval_context):
    result = await logic.AndFunction([literal_zero, literal_true], role=ROLE_VALUE).eval(dummy_eval_context)
    assert result == 0

    result = await logic.AndFunction([literal_ten, literal_true], role=ROLE_VALUE).eval(dummy_eval_context)
    assert result == 1


def test_and_parse():
    e = Function.parse(None, 'AND(false, true)', ROLE_VALUE, 0)
    assert isinstance(e, logic.AndFunction)


def test_and_num_args():
    with pytest.raises(InvalidNumberOfArguments):
        Function.parse(None, 'AND(false)', ROLE_VALUE, 0)


async def test_or_simple(literal_false, literal_true, dummy_eval_context):
    result = await logic.OrFunction([literal_false, literal_false], role=ROLE_VALUE).eval(dummy_eval_context)
    assert result == 0

    result = await logic.OrFunction([literal_false, literal_true], role=ROLE_VALUE).eval(dummy_eval_context)
    assert result == 1

    result = await logic.OrFunction([literal_true, literal_true], role=ROLE_VALUE).eval(dummy_eval_context)
    assert result == 1


async def test_or_multiple(literal_false, literal_true, dummy_eval_context):
    result = await logic.OrFunction(
        [literal_false, literal_false, literal_false], role=ROLE_VALUE
    ).eval(dummy_eval_context)
    assert result == 0

    result = await logic.OrFunction(
        [literal_false, literal_true, literal_false], role=ROLE_VALUE
    ).eval(dummy_eval_context)
    assert result == 1


async def test_or_unavailable(literal_false, literal_true, literal_unavailable, dummy_eval_context):
    result = await logic.OrFunction(
        [literal_false, literal_true, literal_unavailable], role=ROLE_VALUE
    ).eval(dummy_eval_context)
    assert result == 1


async def test_or_number(literal_zero, literal_ten, literal_true, literal_false, dummy_eval_context):
    result = await logic.OrFunction([literal_zero, literal_true], role=ROLE_VALUE).eval(dummy_eval_context)
    assert result == 1

    result = await logic.OrFunction([literal_ten, literal_false], role=ROLE_VALUE).eval(dummy_eval_context)
    assert result == 1


def test_or_parse():
    e = Function.parse(None, 'OR(false, true)', ROLE_VALUE, 0)
    assert isinstance(e, logic.OrFunction)


def test_or_num_args():
    with pytest.raises(InvalidNumberOfArguments):
        Function.parse(None, 'OR(false)', ROLE_VALUE, 0)


async def test_not_simple(literal_false, literal_true, dummy_eval_context):
    result = await logic.NotFunction([literal_false], role=ROLE_VALUE).eval(dummy_eval_context)
    assert result == 1

    result = await logic.NotFunction([literal_true], role=ROLE_VALUE).eval(dummy_eval_context)
    assert result == 0


async def test_not_number(literal_zero, literal_ten, dummy_eval_context):
    result = await logic.NotFunction([literal_zero], role=ROLE_VALUE).eval(dummy_eval_context)
    assert result == 1

    result = await logic.NotFunction([literal_ten], role=ROLE_VALUE).eval(dummy_eval_context)
    assert result == 0


def test_not_parse():
    e = Function.parse(None, 'NOT(false)', ROLE_VALUE, 0)
    assert isinstance(e, logic.NotFunction)


def test_not_num_args():
    with pytest.raises(InvalidNumberOfArguments):
        Function.parse(None, 'NOT()', ROLE_VALUE, 0)

    with pytest.raises(InvalidNumberOfArguments):
        Function.parse(None, 'NOT(false, true)', ROLE_VALUE, 0)


async def test_xor_simple(literal_false, literal_true, dummy_eval_context):
    result = await logic.XOrFunction([literal_false, literal_false], role=ROLE_VALUE).eval(dummy_eval_context)
    assert result == 0

    result = await logic.XOrFunction([literal_false, literal_true], role=ROLE_VALUE).eval(dummy_eval_context)
    assert result == 1

    result = await logic.XOrFunction([literal_true, literal_true], role=ROLE_VALUE).eval(dummy_eval_context)
    assert result == 0


async def test_xor_number(literal_zero, literal_ten, literal_true, literal_false, dummy_eval_context):
    result = await logic.XOrFunction([literal_zero, literal_true], role=ROLE_VALUE).eval(dummy_eval_context)
    assert result == 1

    result = await logic.XOrFunction([literal_ten, literal_false], role=ROLE_VALUE).eval(dummy_eval_context)
    assert result == 1

    result = await logic.XOrFunction([literal_ten, literal_true], role=ROLE_VALUE).eval(dummy_eval_context)
    assert result == 0


def test_xor_parse():
    e = Function.parse(None, 'XOR(false, true)', ROLE_VALUE, 0)
    assert isinstance(e, logic.XOrFunction)


def test_xor_num_args():
    with pytest.raises(InvalidNumberOfArguments):
        Function.parse(None, 'XOR(false)', ROLE_VALUE, 0)

    with pytest.raises(InvalidNumberOfArguments):
        Function.parse(None, 'XOR(false, true, false)', ROLE_VALUE, 0)
