
import abc
import inspect
import logging

from qtoggleserver.core import api as core_api
from qtoggleserver.core.device import attrs as core_device_attrs


logger = logging.getLogger(__name__)


class Event(metaclass=abc.ABCMeta):
    REQUIRED_ACCESS = core_api.ACCESS_LEVEL_NONE

    def __init__(self, typ, params):
        self._type = typ
        self._params = params

    async def to_json(self):
        return {
            'type': self._type,
            'params': await self._resolve_params(self._params)
        }

    async def _resolve_params(self, param):
        if isinstance(param, dict):
            for k, v in param.items():
                param[k] = await self._resolve_params(v)

            return param

        elif isinstance(param, (list, tuple)):
            param = list(param)
            for i in range(len(param)):
                param[i] = await self._resolve_params(param[i])

            return param

        elif callable(param):
            param = param()
            if inspect.isawaitable(param):
                param = await param

            return param

        elif inspect.isawaitable(param):
            return await param

        else:
            return param

    def find_duplicate(self, events):
        return None

    def __str__(self):
        return '{} event'.format(self._type)


class ValueChange(Event):
    REQUIRED_ACCESS = core_api.ACCESS_LEVEL_VIEWONLY

    def __init__(self, port):
        self.port = port

        super().__init__('value-change', {
            'id': port.get_id(),
            'value': port.get_value()
        })

    def find_duplicate(self, events):
        for e in events:
            if isinstance(e, ValueChange) and e.port == self.port:
                return e

    def __str__(self):
        return '{}({}) event'.format(self._type, self.port.get_id())


class PortUpdate(Event):
    REQUIRED_ACCESS = core_api.ACCESS_LEVEL_VIEWONLY

    def __init__(self, port):
        self.port = port

        super().__init__('port-update', port.to_json)

    def find_duplicate(self, events):
        for e in events:
            if isinstance(e, PortUpdate) and e.port == self.port:
                return e

    def __str__(self):
        return '{}({}) event'.format(self._type, self.port.get_id())


class PortAdd(Event):
    REQUIRED_ACCESS = core_api.ACCESS_LEVEL_VIEWONLY

    def __init__(self, port):
        self.port = port

        super().__init__('port-add', port.to_json)

    def __str__(self):
        return '{}({}) event'.format(self._type, self.port.get_id())


class PortRemove(Event):
    REQUIRED_ACCESS = core_api.ACCESS_LEVEL_VIEWONLY

    def __init__(self, port):
        self.port = port

        super().__init__('port-remove', {
            'id': port.get_id()
        })

    def __str__(self):
        return '{}({}) event'.format(self._type, self.port.get_id())


class DeviceUpdate(Event):
    REQUIRED_ACCESS = core_api.ACCESS_LEVEL_ADMIN

    def find_duplicate(self, events):
        for e in events:
            if isinstance(e, DeviceUpdate):
                return e

    def __init__(self):
        super().__init__('device-update', core_device_attrs.to_json())


class SlaveDeviceUpdate(Event):
    REQUIRED_ACCESS = core_api.ACCESS_LEVEL_ADMIN

    def __init__(self, slave):
        self.slave = slave

        super().__init__('slave-device-update', slave.to_json())

    def find_duplicate(self, events):
        for e in events:
            if isinstance(e, SlaveDeviceUpdate) and e.slave == self.slave:
                return e

    def __str__(self):
        return '{}({}) event'.format(self._type, self.slave.get_name())


class SlaveDeviceAdd(Event):
    REQUIRED_ACCESS = core_api.ACCESS_LEVEL_ADMIN

    def __init__(self, slave):
        self.slave = slave

        super().__init__('slave-device-add', slave.to_json())

    def __str__(self):
        return '{}({}) event'.format(self._type, self.slave.get_name())


class SlaveDeviceRemove(Event):
    REQUIRED_ACCESS = core_api.ACCESS_LEVEL_ADMIN

    def __init__(self, name):
        self.name = name
        super().__init__('slave-device-remove', {'name': name})

    def __str__(self):
        return '{}({}) event'.format(self._type, self.name)
