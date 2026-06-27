import re


def deep_update(dst: dict, src: dict) -> dict:
    for k, v in src.items():
        if k in dst and isinstance(dst[k], dict) and isinstance(v, dict):
            deep_update(dst[k], v)
        else:
            dst[k] = v
    return dst


def to_underscore_case(text: str) -> str:
    """
    Transform title case or camel case to underscore case.
    """

    # Replace spaces with underscores
    s = text.replace(" ", "_")

    # Insert underscore before uppercase letters following lowercase letters/digits
    s = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s)

    # Handle consecutive uppercase letters followed by lowercase (e.g., "XMLParser")
    s = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", s)

    return s.lower()
