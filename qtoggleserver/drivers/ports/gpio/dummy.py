from qtoggleserver.core import ports
from qtoggleserver.utils import json as json_utils


class DummyGPIO(ports.Port):
    TYPE = ports.TYPE_BOOLEAN

    ADDITIONAL_ATTRDEFS = {
        "output": {
            "display_name": "Is Output",
            "description": "Controls the port direction.",
            "type": "boolean",
            "modifiable": True,
        }
    }

    def __init__(self, no: int, def_value: bool | None = None, def_output: bool | None = None) -> None:
        self._no: int = no

        self._def_value: bool | None = def_value
        self._def_output: bool | None = def_output

        self._dummy_value: bool | None = def_value or False
        self._dummy_output: bool = def_output if def_output is not None else False

        super().__init__(port_id=f"gpio{no}")

    async def handle_enable(self) -> None:
        if self._def_output is not None:
            await self.attr_set_output(self._def_output)

    async def read_value(self) -> bool | None:
        return self._dummy_value

    async def write_value(self, value: bool | None) -> None:
        self.debug('writing "%s"', json_utils.dumps(value))
        self._dummy_value = value

    async def attr_is_writable(self) -> bool:
        return self._dummy_output

    async def attr_set_output(self, output: bool) -> None:
        self._dummy_output = output

        if output:
            self.debug("setting output mode")
        else:
            self.debug("setting input mode")

        if output and self._def_value is not None:
            await self.write_value(self._def_value)

    async def attr_is_output(self) -> bool:
        return self._dummy_output
