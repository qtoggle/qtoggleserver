
import abc
import asyncio
import re

from typing import Callable, List, Optional, Set

from . import exceptions
from . import parse
from .base import Expression, Evaluated
from .literalvalues import LiteralValue
from .port import PortValue


FUNCTIONS = {}


def function(name: str) -> Callable:
    def decorator(func_class: type) -> type:
        func_class.NAME = name
        FUNCTIONS[name] = func_class

        return func_class

    return decorator


class Function(Expression, metaclass=abc.ABCMeta):
    NAME = None
    MIN_ARGS = None
    MAX_ARGS = None
    DEPS = []
    ARG_KINDS = []
    ENABLED = True

    def __init__(self, args: List[Expression]) -> None:
        self.args: List[Expression] = args

    def __str__(self) -> str:
        s = getattr(self, '_str', None)
        if s is None:
            args_str = ', '.join(str(e) for e in self.args)
            self._str = s = f'{self.NAME}({args_str})'

        return s

    def get_deps(self) -> Set[str]:
        deps = set(self.DEPS)
        for arg in self.args:
            deps |= arg.get_deps()

        return deps

    async def eval_args(self) -> List[Evaluated]:
        return list(await asyncio.gather(*(a.eval() for a in self.args)))

    @classmethod
    def validate_arg_kinds(cls, args: List[Expression], pos_list: List[int]) -> None:
        for i, arg in enumerate(args):
            try:
                kind = cls.ARG_KINDS[i]

            except IndexError:
                kind = (LiteralValue, PortValue, Function)

            if not isinstance(arg, kind):
                raise exceptions.InvalidArgumentKind(cls.NAME, pos_list[i], i + 1)

    @staticmethod
    def parse(self_port_id: Optional[str], sexpression: str, pos: int) -> Expression:
        # Remove leading whitespace
        while sexpression and sexpression[0].isspace():
            sexpression = sexpression[1:]
            pos += 1

        # Remove trailing whitespace
        while sexpression and sexpression[-1].isspace():
            sexpression = sexpression[:-1]

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
                    raise exceptions.UnexpectedCharacter(c, pos + i)

                level += 1

            elif c == ')':
                if level == 0:
                    raise exceptions.UnbalancedParentheses(pos + i)

                elif level == 1:
                    if p_end is None:
                        p_end = i

                    else:
                        raise exceptions.UnbalancedParentheses(pos + i)

                level -= 1

            elif (c == ',') and (level == 1):
                sarg = sexpression[(p_last_comma or p_start) + 1: i]
                spos = (p_last_comma or p_start) + 1
                if not sarg.strip():
                    raise exceptions.UnexpectedCharacter(c, pos + spos + len(sarg))

                sargs.append((sarg, spos))
                p_last_comma = i

            elif (p_start is not None) and (level == 0) and not c.isspace():
                raise exceptions.UnexpectedCharacter(c, pos + i)

        if (p_start is None) or (p_end is None) or (p_start > p_end) or (level != 0):
            raise exceptions.UnexpectedEnd()

        if p_end - p_start > 1:
            sarg = sexpression[(p_last_comma or p_start) + 1: p_end]
            spos = (p_last_comma or p_start) + 1
            if not sarg.strip():
                raise exceptions.UnexpectedCharacter(')', pos + spos + len(sarg))

            sargs.append((sarg, spos))

        func_name = sexpression[:p_start].strip()
        m = re.search(r'[^a-zA-Z0-9_]', func_name)
        if m:
            p = m.start()
            raise exceptions.UnexpectedCharacter(func_name[p], p + pos)

        func_class = FUNCTIONS.get(func_name)
        if func_class is None:
            raise exceptions.UnknownFunction(func_name, pos)

        if not func_class.ENABLED or callable(func_class.ENABLED) and not func_class.ENABLED():
            raise exceptions.UnknownFunction(func_name, pos)

        if func_class.MIN_ARGS is not None and len(sargs) < func_class.MIN_ARGS:
            raise exceptions.InvalidNumberOfArguments(func_name, pos)

        if func_class.MAX_ARGS is not None and len(sargs) > func_class.MAX_ARGS:
            raise exceptions.InvalidNumberOfArguments(func_name, pos)

        args = [parse(self_port_id, sarg, pos + spos) for (sarg, spos) in sargs]
        func_class.validate_arg_kinds(args, [pos + spos + 1 for (_, spos) in sargs])

        return func_class(args)


# These imports are here just because we need all modules to be imported, so that @function decorator registers all
# defined functions.

from .arithmetic import function as _
from .logic import function as _
from .bitwise import function as _
from .comparison import function as _
from .sign import function as _
from .aggregation import function as _
from .rounding import function as _
from .time import function as _
from .date import function as _
from .timeprocessing import function as _
from .various import function as _
