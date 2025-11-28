import pytest

from qtoggleserver.core.expressions import DEP_ASAP, DEP_SECOND, Function, Role, time
from qtoggleserver.core.expressions.exceptions import InvalidNumberOfArguments, UnknownFunction


class TestTime:
    async def test_time(self, dummy_timestamp, dummy_eval_context):
        result = await time.TimeFunction([], role=Role.VALUE).eval(dummy_eval_context)
        assert result == int(dummy_timestamp)

    def test_time_parse(self):
        e = Function.parse(None, "TIME()", Role.VALUE, 0)
        assert isinstance(e, time.TimeFunction)

    def test_time_num_args(self):
        with pytest.raises(InvalidNumberOfArguments):
            Function.parse(None, "TIME(1)", Role.VALUE, 0)

    @pytest.mark.parametrize("role", [Role.TRANSFORM_READ, Role.TRANSFORM_WRITE])
    def test_time_no_transform(self, role):
        with pytest.raises(UnknownFunction):
            Function.parse(None, "TIME()", role, 0)

    def test_time_deps(self):
        assert time.TimeFunction.DEPS == {DEP_SECOND}


class TestTimeMS:
    async def test_timems(self, dummy_timestamp, dummy_eval_context):
        result = await time.TimeMSFunction([], role=Role.VALUE).eval(dummy_eval_context)
        assert result == int(dummy_timestamp * 1000)

    def test_timems_parse(self):
        e = Function.parse(None, "TIMEMS()", Role.VALUE, 0)
        assert isinstance(e, time.TimeMSFunction)

    def test_timems_num_args(self):
        with pytest.raises(InvalidNumberOfArguments):
            Function.parse(None, "TIMEMS(1)", Role.VALUE, 0)

    @pytest.mark.parametrize("role", [Role.TRANSFORM_READ, Role.TRANSFORM_WRITE])
    def test_timems_no_transform(self, role):
        with pytest.raises(UnknownFunction):
            Function.parse(None, "TIMEMS()", role, 0)

    def test_timems_deps(self):
        assert time.TimeMSFunction.DEPS == {DEP_ASAP}
