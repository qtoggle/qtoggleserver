from typing import Any, cast

from jinja2 import Environment, Template
from jinja2.nativetypes import NativeEnvironment, NativeTemplate


__all__ = [
    "Environment",
    "NativeEnvironment",
    "NativeTemplate",
    "Template",
    "get_env",
    "get_native_env",
    "make",
    "make_native",
    "render",
    "render_native",
    "render_sync",
    "render_sync_native",
]

_env: Environment | None = None
_native_env: NativeEnvironment | None = None

_env_sync: Environment | None = None
_native_env_sync: NativeEnvironment | None = None


def get_env(sync: bool = False) -> Environment:
    global _env, _env_sync

    if sync:
        if _env_sync is None:
            _env_sync = Environment(enable_async=False)
        return _env_sync
    else:
        if _env is None:
            _env = Environment(enable_async=True)
        return _env


def get_native_env(sync: bool = False) -> NativeEnvironment:
    global _native_env, _native_env_sync

    if sync:
        if _native_env_sync is None:
            _native_env_sync = NativeEnvironment(enable_async=False)
        return _native_env_sync
    else:
        if _native_env is None:
            _native_env = NativeEnvironment(enable_async=True)
        return _native_env


def make(source: str, sync: bool = False) -> Template:
    return get_env(sync).from_string(source)


def make_native(source: str, sync: bool = False) -> NativeTemplate:
    return cast(NativeTemplate, get_native_env(sync).from_string(source))


async def render(source: str, context: dict[str, Any]) -> str:
    return await make(source).render_async(context)


async def render_native(source: str, context: dict[str, Any]) -> Any:
    return await make_native(source).render_async(context)


def render_sync(source: str, context: dict[str, Any]) -> str:
    return make(source, sync=True).render(context)


def render_sync_native(source: str, context: dict[str, Any]) -> Any:
    return make_native(source, sync=True).render(context)
