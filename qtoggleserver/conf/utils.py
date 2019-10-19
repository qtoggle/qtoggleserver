
import pyhocon
import types


config_factory = pyhocon.ConfigFactory()


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


def config_from_file(file):
    return config_factory.parse_file(file)


def config_from_dict(d):
    return config_factory.from_dict(d)


def config_to_dict(config):
    return config.as_plain_ordered_dict()


def config_merge(config1, config2):
    return pyhocon.ConfigTree.merge_configs(config1, config2)
