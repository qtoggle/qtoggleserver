from qtoggleserver.core.expressions import DEP_ASAP, Role
from tests.unit.qtoggleserver.mock.expressions import MockExpression, MockFunction


class TestFunction:
    def test_is_asap_eval_paused(self):
        f11 = MockFunction(args=[], role=Role.VALUE)
        f12 = MockFunction(args=[], role=Role.VALUE)
        f13 = MockFunction(args=[], role=Role.VALUE)
        f1 = MockFunction(args=[f11, f12, f13], role=Role.VALUE)
        f2 = MockFunction(args=[], role=Role.VALUE)
        e = MockExpression()
        f = MockFunction(args=[f1, f2, e], role=Role.VALUE)

        for func in [f, f11, f12, f1, f2, e]:
            func.DEPS = {DEP_ASAP}

        f11.pause_asap_eval(1000)
        f12.pause_asap_eval(2000)
        f13.pause_asap_eval(500)  # should be ignored because doesn't depend on ASAP
        f1.pause_asap_eval(3000)
        f2.pause_asap_eval(4000)
        f.pause_asap_eval(5000)
        e.pause_asap_eval(400)  # should be ignored because it's not a function

        assert f.is_asap_eval_paused(999)
        assert not f.is_asap_eval_paused(1000)
