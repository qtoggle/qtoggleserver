def deep_update(dst: dict, src: dict) -> dict:
    for k, v in src.items():
        if k in dst and isinstance(dst[k], dict) and isinstance(v, dict):
            deep_update(dst[k], v)
        else:
            dst[k] = v
    return dst
