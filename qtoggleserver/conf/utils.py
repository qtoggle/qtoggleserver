
import types


def obj_to_dict(obj):
    d = {}
    for k, v in obj.__dict__.items():
        if k.startswith('__') or isinstance(v, types.ModuleType):
            continue

        if isinstance(v, type):
            v = obj_to_dict(v)

        d[k] = v

    return d


def update_obj_from_dict(obj, d):
    for k, v in d.items():
        ov = getattr(obj, k, None)
        if isinstance(ov, type):
            update_obj_from_dict(ov, v)

        elif isinstance(ov, types.ModuleType):
            continue

        else:
            setattr(obj, k, v)
