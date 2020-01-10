
from qtoggleserver.core import api as core_api
from qtoggleserver.core import responses as core_responses

from . import devices as slave_devices


class SlaveError(Exception):
    pass


class InvalidDevice(SlaveError):
    pass


class NoListenSupport(SlaveError):
    def __init__(self, name: str) -> None:
        self.name: str = name

        super().__init__(f'Device {name} has no listen support')


class DeviceAlreadyExists(SlaveError):
    def __init__(self, name: str) -> None:
        self.name: str = name

        super().__init__(f'Device {name} already exists')


class DeviceRenamed(SlaveError):
    def __init__(self, slave: 'slave_devices.Slave') -> None:
        self.slave: slave_devices.Slave = slave

        super().__init__(f'{slave} renamed')


class DeviceOffline(SlaveError):
    def __init__(self, slave: 'slave_devices.Slave') -> None:
        self.slave: slave_devices.Slave = slave

        super().__init__(f'{slave} is offline')


class PortNotFound(SlaveError):
    def __init__(self, slave: 'slave_devices.Slave', _id: str) -> None:
        self.slave: slave_devices.Slave = slave
        self.id: str = _id

        super().__init__(f'Could not find port {slave}.{_id}')


def adapt_api_error(error: Exception) -> Exception:
    if isinstance(error, (core_responses.HostUnreachable,
                          core_responses.NetworkUnreachable,
                          core_responses.UnresolvableHostname)):

        return core_api.APIError(502, 'unreachable')

    elif isinstance(error, core_responses.ConnectionRefused):
        return core_api.APIError(502, 'connection refused')

    elif isinstance(error, core_responses.InvalidJson):
        return core_api.APIError(502, 'invalid device')

    elif isinstance(error, core_responses.Timeout):
        return core_api.APIError(504, 'device timeout')

    elif isinstance(error, core_responses.HTTPError):
        return core_api.APIError.from_http_error(error)

    elif isinstance(error, DeviceOffline):
        return core_api.APIError(503, 'device offline')

    elif isinstance(error, InvalidDevice):
        return core_api.APIError(502, 'invalid device')

    elif isinstance(error, core_responses.AuthError):
        return core_api.APIError(400, 'forbidden')  # Yes, 400, since it's a slave authorization issue

    elif isinstance(error, core_api.APIError):
        return error

    else:  # Leave error unchanged since it's probably an internal exception
        return error
