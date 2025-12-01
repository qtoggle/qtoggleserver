from qtoggleserver.core.typing import GenericJSONDict
from qtoggleserver.core.typing import PortValue as CorePortValue


class ExpressionException(Exception):
    pass


class ExpressionParseError(ExpressionException):
    def to_json(self) -> GenericJSONDict:
        return {"reason": "parse-error"}


class UnknownFunction(ExpressionParseError):
    def __init__(self, name: str, pos: int) -> None:
        self.name: str = name
        self.pos: int = pos

        super().__init__(f'Unknown function "{name}"')

    def to_json(self) -> GenericJSONDict:
        return {"reason": "unknown-function", "token": self.name, "pos": self.pos}


class InvalidNumberOfArguments(ExpressionParseError):
    def __init__(self, name: str, pos: int) -> None:
        self.name: str = name
        self.pos: int = pos

        super().__init__(f'Invalid number of arguments for function "{name}"')

    def to_json(self) -> GenericJSONDict:
        return {"reason": "invalid-number-of-arguments", "token": self.name, "pos": self.pos}


class InvalidArgumentKind(ExpressionParseError):
    def __init__(self, name: str, pos: int, num: int) -> None:
        self.name: str = name
        self.pos: int = pos
        self.num: int = num

        super().__init__(f'Invalid argument {num} kind for "{name}" at position {pos}')

    def to_json(self) -> GenericJSONDict:
        return {"reason": "invalid-argument-kind", "token": self.name, "pos": self.pos, "num": self.num}


class UnbalancedParentheses(ExpressionParseError):
    def __init__(self, pos: int) -> None:
        self.pos: int = pos

        super().__init__("Unbalanced parentheses")

    def to_json(self) -> GenericJSONDict:
        return {"reason": "unbalanced-parentheses", "pos": self.pos}


class UnexpectedEnd(ExpressionParseError):
    def __init__(self) -> None:
        super().__init__("Expression is unterminated")

    def to_json(self) -> GenericJSONDict:
        return {"reason": "unexpected-end"}


class NonSelfDependency(ExpressionParseError):
    def __init__(self, port_id: str, pos: int) -> None:
        self.port_id = port_id
        self.pos = pos

        super().__init__(f'Non-self dependency on port "{port_id}"')

    def to_json(self) -> GenericJSONDict:
        return {"reason": "non-self-dependency", "token": self.port_id, "pos": self.pos}


class UnexpectedCharacter(ExpressionParseError):
    def __init__(self, c: str, pos: int) -> None:
        self.c = c
        self.pos: int = pos

        super().__init__(f'Unexpected character "{c}" at position {pos}')

    def to_json(self) -> GenericJSONDict:
        return {"reason": "unexpected-character", "token": self.c, "pos": self.pos}


class EmptyExpression(ExpressionParseError):
    def __init__(self) -> None:
        super().__init__("Expression is empty")

    def to_json(self) -> GenericJSONDict:
        return {"reason": "empty"}


class ExpressionEvalException(ExpressionException):
    pass


class ValueUnavailable(ExpressionEvalException):
    def __init__(self, msg: str | None = None) -> None:
        super().__init__(msg or "Value is unavailable")


class InvalidArgumentValue(ExpressionEvalException):
    def __init__(self, arg_no: int, value: CorePortValue) -> None:
        self.arg_no: int = arg_no
        self.value: CorePortValue = value

        super().__init__(f"Invalid argument {self.arg_no}: {self.value}")


class PortValueUnavailable(ValueUnavailable):
    MSG = 'Port "%s" is unavailable'

    def __init__(self, port_id: str) -> None:
        self.port_id = port_id

        super().__init__(self.MSG % port_id)


class UnknownPortId(PortValueUnavailable):
    MSG = 'Unknown port "%s"'


class DisabledPort(PortValueUnavailable):
    MSG = 'Port "%s" is disabled'


class ExpressionArithmeticError(ExpressionEvalException):
    def __init__(self) -> None:
        super().__init__("Expression arithmetic error")


class RealDateTimeUnavailable(ValueUnavailable):
    def __init__(self) -> None:
        super().__init__("Real date/time is unavailable")
