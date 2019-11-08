
import json


def dumps(obj):
    if isinstance(obj, str):
        return '"' + obj + '"'

    elif isinstance(obj, bool):
        return ['false', 'true'][obj]

    elif isinstance(obj, (int, float)):
        return str(obj)

    elif obj is None:
        return 'null'

    else:
        return json.dumps(obj)


def loads(s):
    return json.loads(s)
