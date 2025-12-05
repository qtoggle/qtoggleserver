import pytest

from qtoggleserver.core.expressions import Role, literalvalues, parse
from qtoggleserver.core.expressions.exceptions import ValueUnavailable


class TestLiteralValue:
    async def test_eval(self, dummy_eval_context):
        e = literalvalues.LiteralValue(42, "42", role=Role.VALUE)
        assert await e._eval(dummy_eval_context) == 42

        e.value = 84.5
        assert await e._eval(dummy_eval_context) == 84.5

        e.value = False
        assert await e._eval(dummy_eval_context) is False

        e.value = None
        with pytest.raises(ValueUnavailable):
            await e._eval(dummy_eval_context)

    def test_bool(self):
        e = parse(None, "false", role=Role.VALUE)
        assert isinstance(e, literalvalues.LiteralValue)
        assert e.value == 0

        e = parse(None, "true", role=Role.VALUE)
        assert isinstance(e, literalvalues.LiteralValue)
        assert e.value == 1

    def test_num(self):
        e = parse(None, "16384", role=Role.VALUE)
        assert isinstance(e, literalvalues.LiteralValue)
        assert e.value == 16384

        e = parse(None, "-3.14", role=Role.VALUE)
        assert isinstance(e, literalvalues.LiteralValue)
        assert e.value == -3.14

    async def test_unavailable(self, dummy_eval_context):
        e = parse(None, "unavailable", role=Role.VALUE)
        assert isinstance(e, literalvalues.LiteralValue)
        assert e.value is None
