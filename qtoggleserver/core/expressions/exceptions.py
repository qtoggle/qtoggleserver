
from qtoggleserver.core.typing import PortValue as CorePortValue
from qtoggleserver.core.typing import GenericJSONDict


class ExpressionException(Exception):
    pass


class ExpressionParseError(ExpressionException):
    def to_json(self) -> GenericJSONDict:
        return {
            'reason': 'parse-error'
        }


class UnknownFunction(ExpressionParseError):
    def __init__(self, name: str, pos: int) -> None:
        self.name: str = name
        self.pos: int = pos

        super().__init__(f'Unknown function "{name}"')

    def to_json(self) -> GenericJSONDict:
        return {
            'reason': 'unknown-function',
            'token': self.name,
            'pos': self.pos
        }


class InvalidNumberOfArguments(ExpressionParseError):
    def __init__(self, name: str, pos: int) -> None:
        self.name: str = name
        self.pos: int = pos

        super().__init__(f'Invalid number of arguments for function "{name}"')

    def to_json(self) -> GenericJSONDict:
        return {
            'reason': 'invalid-number-of-arguments',
            'token': self.name,
            'pos': self.pos
        }


class InvalidArgumentKind(ExpressionParseError):
    def __init__(self, name: str, pos: int, num: int) -> None:
        self.name: str = name
        self.pos: int = pos
        self.num: int = num

        super().__init__(f'Invalid argument {num} kind for "{name}" at position {pos}')

    def to_json(self) -> GenericJSONDict:
        return {
            'reason': 'invalid-argument-kind',
            'token': self.name,
            'pos': self.pos,
            'num': self.num
        }


class UnbalancedParentheses(ExpressionParseError):
    def __init__(self, pos: int) -> None:
        self.pos: int = pos

        super().__init__('Unbalanced parentheses')

    def to_json(self) -> GenericJSONDict:
        return {
            'reason': 'unbalanced-parentheses',
            'pos': self.pos
        }


class UnexpectedEnd(ExpressionParseError):
    def __init__(self) -> None:
        super().__init__('Expression is unterminated')

    def to_json(self) -> GenericJSONDict:
        return {
            'reason': 'unexpected-end'
        }


class CircularDependency(ExpressionParseError):
    def __init__(self, port_id: str) -> None:
        super().__init__(f'Expression creates a dependency loop via port "{port_id}"')

    def to_json(self) -> GenericJSONDict:
        return {
            'reason': 'circular-dependency'
        }


class ExternalDependency(ExpressionParseError):
    def __init__(self, port_id: str, pos: int) -> None:
        self.port_id = port_id
        self.pos = pos

        super().__init__(f'External dependency on port "{port_id}"')

    def to_json(self) -> GenericJSONDict:
        return {
            'reason': 'external-dependency',
            'token': self.port_id,
            'pos': self.pos
        }


class UnexpectedCharacter(ExpressionParseError):
    def __init__(self, c: str, pos: int) -> None:
        self.c = c
        self.pos: int = pos

        super().__init__(f'Unexpected character "{c}" at position {pos}')

    def to_json(self) -> GenericJSONDict:
        return {
            'reason': 'unexpected-character',
            'token': self.c,
            'pos': self.pos
        }


class EmptyExpression(ExpressionParseError):
    def __init__(self) -> None:
        super().__init__('Expression is empty')

    def to_json(self) -> GenericJSONDict:
        return {
            'reason': 'empty-expression'
        }


class ExpressionEvalError(ExpressionException):
    pass


class InvalidArgumentValue(ExpressionEvalError):
    def __init__(self, arg_no: int, value: CorePortValue) -> None:
        self.arg_no: int = arg_no
        self.value: CorePortValue = value

        super().__init__(f'Invalid argument {self.arg_no}: {self.value}')


class UnknownPortId(ExpressionEvalError):
    def __init__(self, port_id: str) -> None:
        self.port_id = port_id

        super().__init__(f'Unknown port "{port_id}"')


class DisabledPort(ExpressionEvalError):
    def __init__(self, port_id: str) -> None:
        self.port_id = port_id

        super().__init__(f'Port "{port_id}" is disabled')


class PortValueUnavailable(ExpressionEvalError):
    def __init__(self, port_id: str) -> None:
        self.port_id = port_id

        super().__init__(f'Port "{port_id}" value is undefined')


class ExpressionArithmeticError(ExpressionEvalError):
    def __init__(self) -> None:
        super().__init__('Expression arithmetic error')


class EvalSkipped(ExpressionEvalError):
    def __init__(self) -> None:
        super().__init__('Evaluation skipped')
