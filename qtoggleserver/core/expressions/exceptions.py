
from qtoggleserver.core.typing import PortValue as CorePortValue


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
