import abc
import datetime
import logging

from typing import Optional

from jinja2 import Environment, Template

from qtoggleserver.conf import settings
from qtoggleserver.core import device
from qtoggleserver.core import events as core_events
from qtoggleserver.core import main as core_main
from qtoggleserver.core import ports as core_ports
from qtoggleserver.core.typing import Attribute, Attributes, NullablePortValue
from qtoggleserver.slaves import devices as slaves_devices

from .filtereventhandler import FilterEventHandler


logger = logging.getLogger(__name__)


class TemplateNotificationsHandler(FilterEventHandler, metaclass=abc.ABCMeta):
    DEFAULT_TEMPLATES = {  # TODO: i18n
        'value-change': {
            'title': '{{port.get_display_name()}} is {{port.get_display_value()}}',
            'body': (
                'Port {{port.get_display_name()}} was {{port.get_display_value(old_value)}} '
                'and is now {{port.get_display_value(new_value)}}.'
            )
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
        'full-update': {
            'title': '{{device.get_display_name()}} has been updated',
            'body': 'Device {{device.get_display_name()}} has been fully updated.'
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

    def __init__(
        self,
        *,
        template: Optional[dict[str, str]] = None,
        templates: Optional[dict[str, dict[str, str]]] = None,
        skip_startup: bool = True,
        filter: dict = None,
        name: Optional[str] = None
    ) -> None:

        self._skip_startup: bool = skip_startup

        # "template" has the highest precedence; then comes "templates" and then comes "DEFAULT_TEMPLATES"
        if template is not None:
            templates = {k: template for k in self.DEFAULT_TEMPLATES.keys()}
        if templates is None:
            templates = self.DEFAULT_TEMPLATES

        # Convert template strings to jinja2 templates
        self._j2env: Environment = Environment(enable_async=True)
        self._templates: dict[str, dict[str, Template]] = {}
        for type_, ts in templates.items():
            # Ensure values in templates are dicts themselves
            if isinstance(ts, str):
                ts = {'title': ts}

            self._templates[type_] = {}
            for k, t in ts.items():
                self._templates[type_][k] = self._j2env.from_string(t) if t is not None else None

        super().__init__(name=name, filter=filter)

    async def render(self, event_type: str, context: dict) -> dict[str, str]:
        template = self._templates[event_type]

        return {k: await t.render_async(context) if t is not None else None for k, t in template.items()}

    @staticmethod
    def get_common_context(event: core_events.Event) -> dict:
        timestamp = event.get_timestamp()
        if timestamp:
            moment = datetime.datetime.fromtimestamp(timestamp)
        else:
            moment = None

        return {
            'event': event,
            'type': event.get_type(),
            'timestamp': timestamp,
            'moment': moment,
            'display_moment': moment.strftime('%c') if moment else '',
            'public_url': settings.public_url
        }

    @abc.abstractmethod
    async def push_message(self, event: core_events.Event, title: str, body: str, **kwargs) -> None:
        raise NotImplementedError()

    async def push_template_message(self, event: core_events.Event, context: dict) -> None:
        template = await self.render(event.get_type(), context)

        await self.push_message(event, **template)

    async def accepts(self, *args, **kwargs) -> bool:
        # Skip notifications during startup
        if self._skip_startup:
            if not core_main.is_ready():
                return False

            if isinstance(self._skip_startup, (int, float)) and core_main.uptime() < self._skip_startup:
                return False

        return await super().accepts(*args, **kwargs)

    async def on_value_change(
        self,
        event: core_events.Event,
        port: core_ports.BasePort,
        old_value: NullablePortValue,
        new_value: NullablePortValue,
        attrs: Attributes
    ) -> None:

        context = self.get_common_context(event)
        context.update({
            'port': port,
            'old_value': old_value,
            'new_value': new_value,
            'attrs': attrs
        })

        await self.push_template_message(event, context)

    async def on_port_update(
        self,
        event: core_events.Event,
        port: core_ports.BasePort,
        old_attrs: Attributes,
        new_attrs: Attributes,
        changed_attrs: dict[str, tuple[Attribute, Attribute]],
        added_attrs: Attributes,
        removed_attrs: Attributes
    ) -> None:

        context = self.get_common_context(event)
        context.update({
            'port': port,
            'old_attrs': old_attrs,
            'new_attrs': new_attrs,
            'changed_attrs': changed_attrs,
            'added_attrs': added_attrs,
            'removed_attrs': removed_attrs,
            'value': port.get_last_read_value()
        })

        await self.push_template_message(event, context)

    async def on_port_add(self, event: core_events.Event, port: core_ports.BasePort, attrs: Attributes) -> None:
        context = self.get_common_context(event)
        context.update({
            'port': port,
            'attrs': attrs,
            'value': port.get_last_read_value()
        })

        await self.push_template_message(event, context)

    async def on_port_remove(self, event: core_events.Event, port: core_ports.BasePort, attrs: Attributes) -> None:
        context = self.get_common_context(event)
        context.update({
            'port': port,
            'attrs': attrs,
            'value': port.get_last_read_value()
        })

        await self.push_template_message(event, context)

    async def on_device_update(
        self,
        event: core_events.Event,
        old_attrs: Attributes,
        new_attrs: Attributes,
        changed_attrs: dict[str, tuple[Attribute, Attribute]],
        added_attrs: Attributes,
        removed_attrs: Attributes
    ) -> None:

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

    async def on_full_update(self, event: core_events.Event) -> None:
        context = self.get_common_context(event)

        await self.push_template_message(event, context)

    async def on_slave_device_update(
        self,
        event: core_events.Event,
        slave: slaves_devices.Slave,
        old_attrs: Attributes,
        new_attrs: Attributes,
        changed_attrs: dict[str, tuple[Attribute, Attribute]],
        added_attrs: Attributes,
        removed_attrs: Attributes
    ) -> None:

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

    async def on_slave_device_add(
        self,
        event: core_events.Event,
        slave: slaves_devices.Slave,
        attrs: Attributes
    ) -> None:

        context = self.get_common_context(event)
        context.update({
            'slave': slave,
            'attrs': attrs
        })

        await self.push_template_message(event, context)

    async def on_slave_device_remove(
        self,
        event: core_events.Event,
        slave: slaves_devices.Slave,
        attrs: Attributes
    ) -> None:

        context = self.get_common_context(event)
        context.update({
            'slave': slave,
            'attrs': attrs
        })

        await self.push_template_message(event, context)
