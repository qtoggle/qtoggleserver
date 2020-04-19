
import importlib
import logging
import os

from typing import List, Optional, Union
from urllib.parse import quote_plus

from jinja2 import Environment, FileSystemLoader, select_autoescape

from .constants import FRONTEND_DIR, FRONTEND_DIR_DEBUG


_env: Optional[Environment] = None
logger = logging.getLogger(__name__)


class J2TemplateMixin:
    def render(self, template_name: str, **context) -> None:
        env = get_env()
        template = env.get_template(template_name)
        template_str = template.render(**context)

        self.finish(template_str)


class NamespaceLoader(FileSystemLoader):
    def __init__(
        self,
        namespace_name: str,
        path: Union[str, List[str]] = 'templates',
        encoding: str = 'utf-8',
        followlinks: bool = False
    ) -> None:

        if isinstance(path, str):
            path = [path]

        namespace = importlib.import_module(namespace_name)
        namespace_path = list(namespace.__path__)[0]
        searchpath = [os.path.join(namespace_path, p) for p in path]

        super().__init__(searchpath=searchpath, encoding=encoding, followlinks=followlinks)


def urlquote(s: Union[str, bytes]) -> Union[str, bytes]:
    if s:
        return quote_plus(s)

    return s


def get_env() -> Environment:
    global _env

    if _env is None:
        logger.debug('creating Jinja2 template environment')
        loader = NamespaceLoader('qtoggleserver', [f'{FRONTEND_DIR_DEBUG}/html', f'{FRONTEND_DIR}/html'])
        _env = Environment(loader=loader, autoescape=select_autoescape())
        _env.filters['urlquote'] = urlquote

    return _env
