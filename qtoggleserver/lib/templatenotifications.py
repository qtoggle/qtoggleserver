
import abc
import datetime
import logging

from jinja2 import Environment

from qtoggleserver.core import device
from qtoggleserver.core import main as core_main
from qtoggleserver.core.events import BaseEventHandler


logger = logging.getLogger(__name__)


class TemplateNotificationsHandler(BaseEventHandler, metaclass=abc.ABCMeta):
    DEFAULT_TEMPLATES = {
        'value-change': {
            'title': '{{port.get_display_name()}} is {{new_value}}{{attrs["unit"]}}',
            'body': 'Port {{port.get_display_name()}} was {{old_value}}{{attrs["unit"]}} '
                    'and is now {{new_value}}{{attrs["unit"]}}.'
        },
        'port-update': {
            'title': '{{port.get_display_name()}} has been updated',
            'body': 'Port {{port.get_display_name()}} attributes have been updated.'
        },
        'port-add': {
            'title': '{{port.get_display_name()}} has been added',
            'body': None
        },
        'port-remove': {
            'title': '{{port.get_display_name()}} has been removed',
            'body': None
        },
        'device-update': {
            'title': '{{device.get_display_name()}} has been updated',
            'body': 'Device {{device.get_display_name()}} attributes have been updated.'
        },
        'slave-device-update': {
            'title': '{{slave.get_display_name()}} has been updated',
            'body': 'Device {{slave.get_display_name()}} attributes have been updated.'
        },
        'slave-device-add': {
            'title': '{{slave.get_display_name()}} has been added',
            'body': None
        },
        'slave-device-remove': {
            'title': '{{slave.get_display_name()}} has been removed',
            'body': None
        },
    }

    logger = logger

    def __init__(self, template=None, templates=None, skip_startup=True, filter=None):
        self._skip_startup = skip_startup
        self._j2env = None

        # "template" has the highest precedence; then comes "templates" and then comes "DEFAULT_TEMPLATES"
        if template is not None:
            templates = {k: template for k in self.DEFAULT_TEMPLATES.keys()}
        if templates is None:
            templates = self.DEFAULT_TEMPLATES

        # Convert template strings to jinja2 templates
        self._j2env = Environment()
        self._templates = {}
        for _type, ts in templates.items():
            self._templates[_type] = {}
            for k, t in ts.items():
                self._templates[_type][k] = self._j2env.from_string(t) if t is not None else None

        super().__init__(filter)

    def render(self, event_type, context):
        template = self._templates[event_type]

        return {k: t.render(context) if t is not None else None for k, t in template.items()}

    @staticmethod
    def get_common_context(event):
        timestamp = event.get_timestamp()
        moment = datetime.datetime.fromtimestamp(timestamp)

        return {
            'event': event,
            'type': event.get_type(),
            'timestamp': int(timestamp),
            'moment': moment,
            'display_moment': moment.strftime('%c')
        }

    async def push_message(self, event, title, body, **kwargs):
        raise NotImplementedError

    async def push_template_message(self, event, context):
        template = self.render(event.get_type(), context)

        await self.push_message(event, **template)

    async def accepts(self, *args, **kwargs):
        # Skip notifications during startup
        if self._skip_startup and not core_main.is_ready():
            return False

        return await super().accepts(*args, **kwargs)

    async def on_value_change(self, event, port, old_value, new_value, attrs):
        context = self.get_common_context(event)
        context.update({
            'port': port,
            'old_value': old_value,
            'new_value': new_value,
            'attrs': attrs
        })

        await self.push_template_message(event, context)

    async def on_port_update(self, event, port, old_attrs, new_attrs,
                             changed_attrs, added_attrs, removed_attrs):

        context = self.get_common_context(event)
        context.update({
            'port': port,
            'old_attrs': old_attrs,
            'new_attrs': new_attrs,
            'changed_attrs': changed_attrs,
            'added_attrs': added_attrs,
            'removed_attrs': removed_attrs,
            'value': port.get_value()
        })

        await self.push_template_message(event, context)

    async def on_port_add(self, event, port, attrs):
        context = self.get_common_context(event)
        context.update({
            'port': port,
            'attrs': attrs,
            'value': port.get_value()
        })

        await self.push_template_message(event, context)

    async def on_port_remove(self, event, port, attrs):
        context = self.get_common_context(event)
        context.update({
            'port': port,
            'attrs': attrs,
            'value': port.get_value()
        })

        await self.push_template_message(event, context)

    async def on_device_update(self, event, old_attrs, new_attrs,
                               changed_attrs, added_attrs, removed_attrs):

        context = self.get_common_context(event)
        context.update({
            'device': device,
            'old_attrs': old_attrs,
            'new_attrs': new_attrs,
            'changed_attrs': changed_attrs,
            'added_attrs': added_attrs,
            'removed_attrs': removed_attrs,
        })

        await self.push_template_message(event, context)

    async def on_slave_device_update(self, event, slave, old_attrs, new_attrs,
                                     changed_attrs, added_attrs, removed_attrs):

        context = self.get_common_context(event)
        context.update({
            'slave': slave,
            'old_attrs': old_attrs,
            'new_attrs': new_attrs,
            'changed_attrs': changed_attrs,
            'added_attrs': added_attrs,
            'removed_attrs': removed_attrs,
        })

        await self.push_template_message(event, context)

    async def on_slave_device_add(self, event, slave, attrs):
        context = self.get_common_context(event)
        context.update({
            'slave': slave,
            'attrs': attrs
        })

        await self.push_template_message(event, context)

    async def on_slave_device_remove(self, event, slave, attrs):
        context = self.get_common_context(event)
        context.update({
            'slave': slave,
            'attrs': attrs
        })

        await self.push_template_message(event, context)
