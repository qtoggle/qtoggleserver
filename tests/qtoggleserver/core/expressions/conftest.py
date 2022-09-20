import pytest

from qtoggleserver.core.expressions import ROLE_VALUE, EvalContext, literalvalues


@pytest.fixture(scope='session')
def dummy_eval_context(dummy_local_datetime):
    return EvalContext(port_values={}, now_ms=int(dummy_local_datetime.timestamp() * 1000))


@pytest.fixture()
def later_eval_context(dummy_eval_context):
    def wrapper_advance_eval_context_time(milliseconds: int) -> EvalContext:
        return EvalContext(dummy_eval_context.port_values, dummy_eval_context.now_ms + milliseconds)

    return wrapper_advance_eval_context_time


@pytest.fixture(scope='session')
def literal_false():
    return literalvalues.LiteralValue(False, 'false', role=ROLE_VALUE)


@pytest.fixture(scope='session')
def literal_true():
    return literalvalues.LiteralValue(True, 'true', role=ROLE_VALUE)


@pytest.fixture(scope='session')
def literal_zero():
    return literalvalues.LiteralValue(0, '0', role=ROLE_VALUE)


@pytest.fixture(scope='session')
def literal_zero_point_five():
    return literalvalues.LiteralValue(0.5, '0.5', role=ROLE_VALUE)


@pytest.fixture(scope='session')
def literal_one():
    return literalvalues.LiteralValue(1, '1', role=ROLE_VALUE)


@pytest.fixture(scope='session')
def literal_two():
    return literalvalues.LiteralValue(2, '2', role=ROLE_VALUE)


@pytest.fixture(scope='session')
def literal_three():
    return literalvalues.LiteralValue(3, '3', role=ROLE_VALUE)


@pytest.fixture(scope='session')
def literal_pi():
    return literalvalues.LiteralValue(3.14159, '3.14159', role=ROLE_VALUE)


@pytest.fixture(scope='session')
def literal_ten():
    return literalvalues.LiteralValue(10, '10', role=ROLE_VALUE)


@pytest.fixture(scope='session')
def literal_ten_point_fifty_one():
    return literalvalues.LiteralValue(10.51, '10.51', role=ROLE_VALUE)


@pytest.fixture(scope='session')
def literal_sixteen():
    return literalvalues.LiteralValue(16, '16', role=ROLE_VALUE)


@pytest.fixture(scope='session')
def literal_one_hundred():
    return literalvalues.LiteralValue(100, '100', role=ROLE_VALUE)


@pytest.fixture(scope='session')
def literal_two_hundreds():
    return literalvalues.LiteralValue(200, '200', role=ROLE_VALUE)


@pytest.fixture(scope='session')
def literal_one_thousand():
    return literalvalues.LiteralValue(1000, '1000', role=ROLE_VALUE)


@pytest.fixture(scope='session')
def literal_minus_one():
    return literalvalues.LiteralValue(-1, '-1', role=ROLE_VALUE)


@pytest.fixture(scope='session')
def literal_minus_two():
    return literalvalues.LiteralValue(-2, '-2', role=ROLE_VALUE)


@pytest.fixture(scope='session')
def literal_minus_pi():
    return literalvalues.LiteralValue(-3.14159, '-3.14159', role=ROLE_VALUE)


@pytest.fixture(scope='session')
def literal_minus_ten_point_fifty_one():
    return literalvalues.LiteralValue(-10.51, '-10.51', role=ROLE_VALUE)


@pytest.fixture(scope='session')
def literal_dummy_timestamp(dummy_timestamp):
    return literalvalues.LiteralValue(dummy_timestamp, str(dummy_timestamp), role=ROLE_VALUE)
