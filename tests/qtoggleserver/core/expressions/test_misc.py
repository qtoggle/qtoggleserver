
import pytest

from qtoggleserver.core.expressions import parse
from qtoggleserver.core.expressions import UnknownFunction, UnbalancedParentheses, UnexpectedEnd, UnexpectedCharacter
from qtoggleserver.core.expressions import EmptyExpression


async def test_parse_complex_expression(num_mock_port1, num_mock_port2):
    num_mock_port1.set_last_read_value(5)
    num_mock_port2.set_last_read_value(-4)

    e = parse('nid1', 'ADD(10, MUL($, 3.14), $nid2)')
    assert round(await e.eval(), 1) == 21.7

    e = parse('nid1', 'ADD(10, MUL($, 3.14), DIV(10, 2), MIN($nid2, 10, $))')
    assert round(await e.eval(), 1) == 26.7


async def test_parse_whitespace(num_mock_port1, num_mock_port2):
    num_mock_port1.set_last_read_value(5)
    num_mock_port2.set_last_read_value(-4)

    e = parse('nid1', '  ADD  (\t10,  MUL  (  $,  3.14  )  ,  $nid2  )  ')
    assert round(await e.eval(), 1) == 21.7


async def test_parse_unknown_function():
    with pytest.raises(UnknownFunction) as exc_info:
        parse(None, 'ADD(10, UNKNOWN_FUNC(3, 14))')

    assert exc_info.value.name == 'UNKNOWN_FUNC'
    assert exc_info.value.pos == 9


async def test_parse_unbalanced_parentheses():
    with pytest.raises(UnbalancedParentheses) as exc_info:
        parse(None, 'ADD(10)), MUL(3, 14))')

    assert exc_info.value.pos == 8


async def test_parse_unexpected_end():
    with pytest.raises(UnexpectedEnd):
        parse(None, 'ADD(10, MUL(3, 14)')


async def test_parse_unexpected_character():
    with pytest.raises(UnexpectedCharacter) as exc_info:
        parse(None, '-ADD(10, $)')

    assert exc_info.value.c == '-'
    assert exc_info.value.pos == 1

    with pytest.raises(UnexpectedCharacter) as exc_info:
        parse(None, 'ADD#(10, $)')

    assert exc_info.value.c == '#'
    assert exc_info.value.pos == 4

    with pytest.raises(UnexpectedCharacter) as exc_info:
        parse(None, 'ADD(%$port, 10)')

    assert exc_info.value.c == '%'
    assert exc_info.value.pos == 5

    with pytest.raises(UnexpectedCharacter) as exc_info:
        parse(None, 'ADD($%port, 10)')

    assert exc_info.value.c == '%'
    assert exc_info.value.pos == 7

    with pytest.raises(UnexpectedCharacter) as exc_info:
        parse(None, 'ADD($port*, 10)')

    assert exc_info.value.c == '*'
    assert exc_info.value.pos == 11

    with pytest.raises(UnexpectedCharacter) as exc_info:
        parse(None, 'ADD(#, 10, $)')

    assert exc_info.value.c == '#'
    assert exc_info.value.pos == 5

    with pytest.raises(UnexpectedCharacter) as exc_info:
        parse(None, '3+4')

    assert exc_info.value.c == '+'
    assert exc_info.value.pos == 2


async def test_parse_empty():
    with pytest.raises(EmptyExpression):
        parse(None, '    ')
