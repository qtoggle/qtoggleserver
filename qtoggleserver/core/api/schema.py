
import jsonschema
import re

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

POST_PORT_SEQUENCE = {
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
        "delays"
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
            "min": 0,
            "max": 65535
        },
        "path": {
            "type": "string",
            "maxLength": 256
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
            "min": 0,
            "max": 65535
        },
        "path": {
            "type": "string",
            "maxLength": 256
        },
        "device_id": {
            "type": "string",
            "pattern": "^[a-zA-Z0-9]{1,32}"
        },
        "password": {
            "type": "string",
            "maxLength": 32
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
        "path"
    ]
}


def _validate_schema(json, schema):
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


def validate(params, schema, invalid_field_msg='invalid field: {field}', unexpected_field_msg='invalid request',
             invalid_request_msg='invalid request'):

    validation_error = _validate_schema(params, schema)
    if validation_error:
        error, field = validation_error
        if error == 'invalid':
            if field:
                if callable(invalid_field_msg):
                    invalid_field_msg = invalid_field_msg(field)

                raise APIError(400, invalid_field_msg.format(field=field))

            else:
                raise APIError(400, invalid_request_msg)

        elif error == 'missing':
            raise APIError(400, 'missing field: {}'.format(field))

        elif error == 'unexpected':
            if callable(unexpected_field_msg):
                unexpected_field_msg = unexpected_field_msg(field)

            raise APIError(400, unexpected_field_msg.format(field=field))

        else:
            raise APIError(400, 'invalid request')
