POST_PERIPHERALS = {
    "type": "object",
    "properties": {
        "driver": {
            "type": "string",
        },
        "name": {
            "type": "string",
            "pattern": "^[a-zA-Z_][a-zA-Z0-9_.-]{0,63}$"
        },
    },
    "additionalProperties": True,
    "required": [
        "driver",
    ]
}

PUT_PERIPHERALS = {
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "driver": {
                "type": "string",
            },
            "name": {
                "type": "string",
                "pattern": "^[a-zA-Z_][a-zA-Z0-9_.-]{0,63}$"
            },
        },
        "additionalProperties": True,
        "required": [
            "driver",
        ]
    },
}
