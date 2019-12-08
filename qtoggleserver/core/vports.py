
import logging

from qtoggleserver import persist

from qtoggleserver.core import ports as core_ports


logger = logging.getLogger(__name__)


_vport_settings = {}


class VirtualPort(core_ports.Port):
    WRITABLE = True
    VIRTUAL = True

    def __init__(self, port_id, typ, mi, ma, integer, step, choices):
        super().__init__(port_id)

        self._type = typ
        self._min = mi
        self._max = ma
        self._integer = integer
        self._step = step
        self._choices = choices

        self._value = self._virtual_value = self.adapt_value_type_sync(typ, integer, mi or 0)

    def map_id(self, new_id):
        raise core_ports.PortError('virtual ports cannot be mapped')

    async def read_value(self):
        return self._virtual_value

    async def write_value(self, value):
        self._virtual_value = value


def add(port_id, typ, mi, ma, integer, step, choices):
    settings = {
        'id': port_id,
        'type': typ,
        'min': mi,
        'max': ma,
        'integer': integer,
        'step': step,
        'choices': choices
    }

    _vport_settings[port_id] = settings

    logger.debug('saving virtual port settings for %s', port_id)
    persist.replace('vports', port_id, settings)


def remove(port_id):
    try:
        _vport_settings.pop(port_id)

    except KeyError:
        logger.error('virtual port settings for %s no longer exist', port_id)

        return False

    logger.debug('removing virtual port settings for %s', port_id)
    persist.remove('vports', filt={'id': port_id})

    return True


def all_settings():
    return [dict({'driver': VirtualPort, 'port_id': port_id}, **settings)
            for port_id, settings in _vport_settings.items()]


def load():
    for entry in persist.query('vports'):
        _vport_settings[entry['id']] = {
            'typ': entry.get('type') or core_ports.TYPE_NUMBER,
            'mi': entry.get('min'),
            'ma': entry.get('max'),
            'integer': entry.get('integer'),
            'step': entry.get('step'),
            'choices': entry.get('choices')
        }

        logger.debug('loaded virtual port settings for %s', entry['id'])


def reset():
    logger.debug('clearing virtual ports persisted data')
    persist.remove('vports')
