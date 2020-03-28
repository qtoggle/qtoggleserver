
import datetime
import json

from typing import Any, Union

import jsonpointer


JSON_CONTENT_TYPE = 'application/json; charset=utf-8'

TYPE_FIELD = '__t'
VALUE_FIELD = '__v'
DATE_FORMAT = '%Y-%m-%d'
DATETIME_FORMAT = '%Y-%m-%dT%H:%M:%S.%fZ'
DATE_TYPE = '__d'
DATETIME_TYPE = '__dt'


def _resolve_refs_rec(obj: Any, root_obj: Any) -> Any:
    if isinstance(obj, dict):
        if len(obj.keys()) == 1 and list(obj.keys())[0] == '$ref':
            ref = list(obj.values())[0]
            ref = ref[1:]  # Skip starting hash
            return jsonpointer.resolve_pointer(root_obj, ref)

        for k, v in obj.items():
            obj[k] = _resolve_refs_rec(v, root_obj)

    elif isinstance(obj, list):
        for i, e in enumerate(obj):
            obj[i] = _resolve_refs_rec(e, root_obj)

    return obj


def _encode_default_json(obj: Any) -> Any:
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


def _decode_json_hook(obj: dict) -> Any:
    __t = obj.get(TYPE_FIELD)
    if __t is not None:
        __v = obj.get(VALUE_FIELD)
        if __t == DATE_TYPE:
            try:
                return datetime.datetime.strptime(__v, DATE_FORMAT)

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
        return str(obj)

    elif obj is None:
        return 'null'

    else:
        return json.dumps(obj, default=_encode_default_json if allow_extended_types else None, **kwargs)


def loads(s: Union[str, bytes], resolve_refs: bool = False, allow_extended_types: bool = False, **kwargs) -> Any:
    obj = json.loads(s, object_hook=_decode_json_hook if allow_extended_types else None, **kwargs)

    if resolve_refs:
        obj = _resolve_refs_rec(obj, root_obj=obj)

    return obj
