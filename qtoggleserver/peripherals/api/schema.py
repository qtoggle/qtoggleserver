POST_PERIPHERALS = {
    "type": "object",
    "properties": {
        "driver": {
            "type": "string",
        },
        "name": {"oneOf": [{"type": "string", "pattern": "^[a-zA-Z_][a-zA-Z0-9_.-]{0,63}$"}, {"type": "null"}]},
        "display_name": {"type": "string", "maxLength": 64},
        "id": {"oneOf": [{"type": "string", "pattern": "^[a-zA-Z_][a-zA-Z0-9_.-]{0,63}$"}, {"type": "null"}]},
        "force_enabled": {"oneOf": [{"type": "boolean"}, {"type": "null"}]},
        "params": {"type": "object"},
    },
    "additionalProperties": True,
    "required": [
        "driver",
    ],
}

PATCH_PERIPHERAL = {
    "type": "object",
    "properties": {
        "driver": {
            "type": "string",
        },
        "name": {"oneOf": [{"type": "string", "pattern": "^[a-zA-Z_][a-zA-Z0-9_.-]{0,63}$"}, {"type": "null"}]},
        "display_name": {"type": "string", "maxLength": 64},
        "force_enabled": {"oneOf": [{"type": "boolean"}, {"type": "null"}]},
        "params": {"type": "object"},
    },
    "additionalProperties": True,
    "required": [
        "driver",
    ],
}

PUT_PERIPHERALS = {
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "driver": {
                "type": "string",
            },
            "name": {"oneOf": [{"type": "string", "pattern": "^[a-zA-Z_][a-zA-Z0-9_.-]{0,63}$"}, {"type": "null"}]},
            "display_name": {"type": "string", "maxLength": 64},
            "id": {"oneOf": [{"type": "string", "pattern": "^[a-zA-Z_][a-zA-Z0-9_.-]{0,63}$"}, {"type": "null"}]},
            "params": {"type": "object"},
            "force_enabled": {"oneOf": [{"type": "boolean"}, {"type": "null"}]},
            "static": {"type": "boolean"},
        },
        "additionalProperties": True,
        "required": [
            "driver",
        ],
    },
}
