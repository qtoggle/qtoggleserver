
import logging

from jinja2 import Environment, PackageLoader, select_autoescape

from .constants import FRONTEND_DIR


_env = None
logger = logging.getLogger(__name__)


class J2TemplateMixin:
    def render(self, template_name, **context):
        env = get_env()
        template = env.get_template(template_name)
        template_str = template.render(**context)

        self.finish(template_str)


def get_env():
    global _env

    if _env is None:
        logger.debug('creating Jinja2 template environment')
        package_loader = PackageLoader('qtoggleserver', '{}/html'.format(FRONTEND_DIR))
        _env = Environment(loader=package_loader, autoescape=select_autoescape())

    return _env
