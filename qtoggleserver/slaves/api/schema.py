
POST_SLAVE_DEVICES = {
    "type": "object",
    "properties": {
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
        "admin_password": {
            "type": "string",
            "maxLength": 32
        },
        "poll_interval": {
            "type": "number",
            "min": 0,
            "max": 86400
        },
        "listen_enabled": {
            "type": "boolean"
        }
    },
    "additionalProperties": False,
    "required": [
        "scheme",
        "host",
        "port",
        "path",
        "admin_password"
    ]
}

PATCH_SLAVE_DEVICE = {
    "type": "object",
    "properties": {
        "enabled": {
            "type": "boolean"
        },
        "poll_interval": {
            "type": "number",
            "min": 0,
            "max": 86400
        },
        "listen_enabled": {
            "type": "boolean"
        }
    },
    "additionalProperties": False
}

POST_SLAVE_DEVICE_EVENTS = {
    "type": "object",
    "properties": {
        "type": {
            "type": "string"
        },
        "params": {
            "type": "object"
        }
    },
    "additionalProperties": False,
    "required": [
        "type"
    ]
}

PATCH_DISCOVERED_DEVICE = {
    "type": "object",
    "properties": {
        "attrs": {
            "type": "object"
        }
    },
    "additionalProperties": False,
    "required": [
        "attrs"
    ]
}
