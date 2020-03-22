
from qtoggleserver.core.typing import PortValue as CorePortValue


class ExpressionException(Exception):
    pass


class InvalidExpression(ExpressionException):
    pass


class InvalidArgument(ExpressionException):
    def __init__(self, arg_no: int, value: CorePortValue) -> None:
        self.arg_no: int = arg_no
        self.value: CorePortValue = value

    def __str__(self) -> str:
        return f'invalid argument {self.arg_no}: {self.value}'


class CircularDependency(ExpressionException):
    pass


class IncompleteExpression(ExpressionException):
    pass


class EvalSkipped(ExpressionException):
    pass
