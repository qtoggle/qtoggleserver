
from .gpio import GPIO

try:
    from .rpi import RPiGPIO

except ImportError:
    pass
