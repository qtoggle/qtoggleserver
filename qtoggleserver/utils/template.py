from typing import Any, cast

from jinja2 import Environment, Template
from jinja2.nativetypes import NativeEnvironment, NativeTemplate


_environment: Environment | None = None
_native_environment: Environment | None = None


def get_env() -> Environment:
    global _environment

    if _environment is None:
        _environment = Environment(enable_async=True)
        _environment.globals.update(__builtins__)

    return _environment


def get_native_env() -> NativeEnvironment:
    global _native_environment

    if _native_environment is None:
        _native_environment = NativeEnvironment(enable_async=True)
        _native_environment.globals.update(__builtins__)

    return _native_environment


def make(source: str) -> Template:
    return get_env().from_string(source)


def make_native(source: str) -> NativeTemplate:
    return cast(NativeTemplate, get_native_env().from_string(source))


def render(source: str, context: dict[str, Any]) -> str:
    return make(source).render(context)


async def render_async(source: str, context: dict[str, Any]) -> str:
    return await make(source).render_async(context)


async def render_native(source: str, context: dict[str, Any]) -> Any:
    return await make_native(source).render_async(context)
