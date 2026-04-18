import pytest

from qtoggleserver.core.expressions import Role, literalvalues, parse
from qtoggleserver.core.expressions.exceptions import ValueUnavailable


class TestLiteralValue:
    async def test_eval(self, dummy_eval_context):
        e = literalvalues.LiteralValue(42, "42", role=Role.VALUE)
        assert await e._eval(dummy_eval_context) == 42

        e = literalvalues.LiteralValue(84.5, "84.5", role=Role.VALUE)
        assert await e._eval(dummy_eval_context) == 84.5

        e = literalvalues.LiteralValue(False, "false", role=Role.VALUE)
        assert await e._eval(dummy_eval_context) == 0

        e = literalvalues.LiteralValue(True, "true", role=Role.VALUE)
        assert await e._eval(dummy_eval_context) == 1

        e = literalvalues.LiteralValue(None, "unavailable", role=Role.VALUE)
        with pytest.raises(ValueUnavailable):
            await e._eval(dummy_eval_context)

    def test_bool(self):
        e = parse(None, "false", role=Role.VALUE)
        assert isinstance(e, literalvalues.LiteralValue)
        assert e._coerced_value == 0

        e = parse(None, "true", role=Role.VALUE)
        assert isinstance(e, literalvalues.LiteralValue)
        assert e._coerced_value == 1

    def test_num(self):
        e = parse(None, "16384", role=Role.VALUE)
        assert isinstance(e, literalvalues.LiteralValue)
        assert e._coerced_value == 16384

        e = parse(None, "-3.14", role=Role.VALUE)
        assert isinstance(e, literalvalues.LiteralValue)
        assert e._coerced_value == -3.14

    async def test_unavailable(self, dummy_eval_context):
        e = parse(None, "unavailable", role=Role.VALUE)
        assert isinstance(e, literalvalues.LiteralValue)
        assert e._coerced_value is None
