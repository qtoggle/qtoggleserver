
import importlib
import logging
import os

from typing import Optional

from jinja2 import Environment, FileSystemLoader, select_autoescape

from .constants import FRONTEND_DIR


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
        path: str = 'templates',
        encoding: str = 'utf-8',
        followlinks: bool = False
    ) -> None:

        namespace = importlib.import_module(namespace_name)
        searchpath = [os.path.join(p, path) for p in namespace.__path__]

        super().__init__(searchpath=searchpath, encoding=encoding, followlinks=followlinks)


def get_env() -> Environment:
    global _env

    if _env is None:
        logger.debug('creating Jinja2 template environment')
        loader = NamespaceLoader('qtoggleserver', f'{FRONTEND_DIR}/html')
        _env = Environment(loader=loader, autoescape=select_autoescape())

    return _env
