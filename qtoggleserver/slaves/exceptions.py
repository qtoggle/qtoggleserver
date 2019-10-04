
from qtoggleserver.core import api as core_api
from qtoggleserver.core import responses as core_responses


class SlaveError(Exception):
    pass


class InvalidDevice(SlaveError):
    pass


class NoListenSupport(SlaveError):
    def __init__(self, name):
        self.name = name

        super().__init__('device {} has no listen support'.format(name))


class DeviceAlreadyExists(SlaveError):
    def __init__(self, name):
        self.name = name

        super().__init__('device {} already exists'.format(name))


class DeviceRenamed(SlaveError):
    def __init__(self, slave):
        self.slave = slave

        super().__init__('{} renamed'.format(slave))


class DeviceOffline(SlaveError):
    def __init__(self, slave):
        self.slave = slave

        super().__init__('{} is offline'.format(slave))


class PortNotFound(SlaveError):
    def __init__(self, slave, _id):
        self.slave = slave
        self.id = _id

        super().__init__('could not find port {}.{}'.format(slave, _id))


def adapt_api_error(error):
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
        return core_api.APIError(400, 'forbidden')  # yes, 400, since it's a slave authorization issue

    elif isinstance(error, core_api.APIError):
        return error

    else:  # Leave error unchanged since it's probably an internal exception
        return error
