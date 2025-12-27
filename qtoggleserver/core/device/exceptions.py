class DeviceException(Exception):
    pass


class DeviceAttributeException(DeviceException):
    pass


class DeviceAttributeError(DeviceAttributeException):
    def __init__(self, error: str, attribute: str) -> None:
        self.error: str = error
        self.attribute: str = attribute


class NoSuchDriver(DeviceAttributeException):
    pass
