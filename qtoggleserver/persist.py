
import abc
import logging

from qtoggleserver import utils
from qtoggleserver.conf import settings
from qtoggleserver.conf import utils as conf_utils
from qtoggleserver.utils import json as json_utils


logger = logging.getLogger(__name__)

_driver = None


class BaseDriver(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def query(self, collection, fields, filt, limit):
        return []

    @abc.abstractmethod
    def insert(self, collection, record):
        return '1'  # returns the inserted record id

    @abc.abstractmethod
    def update(self, collection, record_part, filt):
        return 0  # returns the number of updated records

    @abc.abstractmethod
    def replace(self, collection, _id, record, upsert):
        return False  # returns True if replaced

    @abc.abstractmethod
    def remove(self, collection, filt):
        return 0  # returns the number of removed records

    @abc.abstractmethod
    def close(self):
        pass


def _get_driver():
    global _driver

    if _driver is None:
        driver_args = conf_utils.obj_to_dict(settings.persist)
        driver_class_path = driver_args.pop('driver')

        try:
            logger.debug('loading persistence driver %s', driver_class_path)
            driver_class = utils.load_attr(driver_class_path)
            _driver = driver_class(**driver_args)

        except Exception as e:
            logger.error('failed to load persistence driver %s: %s', driver_class_path, e, exc_info=True)

            raise

    return _driver


def query(collection, fields=None, filt=None, limit=None):
    if logger.getEffectiveLevel() <= logging.DEBUG:
        logger.debug('querying %s (%s) where %s', collection, json_utils.dumps(fields) if fields else 'all fields',
                     json_utils.dumps(filt))

    return _get_driver().query(collection, fields, filt or {}, limit)


def get(collection, _id):
    if logger.getEffectiveLevel() <= logging.DEBUG:
        logger.debug('getting record with id %s from %s', _id, collection)

    records = list(_get_driver().query(collection, fields=None, filt={'id': _id}, limit=1))
    if records:
        return records[0]

    return None


def get_value(name, default=None):
    if logger.getEffectiveLevel() <= logging.DEBUG:
        logger.debug('getting value of %s', name)

    records = list(_get_driver().query(name, fields=None, filt={}, limit=2))
    if len(records) > 1:
        logger.warning('more than one record found in single-value collection %s', name)

        record = records[0]

    elif len(records) > 0:
        record = records[0]

    else:
        return default

    return record['value']


def set_value(name, value):
    if logger.getEffectiveLevel() <= logging.DEBUG:
        logger.debug('setting %s to %s', name, json_utils.dumps(value))

    record = {'value': value}
    _get_driver().replace(name, '', record, upsert=True)


def insert(collection, record):
    if logger.getEffectiveLevel() <= logging.DEBUG:
        logger.debug('inserting %s into %s', json_utils.dumps(record), collection)

    return _get_driver().insert(collection, record)


def update(collection, record_part, filt=None):
    if logger.getEffectiveLevel() <= logging.DEBUG:
        logger.debug('updating %s where %s with %s', collection, json_utils.dumps(filt or {}),
                     json_utils.dumps(record_part))

    count = _get_driver().update(collection, record_part, filt or {})

    logger.debug('modified %s records in %s', count, collection)

    return count


def replace(collection, _id, record, upsert=True):
    if logger.getEffectiveLevel() <= logging.DEBUG:
        logger.debug('replacing record with id %s with %s in %s', _id, json_utils.dumps(record), collection)

    record = dict(record, id=_id)  # make sure the new record contains the id field
    replaced = _get_driver().replace(collection, _id, record, upsert)

    if replaced:
        logger.debug('replaced record with id %s in %s', _id, collection)

    return replaced


def remove(collection, filt=None):
    if logger.getEffectiveLevel() <= logging.DEBUG:
        logger.debug('removing from %s where %s', collection, json_utils.dumps(filt or {}))

    count = _get_driver().remove(collection, filt or {})

    logger.debug('removed %s records from %s', count, collection)

    return count


def close():
    logger.debug('closing')

    return _get_driver().close()
