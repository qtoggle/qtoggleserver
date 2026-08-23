class PeripheralException(Exception):
    pass


class DriverLoadError(PeripheralException):
    pass


class DuplicatePeripheral(PeripheralException):
    pass


class NotOurPort(PeripheralException):
    pass
