import datetime
import json
import math

from typing import Any, Union

import jsonpointer


JSON_CONTENT_TYPE = 'application/json; charset=utf-8'

TYPE_FIELD = '__t'
VALUE_FIELD = '__v'
DATE_FORMAT = '%Y-%m-%d'
DATETIME_FORMAT = '%Y-%m-%dT%H:%M:%S.%fZ'
DATE_TYPE = '__d'
DATETIME_TYPE = '__dt'


def _replace_nan_inf_rec(obj: Any, replace_value: Any) -> Any:
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
        if len(obj.keys()) == 1 and list(obj.keys())[0] == '$ref':
            ref = list(obj.values())[0]
            ref = ref[1:]  # skip starting hash
            return jsonpointer.resolve_pointer(root_obj, ref)

        for k, v in obj.items():
            obj[k] = _resolve_refs_rec(v, root_obj)
    elif isinstance(obj, list):
        for i, e in enumerate(obj):
            obj[i] = _resolve_refs_rec(e, root_obj)

    return obj


def encode_default_json(obj: Any) -> Any:
    if isinstance(obj, datetime.datetime):
        return {
            TYPE_FIELD: DATETIME_TYPE,
            VALUE_FIELD: obj.strftime(DATETIME_FORMAT)
        }
    elif isinstance(obj, datetime.date):
        return {
            TYPE_FIELD: DATE_TYPE,
            VALUE_FIELD: obj.strftime(DATE_FORMAT)
        }
    elif isinstance(obj, (set, tuple)):
        return list(obj)
    else:
        raise TypeError()


def decode_json_hook(obj: dict) -> Any:
    __t = obj.get(TYPE_FIELD)
    if __t is not None:
        __v = obj.get(VALUE_FIELD)
        if __t == DATE_TYPE:
            try:
                return datetime.datetime.strptime(__v, DATE_FORMAT).date()
            except ValueError:
                pass
        elif __t == DATETIME_TYPE:
            try:
                return datetime.datetime.strptime(__v, DATETIME_FORMAT)
            except ValueError:
                pass

    return obj


def dumps(obj: Any, allow_extended_types: bool = False, **kwargs) -> str:
    # Treat primitive types separately to gain just a bit of performance
    if isinstance(obj, str):
        return '"' + obj + '"'
    elif isinstance(obj, bool):
        return ['false', 'true'][obj]
    elif isinstance(obj, (int, float)):
        if math.isinf(obj) or math.isnan(obj):
            return 'null'

        return str(obj)
    elif obj is None:
        return 'null'
    else:
        if allow_extended_types:
            return json.dumps(obj, default=encode_default_json, allow_nan=True, **kwargs)
        else:
            try:
                return json.dumps(obj, allow_nan=False, **kwargs)
            except ValueError:
                # Retry again by replacing Infinity and NaN values with None
                obj = _replace_nan_inf_rec(obj, replace_value=None)
                return json.dumps(obj, allow_nan=False, **kwargs)


def loads(s: Union[str, bytes], resolve_refs: bool = False, allow_extended_types: bool = False, **kwargs) -> Any:
    object_hook = decode_json_hook if allow_extended_types else None
    obj = json.loads(s, object_hook=object_hook, **kwargs)

    if resolve_refs:
        obj = _resolve_refs_rec(obj, root_obj=obj)

    return obj
