import json
import math

from datetime import date, datetime
from enum import StrEnum
from typing import Any, cast

import jsonpointer


JSON_CONTENT_TYPE = "application/json; charset=utf-8"

TYPE_FIELD = "__t"
VALUE_FIELD = "__v"
DATE_FORMAT = "%Y-%m-%d"
DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"
DATE_TYPE = "__d"
DATETIME_TYPE = "__dt"

DATETIME_FORMAT_ISO = "%Y-%m-%dT%H:%M:%SZ"
DATE_FORMAT_ISO = "%Y-%m-%d"
# These are the lengths of the actual formatted output strings, not the format templates
DATETIME_FORMAT_ISO_LEN = 20  # "2024-01-15T14:30:45Z"
DATE_FORMAT_ISO_LEN = 10  # "2024-01-15"


class ExtraTypes(StrEnum):
    """Serialization modes for handling non-standard JSON types in dumps()/loads().

    Attributes:
        NONE: Standard JSON only; date/datetime objects raise TypeError, NaN/Inf replaced with null.
        ISO: Serialize date/datetime as ISO strings; deserialize back. No NaN/Inf allowed.
        EXTENDED: Serialize date/datetime as {__t, __v} objects for roundtrip fidelity. Allow NaN/Inf.
        STR: Fallback serializer that converts any unserializable object to string via str(). Use for
             logging or debugging; not suitable for deserialization.
    """

    NONE = ""
    ISO = "iso"
    EXTENDED = "extended"
    STR = "str"


# Backwards compatibility aliases (deprecated, use ExtraTypes enum instead)
EXTRA_TYPES_NONE = ExtraTypes.NONE
EXTRA_TYPES_ISO = ExtraTypes.ISO
EXTRA_TYPES_EXTENDED = ExtraTypes.EXTENDED
EXTRA_TYPES_STR = ExtraTypes.STR


def _replace_nan_inf_rec(obj: Any, replace_value: Any) -> Any:
    new_obj: Any
    if isinstance(obj, dict):
        new_obj = {}
        for k, v in obj.items():
            if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
                new_obj[k] = replace_value
            else:
                new_obj[k] = _replace_nan_inf_rec(v, replace_value)
    elif isinstance(obj, (list, tuple, set)):
        new_obj = []
        for e in obj:
            if isinstance(e, float) and (math.isnan(e) or math.isinf(e)):
                new_obj.append(replace_value)
            else:
                new_obj.append(_replace_nan_inf_rec(e, replace_value))
    else:
        new_obj = obj

    return new_obj


def _resolve_refs_rec(obj: Any, root_obj: Any) -> Any:
    if isinstance(obj, dict):
        if len(obj.keys()) == 1 and list(obj.keys())[0] == "$ref":
            ref = list(obj.values())[0]
            ref = ref[1:]  # skip starting hash
            return jsonpointer.resolve_pointer(root_obj, ref)

        for k, v in obj.items():
            obj[k] = _resolve_refs_rec(v, root_obj)
    elif isinstance(obj, list):
        for i, e in enumerate(obj):
            obj[i] = _resolve_refs_rec(e, root_obj)

    return obj


def encode_default_json_iso(obj: Any) -> Any:
    """JSON encoder for ISO mode: date/datetime → ISO strings, set/tuple → list."""
    if isinstance(obj, datetime):
        return obj.strftime(DATETIME_FORMAT_ISO)
    elif isinstance(obj, date):
        return obj.strftime(DATE_FORMAT)
    elif isinstance(obj, (set, tuple)):
        return list(obj)
    else:
        raise TypeError()


def encode_default_json_extended(obj: Any) -> Any:
    """JSON encoder for EXTENDED mode: date/datetime → {__t, __v} objects, set/tuple → list."""
    if isinstance(obj, datetime):
        return {TYPE_FIELD: DATETIME_TYPE, VALUE_FIELD: obj.strftime(DATETIME_FORMAT)}
    elif isinstance(obj, date):
        return {TYPE_FIELD: DATE_TYPE, VALUE_FIELD: obj.strftime(DATE_FORMAT)}
    elif isinstance(obj, (set, tuple)):
        return list(obj)
    else:
        raise TypeError()


def encode_default_json_str(obj: Any) -> Any:
    """JSON encoder for STR mode: fallback that serializes any object to string.

    This is a last-resort encoder for logging/debugging. It converts any object
    that can't be serialized by the standard JSON encoder to a string representation.
    Objects serialized this way cannot be deserialized back to their original type.
    """
    return str(obj)


