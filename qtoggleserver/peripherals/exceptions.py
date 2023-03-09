class PeripheralException(Exception):
    pass


class NoSuchDriver(PeripheralException):
    pass


class DuplicatePeripheral(PeripheralException):
    pass


class NotOurPort(PeripheralException):
    pass
