class DeviceException(Exception):
    pass


class DeviceAttributeError(DeviceException):
    def __init__(self, error: str, attribute: str) -> None:
        self.error: str = error
        self.attribute: str = attribute


class NoSuchDriver(DeviceException):
    pass
