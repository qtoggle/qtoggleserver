
import re

from typing import Any, Callable, Optional, Tuple, Union

import jsonschema

from qtoggleserver.core.typing import GenericJSONDict

from . import APIError


POST_RESET = {
    "type": "object",
    "properties": {
        "factory": {
            "type": "boolean"
        }
    },
    "additionalProperties": False,
}

PATCH_FIRMWARE = {
    "type": "object",
    "properties": {
        "version": {
            "type": "string",
            "maxLength": 256
        },
        "url": {
            "type": "string",
            "maxLength": 256
        }
    },
    "additionalProperties": False,
    "anyOf": [
        {
            "required": ["version"]
        },
        {
            "required": ["url"]
        }
    ]
}

PUT_PORTS = {
    "type": "array",
    "items": {
        "type": "object"
    },
    "additionalProperties": True
}

POST_PORTS = {
    "type": "object",
    "properties": {
        "id": {
            "type": "string",
            "pattern": "^[a-zA-Z_][a-zA-Z0-9_.-]{0,63}$"
        },
        "type": {
            "enum": ["boolean", "number"]
        },
        "min": {
            "type": "number"
        },
        "max": {
            "type": "number"
        },
        "integer": {
            "type": "boolean"
        },
        "step": {
            "type": "number"
        },
        "choices": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "value": {
                        "oneOf": [
                            {"type": "boolean"},
                            {"type": "number"}
                        ]
                    },
                    "display_name": {
                        "type": "string",
                        "maxLength": 64
                    }
                },
                "required": ["value"],
                "additionalProperties": False,
            },
            "minItems": 2,
            "maxItems": 256
        },
    },
    "additionalProperties": False,
    "required": [
        "id",
        "type"
    ]
}

PATCH_PORT_SEQUENCE = {
    "type": "object",
    "properties": {
        "values": {
            "type": "array",
            "items": {
                "oneOf": [
                    {"type": "boolean"},
                    {"type": "number"}
                ]
            },
            "minItems": 0,
            "maxItems": 256
        },
        "delays": {
            "type": "array",
            "items": {
                "type": "integer",
                "min": 0,
                "max": 60000
            },
            "minItems": 0,
            "maxItems": 256
        },
        "repeat": {
            "type": "integer",
            "min": 0,
            "max": 65535
        }
    },
    "additionalProperties": False,
    "required": [
        "values",
        "delays",
        "repeat"
    ]
}

PATCH_WEBHOOKS = {
    "type": "object",
    "properties": {
        "enabled": {
            "type": "boolean"
        },
        "scheme": {
            "enum": ["http", "https"]
        },
        "host": {
            "type": "string",
            "maxLength": 256
        },
        "port": {
            "type": "integer",
            "min": 1,
            "max": 65535
        },
        "path": {
            "type": "string",
            "maxLength": 256
        },
        "password": {
            "type": "string",
            "maxLength": 64
        },
        "password_hash": {
            "type": "string",
            "pattern": "^[a-f0-9]{64}$"
        },
        "timeout": {
            "type": "integer",
            "minimum": 1,
            "maximum": 3600
        },
        "retries": {
            "type": "integer",
            "minimum": 0,
            "maximum": 10
        }
    },
    "additionalProperties": False,
    "required": [
        "enabled",
        "scheme",
        "host",
        "port",
        "path",
        "timeout",
        "retries"
    ]
}

PATCH_REVERSE = {
    "type": "object",
    "properties": {
        "enabled": {
            "type": "boolean"
        },
        "scheme": {
            "enum": ["http", "https"]
        },
        "host": {
            "type": "string",
            "maxLength": 256
        },
        "port": {
            "type": "integer",
            "min": 1,
            "max": 65535
        },
        "path": {
            "type": "string",
            "maxLength": 256
        },
        "password": {
            "type": "string",
            "maxLength": 64
        },
        "password_hash": {
            "type": "string",
            "pattern": "^[a-f0-9]{64}$"
        },
        "device_id": {
            "type": "string",
            "pattern": "^[a-zA-Z0-9]{1,64}"
        },
        "timeout": {
            "type": "integer",
            "minimum": 1,
            "maximum": 3600
        },
    },
    "additionalProperties": False,
    "required": [
        "enabled",
        "scheme",
        "host",
        "port",
        "path",
        "device_id",
        "timeout"
    ]
}


def _validate_schema(json: Any, schema: GenericJSONDict) -> Optional[Tuple[str, Optional[str]]]:
    try:
        jsonschema.Draft4Validator(schema=schema).validate(json)
        return None

    except jsonschema.ValidationError as e:
        try:
            field = e.path.pop()
            return 'invalid', field

        except Exception:
            try:
                field = re.match(r'\'(\w+)\' is a required property', e.message).group(1)
                return 'missing', field

            except Exception:
                try:
                    field = re.match(r'Additional properties are not allowed \(u?\'(\w+)\'.*', e.message).group(1)
                    return 'unexpected', field

                except Exception:
                    return 'invalid', None


def validate(
    params: Any, schema: GenericJSONDict,
    invalid_field_code: Union[str, Callable] = 'invalid-field',
    unexpected_field_code: Union[str, Callable] = 'invalid-request',
    missing_field_code: Union[str, Callable] = 'missing-field',
    invalid_request_code: str = 'invalid-request',
    invalid_field_name: str = 'field',
    unexpected_field_name: str = 'field',
    missing_field_name: str = 'field'
) -> None:

    validation_error = _validate_schema(params, schema)
    if validation_error:
        error, field = validation_error
        if error == 'invalid':
            if field:
                if callable(invalid_field_code):
                    invalid_field_code = invalid_field_code(field)

                raise APIError(400, invalid_field_code, **{invalid_field_name: field})

            else:
                raise APIError(400, invalid_request_code)

        elif error == 'missing':
            if callable(missing_field_code):
                missing_field_code = missing_field_code(field)

            raise APIError(400, missing_field_code, **{missing_field_name: field})

        elif error == 'unexpected':
            if callable(unexpected_field_code):
                unexpected_field_code = unexpected_field_code(field)

            raise APIError(400, unexpected_field_code, **{unexpected_field_name: field})

        else:
            raise APIError(400, 'invalid-request')
