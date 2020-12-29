
from qtoggleserver.core.expressions import parse
from qtoggleserver.core.expressions import literalvalues


def test_literal_parse_bool():
    e = parse(None, 'false')
    assert isinstance(e, literalvalues.LiteralValue)
    assert e.value == 0

    e = parse(None, 'true')
    assert isinstance(e, literalvalues.LiteralValue)
    assert e.value == 1


def test_literal_parse_num():
    e = parse(None, '16384')
    assert isinstance(e, literalvalues.LiteralValue)
    assert e.value == 16384

    e = parse(None, '-3.14')
    assert isinstance(e, literalvalues.LiteralValue)
    assert e.value == -3.14