def decode_json_hook_iso(obj: dict) -> Any:
    for k, v in obj.items():
        if isinstance(v, str):
            if len(v) == DATETIME_FORMAT_ISO_LEN:
                try:
                    obj[k] = datetime.strptime(v, DATETIME_FORMAT_ISO)
                except ValueError:
                    pass
            elif len(v) == DATE_FORMAT_ISO_LEN:
                try:
                    obj[k] = datetime.strptime(v, DATE_FORMAT_ISO).date()
                except ValueError:
                    pass

    return obj


def decode_json_hook_extended(obj: dict[Any, Any]) -> Any:
    __t = obj.get(TYPE_FIELD)
    if __t is not None:
        __v = cast(str, obj.get(VALUE_FIELD))
        if __t == DATE_TYPE:
            try:
                return datetime.strptime(__v, DATE_FORMAT).date()
            except ValueError:
                pass
        elif __t == DATETIME_TYPE:
            try:
                return datetime.strptime(__v, DATETIME_FORMAT)
            except ValueError:
                pass

    return obj


def dumps(obj: Any, extra_types: str | ExtraTypes = ExtraTypes.NONE, **kwargs) -> str:
    """Serialize Python object to JSON string.

    Fast-path optimization for primitive types (str, bool, int, float, None).
    For complex objects, delegates to json.dumps() with appropriate encoder.

    Args:
        obj: Object to serialize.
        extra_types: Serialization mode for non-standard JSON types (date/datetime/etc).
            - NONE (default): Standard JSON only; NaN/Inf → null, date/datetime raise TypeError.
            - ISO: date/datetime → ISO strings; no NaN/Inf allowed.
            - EXTENDED: date/datetime → {__t, __v} objects for roundtrip; allow NaN/Inf.
            - STR: Convert any unserializable object to str() (for logging, not deserialization).
        **kwargs: Additional arguments passed to json.dumps().

    Returns:
        JSON string representation.

    Examples:
        >>> dumps({"date": datetime(2024, 1, 1)}, extra_types=ExtraTypes.ISO)
        '{"date": "2024-01-01T00:00:00Z"}'
        >>> dumps({"obj": MyClass()}, extra_types=ExtraTypes.STR)
        '{"obj": "<MyClass instance>"}'
    """
    # Treat primitive types separately to gain just a bit of performance
    if isinstance(obj, str):
        return '"' + obj + '"'
    elif isinstance(obj, bool):
        return ["false", "true"][obj]
    elif isinstance(obj, (int, float)):
        # Handle NaN/Inf based on mode
        if math.isinf(obj) or math.isnan(obj):
            # ISO and NONE modes: convert to null
            # EXTENDED and STR modes: let json.dumps handle it (will produce NaN/Infinity literals)
            if extra_types in (ExtraTypes.ISO, ExtraTypes.NONE, ""):
                return "null"
            else:
                # Fall through to json.dumps for EXTENDED/STR modes
                pass
        else:
            return str(obj)

    if obj is None:
        return "null"

    # Complex types: delegate to json.dumps with appropriate encoder
    if extra_types == ExtraTypes.EXTENDED:
        return json.dumps(obj, default=encode_default_json_extended, allow_nan=True, **kwargs)
    elif extra_types == ExtraTypes.ISO:
        return json.dumps(obj, default=encode_default_json_iso, allow_nan=False, **kwargs)
    elif extra_types == ExtraTypes.STR:
        return json.dumps(obj, default=encode_default_json_str, allow_nan=True, **kwargs)
    else:
        try:
            return json.dumps(obj, allow_nan=False, **kwargs)
        except ValueError:
            # Retry again by replacing Infinity and NaN values with None
            obj = _replace_nan_inf_rec(obj, replace_value=None)
            return json.dumps(obj, allow_nan=False, **kwargs)


def loads(s: str | bytes, resolve_refs: bool = False, extra_types: str | ExtraTypes = ExtraTypes.NONE, **kwargs) -> Any:
    """Deserialize JSON string to Python object.

    Args:
        s: JSON string or bytes to deserialize.
        resolve_refs: If True, resolve JSON references ($ref pointers) in the result.
        extra_types: Deserialization mode for non-standard JSON types.
            - NONE (default): Standard JSON only.
            - ISO: Parse ISO date/datetime strings back to date/datetime objects.
            - EXTENDED: Parse {__t, __v} objects back to date/datetime objects.
            - STR: Not applicable (objects serialized with STR cannot be deserialized).
        **kwargs: Additional arguments passed to json.loads().

    Returns:
        Deserialized Python object.
    """
    if extra_types == ExtraTypes.EXTENDED:
        object_hook = decode_json_hook_extended
    elif extra_types == ExtraTypes.ISO:
        object_hook = decode_json_hook_iso
    else:
        object_hook = None

    obj = json.loads(s, object_hook=object_hook, **kwargs)
    if resolve_refs:
        obj = _resolve_refs_rec(obj, root_obj=obj)

    return obj
