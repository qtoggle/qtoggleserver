import logging

from typing import Optional

from qtoggleserver import persist
from qtoggleserver.core import ports as core_ports
from qtoggleserver.core.typing import GenericJSONDict, GenericJSONList, NullablePortValue, PortValue, PortValueChoices


logger = logging.getLogger(__name__)

_vport_args: dict[str, GenericJSONDict] = {}


class VirtualPort(core_ports.Port):
    WRITABLE = True
    VIRTUAL = True

    def __init__(
        self,
        id_: str,
        type_: str,
        min_: Optional[float],
        max_: Optional[float],
        integer: Optional[bool],
        step: Optional[float],
        choices: Optional[PortValueChoices]
    ) -> None:

        super().__init__(id_)

        self._type: str = type_
        self._min: Optional[float] = min_
        self._max: Optional[float] = max_
        self._integer: Optional[bool] = integer
        self._step: Optional[float] = step
        self._choices: Optional[PortValueChoices] = choices

        self._value = self._virtual_value = None
        self._virtual_value: NullablePortValue = None

    def map_id(self, new_id: str) -> None:
        raise core_ports.PortError('Virtual ports cannot be mapped')

    async def read_value(self) -> NullablePortValue:
        return self._virtual_value

    async def write_value(self, value: PortValue) -> None:
        self._virtual_value = value


async def add(
    id_: str,
    type_: str,
    min_: Optional[float],
    max_: Optional[float],
    integer: Optional[bool],
    step: Optional[float],
    choices: Optional[PortValueChoices]
) -> None:

    settings = {
        'id': id_,
        'type': type_,
        'min': min_,
        'max': max_,
        'integer': integer,
        'step': step,
        'choices': choices
    }

    _vport_args[id_] = settings

    logger.debug('saving virtual port settings for %s', id_)
    await persist.replace('vports', id_, settings)


async def remove(port_id: str) -> None:
    _vport_args.pop(port_id, None)
    logger.debug('removing virtual port settings for %s', port_id)
    await persist.remove('vports', filt={'id': port_id})


def all_port_args() -> GenericJSONList:
    return [
        {'driver': VirtualPort, 'id_': port_id, **args}
        for port_id, args in _vport_args.items()
    ]


async def init() -> None:
    for entry in await persist.query('vports'):
        _vport_args[entry['id']] = {
            'type_': entry.get('type') or core_ports.TYPE_NUMBER,
            'min_': entry.get('min'),
            'max_': entry.get('max'),
            'integer': entry.get('integer'),
            'step': entry.get('step'),
            'choices': entry.get('choices')
        }

        logger.debug('loaded virtual port settings for %s', entry['id'])

    # Use raise_on_error=False because we prefer a partial successful startup rather than a failed one
    await core_ports.load(all_port_args(), raise_on_error=False)


async def reset() -> None:
    logger.debug('clearing virtual ports persisted data')
    await persist.remove('vports')
