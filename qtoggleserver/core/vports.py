
import logging

from typing import Dict, List, Optional

from qtoggleserver import persist
from qtoggleserver.core import ports as core_ports
from qtoggleserver.core.typing import GenericJSONDict, NullablePortValue, PortValue, PortValueChoices


logger = logging.getLogger(__name__)

_vport_args: Dict[str, GenericJSONDict] = {}


class VirtualPort(core_ports.Port):
    WRITABLE = True
    VIRTUAL = True

    def __init__(
        self,
        port_id: str,
        _type: str,
        _min: Optional[float],
        _max: Optional[float],
        integer: Optional[bool],
        step: Optional[float],
        choices: Optional[PortValueChoices]
    ) -> None:

        super().__init__(port_id)

        self._type: str = _type
        self._min: Optional[float] = _min
        self._max: Optional[float] = _max
        self._integer: Optional[bool] = integer
        self._step: Optional[float] = step
        self._choices: Optional[PortValueChoices] = choices

        self._value = self._virtual_value = self.adapt_value_type_sync(_type, integer, _min or 0)

    def map_id(self, new_id: str) -> None:
        raise core_ports.PortError('Virtual ports cannot be mapped')

    async def read_value(self) -> NullablePortValue:
        return self._virtual_value

    async def write_value(self, value: PortValue) -> None:
        self._virtual_value = value


def add(
    port_id: str,
    _type: str,
    _min: Optional[float],
    _max: Optional[float],
    integer: Optional[bool],
    step: Optional[float],
    choices: Optional[PortValueChoices]
) -> None:

    settings = {
        'id': port_id,
        'type': _type,
        'min': _min,
        'max': _max,
        'integer': integer,
        'step': step,
        'choices': choices
    }

    _vport_args[port_id] = settings

    logger.debug('saving virtual port settings for %s', port_id)
    persist.replace('vports', port_id, settings)


def remove(port_id: str) -> None:
    _vport_args.pop(port_id, None)
    logger.debug('removing virtual port settings for %s', port_id)
    persist.remove('vports', filt={'id': port_id})


def all_port_args() -> List[GenericJSONDict]:
    return [dict({'driver': VirtualPort, 'port_id': port_id}, **args)
            for port_id, args in _vport_args.items()]


def load() -> None:
    for entry in persist.query('vports'):
        _vport_args[entry['id']] = {
            '_type': entry.get('type') or core_ports.TYPE_NUMBER,
            '_min': entry.get('min'),
            '_max': entry.get('max'),
            'integer': entry.get('integer'),
            'step': entry.get('step'),
            'choices': entry.get('choices')
        }

        logger.debug('loaded virtual port settings for %s', entry['id'])


def reset() -> None:
    logger.debug('clearing virtual ports persisted data')
    persist.remove('vports')
