
import datetime
import json

from typing import Any, Callable, Union

import jsonpointer


JSON_CONTENT_TYPE = 'application/json; charset=utf-8'


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


def _make_json_encoder(date_format: str = '%Y-%m-%d', datetime_format: str = '%Y-%m-%dT%H:%M:%SZ') -> Callable:
    def encode_default_json(obj: Any) -> str:
        if isinstance(obj, datetime.datetime):
            return obj.strftime(datetime_format)

        elif isinstance(obj, datetime.date):
            return obj.strftime(date_format)

        elif isinstance(obj, (set, tuple)):
            return json.dumps(list(obj), default=encode_default_json)

    return encode_default_json


def dumps(obj: Any) -> str:
    if isinstance(obj, str):
        return '"' + obj + '"'

    elif isinstance(obj, bool):
        return ['false', 'true'][obj]

    elif isinstance(obj, (int, float)):
        return str(obj)

    elif obj is None:
        return 'null'

    else:
        return json.dumps(obj, default=_make_json_encoder())


def loads(s: Union[str, bytes], resolve_refs: bool = False) -> Any:
    obj = json.loads(s)

    if resolve_refs:
        obj = _resolve_refs_rec(obj, root_obj=obj)

    return obj
