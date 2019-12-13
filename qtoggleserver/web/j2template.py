
import importlib
import logging
import os

from jinja2 import Environment, FileSystemLoader, select_autoescape

from .constants import FRONTEND_DIR


_env = None
logger = logging.getLogger(__name__)


class J2TemplateMixin:
    def render(self, template_name, **context):
        env = get_env()
        template = env.get_template(template_name)
        template_str = template.render(**context)

        self.finish(template_str)


class NamespaceLoader(FileSystemLoader):
    def __init__(self, namespace_name, path='templates', encoding='utf-8', followlinks=False):
        namespace = importlib.import_module(namespace_name)
        searchpath = [os.path.join(p, path) for p in namespace.__path__]

        super().__init__(searchpath=searchpath, encoding=encoding, followlinks=followlinks)


def get_env():
    global _env

    if _env is None:
        logger.debug('creating Jinja2 template environment')
        loader = NamespaceLoader('qtoggleserver', '{}/html'.format(FRONTEND_DIR))
        _env = Environment(loader=loader, autoescape=select_autoescape())

    return _env
