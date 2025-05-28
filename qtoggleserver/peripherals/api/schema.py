POST_PERIPHERALS = {
    "type": "object",
    "properties": {
        "driver": {
            "type": "string",
        },
        "name": {"oneOf": [{"type": "string", "pattern": "^[a-zA-Z_][a-zA-Z0-9_.-]{0,63}$"}, {"type": "null"}]},
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
            "id": {"oneOf": [{"type": "string", "pattern": "^[a-zA-Z_][a-zA-Z0-9_.-]{0,63}$"}, {"type": "null"}]},
        },
        "additionalProperties": True,
        "required": [
            "driver",
        ],
    },
}
