import pytest

from qtoggleserver.core.expressions import ROLE_VALUE, literalvalues, parse
from qtoggleserver.core.expressions.exceptions import ValueUnavailable


def test_literal_parse_bool():
    e = parse(None, "false", role=ROLE_VALUE)
    assert isinstance(e, literalvalues.LiteralValue)
    assert e.value == 0

    e = parse(None, "true", role=ROLE_VALUE)
    assert isinstance(e, literalvalues.LiteralValue)
    assert e.value == 1


def test_literal_parse_num():
    e = parse(None, "16384", role=ROLE_VALUE)
    assert isinstance(e, literalvalues.LiteralValue)
    assert e.value == 16384

    e = parse(None, "-3.14", role=ROLE_VALUE)
    assert isinstance(e, literalvalues.LiteralValue)
    assert e.value == -3.14


async def test_literal_unavailable(dummy_eval_context):
    e = parse(None, "unavailable", role=ROLE_VALUE)
    with pytest.raises(ValueUnavailable):
        await e.eval(dummy_eval_context)


def test_literal_parse_unavailable():
    e = parse(None, "unavailable", role=ROLE_VALUE)
    assert isinstance(e, literalvalues.LiteralValue)
    assert e.value is None

    e = parse(None, "-3.14", role=ROLE_VALUE)
    assert isinstance(e, literalvalues.LiteralValue)
    assert e.value == -3.14
