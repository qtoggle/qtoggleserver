
import pytest

from qtoggleserver.core.expressions import literalvalues
from qtoggleserver.core.expressions import EvalContext


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
    return literalvalues.LiteralValue(False, 'false')


@pytest.fixture(scope='session')
def literal_true():
    return literalvalues.LiteralValue(True, 'true')


@pytest.fixture(scope='session')
def literal_zero():
    return literalvalues.LiteralValue(0, '0')


@pytest.fixture(scope='session')
def literal_zero_point_five():
    return literalvalues.LiteralValue(0.5, '0.5')


@pytest.fixture(scope='session')
def literal_one():
    return literalvalues.LiteralValue(1, '1')


@pytest.fixture(scope='session')
def literal_two():
    return literalvalues.LiteralValue(2, '2')


@pytest.fixture(scope='session')
def literal_three():
    return literalvalues.LiteralValue(3, '3')


@pytest.fixture(scope='session')
def literal_pi():
    return literalvalues.LiteralValue(3.14159, '3.14159')


@pytest.fixture(scope='session')
def literal_ten():
    return literalvalues.LiteralValue(10, '10')


@pytest.fixture(scope='session')
def literal_ten_point_fifty_one():
    return literalvalues.LiteralValue(10.51, '10.51')


@pytest.fixture(scope='session')
def literal_sixteen():
    return literalvalues.LiteralValue(16, '16')


@pytest.fixture(scope='session')
def literal_one_hundred():
    return literalvalues.LiteralValue(100, '100')


@pytest.fixture(scope='session')
def literal_two_hundreds():
    return literalvalues.LiteralValue(200, '200')


@pytest.fixture(scope='session')
def literal_one_thousand():
    return literalvalues.LiteralValue(1000, '1000')


@pytest.fixture(scope='session')
def literal_minus_one():
    return literalvalues.LiteralValue(-1, '-1')


@pytest.fixture(scope='session')
def literal_minus_two():
    return literalvalues.LiteralValue(-2, '-2')


@pytest.fixture(scope='session')
def literal_minus_pi():
    return literalvalues.LiteralValue(-3.14159, '-3.14159')


@pytest.fixture(scope='session')
def literal_minus_ten_point_fifty_one():
    return literalvalues.LiteralValue(-10.51, '-10.51')


@pytest.fixture(scope='session')
def literal_dummy_timestamp(dummy_timestamp):
    return literalvalues.LiteralValue(dummy_timestamp, str(dummy_timestamp))
