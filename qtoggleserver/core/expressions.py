
from __future__ import annotations

import abc
import datetime
import math
import time

from typing import Callable, List, Optional, Set, Tuple

from qtoggleserver.core.typing import PortValue as CorePortValue


FUNCTIONS = {}


def function(name: str) -> Callable:
    def decorator(func_class: type) -> type:
        func_class.NAME = name
        FUNCTIONS[name] = func_class

        return func_class

    return decorator


class ExpressionError(Exception):
    pass


class InvalidExpression(ExpressionError):
    pass


class InvalidArgument(ExpressionError):
    def __init__(self, arg_no: int, value: CorePortValue) -> None:
        self.arg_no: int = arg_no
        self.value: CorePortValue = value

    def __str__(self) -> str:
        return f'invalid argument {self.arg_no}: {self.value}'


class CircularDependency(ExpressionError):
    pass


class IncompleteExpression(ExpressionError):
    pass


class Expression(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def eval(self) -> CorePortValue:
        raise NotImplementedError()

    def get_deps(self) -> Set[str]:
        # Special deps:
        #  * 'time' - used to indicate dependency on system time (seconds)
        #  * 'time_ms' - used to indicate dependency on system time (milliseconds)

        return set()

    @staticmethod
    @abc.abstractmethod
    def parse(self_port_id: Optional[str], sexpression: str) -> Expression:
        raise NotImplementedError()


class Constant(Expression):
    def __init__(self, value: CorePortValue, sexpression: str) -> None:
        self.value: CorePortValue = value
        self.sexpression: str = sexpression

    def __str__(self) -> str:
        return self.sexpression

    def eval(self) -> CorePortValue:
        return self.value

    @staticmethod
    def parse(self_port_id: Optional[str], sexpression: str) -> Expression:
        sexpression = sexpression.strip()

        if sexpression == 'true':
            value = 1

        elif sexpression == 'false':
            value = 0

        else:
            try:
                value = int(sexpression)

            except ValueError:
                try:
                    value = float(sexpression)

                except ValueError:
                    raise InvalidExpression(f'"{sexpression}" is not a valid constant') from None

        return Constant(value, sexpression)


class Function(Expression, metaclass=abc.ABCMeta):
    NAME = None
    MIN_ARGS = None
    MAX_ARGS = None

    def __init__(self, args: List[Expression]) -> None:
        self.args: List[Expression] = args
        self._deps: Optional[Set[str]] = None

    def __str__(self) -> str:
        s = getattr(self, '_str', None)
        if s is None:
            args_str = ', '.join(str(e) for e in self.args)
            self._str = s = f'{self.NAME}({args_str})'

        return s

    def get_deps(self) -> Set[str]:
        if self._deps is None:
            self._deps = set()

            for arg in self.args:
                self._deps |= arg.get_deps()

        return self._deps

    def eval_args(self) -> List[CorePortValue]:
        return [a.eval() for a in self.args]

    @staticmethod
    def parse(self_port_id: Optional[str], sexpression: str) -> Expression:
        sexpression = sexpression.strip()

        p_start = None
        p_end = None
        p_last_comma = None
        level = 0
        sargs = []
        for i, c in enumerate(sexpression):
            if c == '(':
                if p_start is None:
                    p_start = i

                elif level == 0:
                    raise InvalidExpression('Empty function call')

                level += 1

            elif c == ')':
                if level == 0:
                    raise InvalidExpression('Unbalanced parentheses')

                elif level == 1:
                    if (p_end is None) and (i == len(sexpression) - 1):
                        p_end = i

                    else:
                        raise InvalidExpression('Unexpected text after function call')

                level -= 1

            elif c == ',' and level == 1:
                sargs.append(sexpression[(p_last_comma or p_start) + 1: i])
                p_last_comma = i

        if (p_start is None) or (p_end is None) or (p_start > p_end) or (level != 0):
            raise InvalidExpression('Unbalanced parentheses')

        if p_end - p_start > 1:
            sargs.append(sexpression[(p_last_comma or p_start) + 1: p_end])

        func_name = sexpression[:p_start].strip()
        func_class = FUNCTIONS.get(func_name)
        if func_class is None:
            raise InvalidExpression(f'Unknown function "{func_name}"')

        if func_class.MIN_ARGS is not None and len(sargs) < func_class.MIN_ARGS:
            raise InvalidExpression(f'Too few arguments for function "{func_name}"')

        if func_class.MAX_ARGS is not None and len(sargs) > func_class.MAX_ARGS:
            raise InvalidExpression(f'Too many arguments for function "{func_name}"')

        args = [parse(self_port_id, sa) for sa in sargs]

        return func_class(args)


@function('ADD')
class AddFunction(Function):
    MIN_ARGS = 2

    def eval(self) -> CorePortValue:
        return sum(self.eval_args())


@function('SUB')
class SubFunction(Function):
    MIN_ARGS = MAX_ARGS = 2

    def eval(self) -> CorePortValue:
        eval_args = self.eval_args()
        return eval_args[0] - eval_args[1]


@function('MUL')
class MulFunction(Function):
    MIN_ARGS = 2

    def eval(self) -> CorePortValue:
        r = 1
        for e in self.eval_args():
            r *= e

        return r


@function('DIV')
class DivFunction(Function):
    MIN_ARGS = MAX_ARGS = 2

    def eval(self) -> CorePortValue:
        eval_args = self.eval_args()

        if eval_args[1]:
            return int(eval_args[0] / eval_args[1])

        else:
            return 0


@function('MOD')
class ModFunction(Function):
    MIN_ARGS = MAX_ARGS = 2

    def eval(self) -> CorePortValue:
        eval_args = self.eval_args()

        if eval_args[1]:
            return eval_args[0] % eval_args[1]

        else:
            return 0


@function('AND')
class AndFunction(Function):
    MIN_ARGS = 2

    def eval(self) -> CorePortValue:
        r = True
        for e in self.eval_args():
            r = r and bool(e)

        return int(r)


@function('OR')
class OrFunction(Function):
    MIN_ARGS = 2

    def eval(self) -> CorePortValue:
        r = False
        for e in self.eval_args():
            r = r or bool(e)

        return int(r)


@function('NOT')
class NotFunction(Function):
    MIN_ARGS = MAX_ARGS = 1

    def eval(self) -> CorePortValue:
        return int(not bool(self.eval_args()[0]))


@function('XOR')
class XorFunction(Function):
    MIN_ARGS = MAX_ARGS = 2

    def eval(self) -> CorePortValue:
        eval_args = self.eval_args()

        e1 = bool(eval_args[0])
        e2 = bool(eval_args[1])

        return int(e1 and not e2 or e2 and not e1)


@function('BITAND')
class BitAndFunction(Function):
    MIN_ARGS = MAX_ARGS = 2

    def eval(self) -> CorePortValue:
        r = -1
        for e in self.eval_args():
            r &= int(e)

        return r


@function('BITOR')
class BitOrFunction(Function):
    MIN_ARGS = MAX_ARGS = 2

    def eval(self) -> CorePortValue:
        r = 0
        for e in self.eval_args():
            r |= int(e)

        return r


@function('BITNOT')
class BitNotFunction(Function):
    MIN_ARGS = MAX_ARGS = 1

    def eval(self) -> CorePortValue:
        return ~int(self.eval_args()[0])


@function('BITXOR')
class BitXOrFunction(Function):
    MIN_ARGS = MAX_ARGS = 2

    def eval(self) -> CorePortValue:
        eval_args = self.eval_args()

        return int(eval_args[0]) ^ int(eval_args[1])


@function('SHL')
class SHLFunction(Function):
    MIN_ARGS = MAX_ARGS = 2

    def eval(self) -> CorePortValue:
        eval_args = self.eval_args()

        return int(eval_args[0]) << int(eval_args[1])


@function('SHR')
class SHRFunction(Function):
    MIN_ARGS = MAX_ARGS = 2

    def eval(self) -> CorePortValue:
        eval_args = self.eval_args()

        return int(eval_args[0]) >> int(eval_args[1])


@function('IF')
class IfFunction(Function):
    MIN_ARGS = MAX_ARGS = 3

    def eval(self) -> CorePortValue:
        eval_args = self.eval_args()

        if eval_args[0]:
            return eval_args[1]

        else:
            return eval_args[2]


@function('EQ')
class EqFunction(Function):
    MIN_ARGS = MAX_ARGS = 2

    def eval(self) -> CorePortValue:
        eval_args = self.eval_args()

        return int(eval_args[0] == eval_args[1])


@function('GT')
class GTFunction(Function):
    MIN_ARGS = MAX_ARGS = 2

    def eval(self) -> CorePortValue:
        eval_args = self.eval_args()

        return int(eval_args[0] > eval_args[1])


@function('GTE')
class GTEFunction(Function):
    MIN_ARGS = MAX_ARGS = 2

    def eval(self) -> CorePortValue:
        eval_args = self.eval_args()

        return int(eval_args[0] >= eval_args[1])


@function('LT')
class LTFunction(Function):
    MIN_ARGS = MAX_ARGS = 2

    def eval(self) -> CorePortValue:
        eval_args = self.eval_args()

        return int(eval_args[0] < eval_args[1])


@function('LTE')
class LTEFunction(Function):
    MIN_ARGS = MAX_ARGS = 2

    def eval(self) -> CorePortValue:
        eval_args = self.eval_args()

        return int(eval_args[0] <= eval_args[1])


@function('ABS')
class AbsFunction(Function):
    MIN_ARGS = MAX_ARGS = 1

    def eval(self) -> CorePortValue:
        return abs(self.eval_args()[0])


@function('SGN')
class SgnFunction(Function):
    MIN_ARGS = MAX_ARGS = 1

    def eval(self) -> CorePortValue:
        e = int(self.eval_args()[0])
        if e > 0:
            return 1

        elif e < 0:
            return -1

        else:
            return 0


@function('MIN')
class MinFunction(Function):
    MIN_ARGS = 2

    def eval(self) -> CorePortValue:
        eval_args = self.eval_args()

        m = eval_args[0]
        for e in eval_args[1:]:
            if e < m:
                m = e

        return m


@function('MAX')
class MaxFunction(Function):
    MIN_ARGS = 2

    def eval(self) -> CorePortValue:
        eval_args = self.eval_args()

        m = eval_args[0]
        for e in eval_args[1:]:
            if e > m:
                m = e

        return m


@function('FLOOR')
class FloorFunction(Function):
    MIN_ARGS = MAX_ARGS = 1

    def eval(self) -> CorePortValue:
        eval_args = self.eval_args()

        return int(math.floor(eval_args[0]))


@function('CEIL')
class CeilFunction(Function):
    MIN_ARGS = MAX_ARGS = 1

    def eval(self) -> CorePortValue:
        eval_args = self.eval_args()

        return int(math.ceil(eval_args[0]))


@function('ROUND')
class RoundFunction(Function):
    MIN_ARGS = 1
    MAX_ARGS = 2

    def eval(self) -> CorePortValue:
        eval_args = self.eval_args()

        v = eval_args[0]
        d = 0
        if len(eval_args) == 2:
            d = eval_args[1]

        return round(v, d)


@function('TIME')
class TimeFunction(Function):
    MIN_ARGS = MAX_ARGS = 0

    def get_deps(self) -> Set[str]:
        return {'time'}

    def eval(self) -> CorePortValue:
        return int(time.time())


@function('TIMEMS')
class TimeMSFunction(Function):
    MIN_ARGS = MAX_ARGS = 0

    def get_deps(self) -> Set[str]:
        return {'time_ms'}

    def eval(self) -> CorePortValue:
        return int(time.time() * 1000)


@function('HELD')
class HeldFunction(Function):
    MIN_ARGS = MAX_ARGS = 3

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self._time_ms: Optional[int] = None
        self._last_value: Optional[CorePortValue] = None

    def get_deps(self) -> Set[str]:
        return {'time_ms'}

    def eval(self) -> CorePortValue:
        time_ms = int(time.time() * 1000)
        result = False

        value = self.args[0].eval()
        fixed_value = self.args[1].eval()
        duration = self.args[2].eval()

        if self._time_ms is None:  # Very first expression eval call
            self._time_ms = time_ms

        else:
            delta = time_ms - self._time_ms

            if self._last_value != value:
                self._time_ms = time_ms  # Reset held timer

            else:
                result = (delta >= duration) and (value == fixed_value)

        self._last_value = value

        return result


@function('DELAY')
class DelayFunction(Function):
    MIN_ARGS = MAX_ARGS = 2
    HISTORY_SIZE = 1024

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self._queue: List[Tuple[int, CorePortValue]] = []
        self._last_value: Optional[CorePortValue] = None
        self._current_value: Optional[CorePortValue] = None

    def get_deps(self) -> Set[str]:
        return {'time_ms'}

    def eval(self) -> CorePortValue:
        time_ms = int(time.time() * 1000)

        value = self.args[0].eval()
        delay = self.args[1].eval()

        if self._current_value is None:
            self._current_value = value

        # Detect value transitions and build history
        if value != self._last_value:
            self._last_value = value

            # Drop elements from queue if history size reached
            while len(self._queue) >= self.HISTORY_SIZE:
                self._queue.pop(0)

            self._queue.append((time_ms, value))

        # Process history
        while self._queue and (time_ms - self._queue[0][0]) >= delay:
            self._current_value = self._queue.pop(0)[1]

        return self._current_value


@function('HYST')
class HystFunction(Function):
    MIN_ARGS = MAX_ARGS = 3

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self._last_result: int = 0

    def eval(self) -> CorePortValue:
        value = self.args[0].eval()
        threshold1 = self.args[1].eval()
        threshold2 = self.args[2].eval()

        self._last_result = int((self._last_result == 0 and value > threshold2) or
                                (self._last_result != 0 and value >= threshold1))

        return self._last_result


@function('YEAR')
class YearFunction(Function):
    MIN_ARGS = MAX_ARGS = 0

    def get_deps(self) -> Set[str]:
        return {'time'}

    def eval(self) -> CorePortValue:
        return datetime.datetime.now().year


@function('MONTH')
class MonthFunction(Function):
    MIN_ARGS = MAX_ARGS = 0

    def get_deps(self) -> Set[str]:
        return {'time'}

    def eval(self) -> CorePortValue:
        return datetime.datetime.now().month


@function('DAY')
class DayFunction(Function):
    MIN_ARGS = MAX_ARGS = 0

    def get_deps(self) -> Set[str]:
        return {'time'}

    def eval(self) -> CorePortValue:
        return datetime.datetime.now().day


@function('DOW')
class DOWFunction(Function):
    MIN_ARGS = MAX_ARGS = 0

    def get_deps(self) -> Set[str]:
        return {'time'}

    def eval(self) -> CorePortValue:
        return datetime.datetime.now().weekday()


@function('HOUR')
class HourFunction(Function):
    MIN_ARGS = MAX_ARGS = 0

    def get_deps(self) -> Set[str]:
        return {'time'}

    def eval(self) -> CorePortValue:
        return datetime.datetime.now().hour


@function('MINUTE')
class MinuteFunction(Function):
    MIN_ARGS = MAX_ARGS = 0

    def get_deps(self) -> Set[str]:
        return {'time'}

    def eval(self) -> CorePortValue:
        return datetime.datetime.now().minute


@function('SECOND')
class SecondFunction(Function):
    MIN_ARGS = MAX_ARGS = 0

    def get_deps(self) -> Set[str]:
        return {'time'}

    def eval(self) -> CorePortValue:
        return datetime.datetime.now().second


@function('HMSINTERVAL')
class HMSIntervalFunction(Function):
    MIN_ARGS = 4
    MAX_ARGS = 6

    def get_deps(self) -> Set[str]:
        return {'time'}

    def eval(self) -> CorePortValue:
        now = datetime.datetime.now()

        if len(self.args) >= 6:
            start_h = self.args[0].eval()
            start_m = self.args[1].eval()
            start_s = self.args[2].eval()
            stop_h = self.args[3].eval()
            stop_m = self.args[4].eval()
            stop_s = self.args[5].eval()

            if not (0 <= start_h <= 23):
                raise InvalidArgument(1, start_h)

            if not (0 <= start_m <= 59):
                raise InvalidArgument(2, start_m)

            if not (0 <= start_s <= 59):
                raise InvalidArgument(3, start_s)

            if not (0 <= stop_h <= 23):
                raise InvalidArgument(4, stop_h)

            if not (0 <= stop_m <= 59):
                raise InvalidArgument(5, stop_m)

            if not (0 <= stop_s <= 59):
                raise InvalidArgument(6, stop_s)

            start_time = datetime.time(start_h, start_m, start_s)
            stop_time = datetime.time(stop_h, stop_m, stop_s)

        else:  # Assuming 4
            start_h = self.args[0].eval()
            start_m = self.args[1].eval()
            stop_h = self.args[2].eval()
            stop_m = self.args[3].eval()

            if not (0 <= start_h <= 23):
                raise InvalidArgument(1, start_h)

            if not (0 <= start_m <= 59):
                raise InvalidArgument(2, start_m)

            if not (0 <= stop_h <= 23):
                raise InvalidArgument(3, stop_h)

            if not (0 <= stop_m <= 59):
                raise InvalidArgument(4, stop_m)

            start_time = datetime.time(start_h, start_m, 00)
            stop_time = datetime.time(stop_h, stop_m, 59)

        start_dt = datetime.datetime.combine(now.date(), start_time)
        stop_dt = datetime.datetime.combine(now.date(), stop_time)

        return start_dt <= now <= stop_dt


# Import core.ports after defining Expression, because core.ports.BasePort depends on Expression.
from qtoggleserver.core import ports as core_ports  # noqa: E402


class PortValue(Expression):
    def __init__(self, port_id: str) -> None:
        self.port_id: str = port_id

    def __str__(self) -> str:
        return f'${self.port_id}'

    def get_deps(self) -> Set[str]:
        return {f'${self.port_id}'}

    def get_port(self) -> core_ports.BasePort:
        return core_ports.get(self.port_id)

    def eval(self) -> CorePortValue:
        port = self.get_port()
        if not port:
            raise IncompleteExpression(f'Unknown port {self.port_id}')

        if not port.is_enabled():
            raise IncompleteExpression(f'{port} is disabled')

        value = port.get_value()
        if value is None:
            raise IncompleteExpression(f'Value of port {port} is undefined')

        return float(value)

    @staticmethod
    def parse(self_port_id: Optional[str], sexpression: str) -> Expression:
        sexpression = sexpression.strip()
        port_id = sexpression.strip('$')

        if port_id:
            return PortValue(port_id)

        else:
            return SelfPortValue(self_port_id)


class SelfPortValue(PortValue):
    def __str__(self) -> str:
        return '$'


def parse(self_port_id: Optional[str], sexpression: str) -> Expression:
    sexpression = sexpression.strip()
    if sexpression.startswith('$'):
        return PortValue.parse(self_port_id, sexpression)

    elif sexpression.count('('):
        return Function.parse(self_port_id, sexpression)

    else:
        return Constant.parse(self_port_id, sexpression)


async def check_loops(port: core_ports.BasePort, expression: Expression) -> None:
    seen_ports = {port}

    async def check_loops_rec(level: int, e: Expression) -> int:
        if isinstance(e, PortValue):
            p = e.get_port()
            if not p:
                return 0

            # A loop is detected when we stumble upon the initial port at a level deeper than 1
            if port is p and level > 1:
                return level

            # Avoid visiting the same port twice
            if p in seen_ports:
                return 0

            seen_ports.add(p)

            expr = await p.get_expression()
            if expr:
                lv = await check_loops_rec(level + 1, expr)
                if lv:
                    return lv

            return 0

        elif isinstance(e, Function):
            for arg in e.args:
                lv = await check_loops_rec(level, arg)
                if lv:
                    return lv

        return 0

    if await check_loops_rec(1, expression) > 1:
        raise CircularDependency(f'{port} is recursively referred')
