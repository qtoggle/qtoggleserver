import inspect
import re
import sys
import types


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


def stack_to_traceback(skip: int = 1) -> types.TracebackType | None:
    """
    Convert `inspect.stack()` into a `types.TracebackType` object. skip=1 omits this helper function itself from the
    traceback."""

    frames = inspect.stack()[skip:]

    tb = None
    for frame_info in frames:
        tb = types.TracebackType(
            tb_next=tb,
            tb_frame=frame_info.frame,
            tb_lasti=frame_info.frame.f_lasti,
            tb_lineno=frame_info.lineno,
        )
    return tb


def append_traceback(exc: Exception | None = None, tb: types.TracebackType | None = None) -> Exception:
    """Use inside an `except` block to return the current exception (or `exc`) with `tb` traceback appended to its own
    traceback."""

    if exc is None:
        exc = sys.exc_info()[1]
        if exc is None:
            raise AssertionError("Use this function inside an `except` block")
    if not tb:
        tb = stack_to_traceback(skip=3)

    # Walk to the last frame of tb1, rebuilding the chain
    # because tb_next is read-only on existing traceback objects
    frames = []
    cur = tb
    while cur is not None:
        frames.append((cur.tb_frame, cur.tb_lasti, cur.tb_lineno))
        cur = cur.tb_next
    # Rebuild from the tail, linking to tb2
    result = exc.__traceback__
    for frame, lasti, lineno in reversed(frames):
        result = types.TracebackType(
            tb_next=result,
            tb_frame=frame,
            tb_lasti=lasti,
            tb_lineno=lineno,
        )

    return exc.with_traceback(result)
