import pytest

from qtoggleserver.core.expressions import Role, literalvalues, parse
from qtoggleserver.core.expressions.exceptions import UnexpectedCharacter, ValueUnavailable


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

    @pytest.mark.parametrize(
        "sexpression, value",
        [("0", 0), ("007", 7), ("-0", 0), ("-12", -12), ("3.25", 3.25), ("-0.5", -0.5), ("10.0", 10.0)],
    )
    def test_spec_numbers(self, sexpression, value):
        """Should accept base 10 numbers with an optional minus sign and a dot between digits, as int or float."""

        e = parse(None, sexpression, role=Role.VALUE)
        assert e._coerced_value == value
        assert type(e._coerced_value) is type(value)

    @pytest.mark.parametrize(
        "sexpression, token, pos",
        [
            ("inf", "i", 1),
            ("nan", "n", 1),
            ("infinity", "i", 1),
            ("1e3", "e", 2),
            ("1E3", "E", 2),
            ("1_000", "_", 2),
            ("+5", "+", 1),
            ("١٢", "١", 1),  # Arabic-Indic digits
            (".5", ".", 1),
            ("5.", ".", 2),
            ("-", "-", 1),
            ("1.2.3", ".", 4),
            ("ADD(1e3, 2)", "e", 6),
        ],
    )
    def test_non_spec_numbers(self, sexpression, token, pos):
        """Should reject numbers that only Python's int() or float() accept, at their first unexpected character."""

        with pytest.raises(UnexpectedCharacter) as exc_info:
            parse(None, sexpression, role=Role.VALUE)
        assert exc_info.value.to_json() == {"reason": "unexpected-character", "token": token, "pos": pos}

    async def test_too_many_digits(self, dummy_eval_context):
        """Should parse an integer too long for Python's int(), and evaluate it to unavailable, like an overflowing
        float."""

        e = parse(None, "1" * 4301, role=Role.VALUE)
        with pytest.raises(ValueUnavailable):
            await e.eval(dummy_eval_context)
