
from __future__ import annotations

import abc
import logging

from typing import Any, Dict, Iterable, List, Optional

from qtoggleserver.conf import settings
from qtoggleserver.utils import conf as conf_utils
from qtoggleserver.utils import dynload as dynload_utils
from qtoggleserver.utils import json as json_utils


# TODO: move to persist.typing module
Id = str
Record = Dict[str, Any]


logger = logging.getLogger(__name__)

_driver: Optional[BaseDriver] = None


class BaseDriver(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def query(
        self,
        collection: str,
        fields: Optional[List[str]],
        filt: Dict[str, Any],
        limit: Optional[int]
    ) -> Iterable[Record]:

        return []

    @abc.abstractmethod
    def insert(self, collection: str, record: Record) -> Id:
        return '1'  # Returns the inserted record id

    @abc.abstractmethod
    def update(self, collection: str, record_part: Record, filt: Dict[str, Any]) -> int:
        return 0  # Returns the number of updated records

    @abc.abstractmethod
    def replace(self, collection: str, id_: Id, record: Record, upsert: bool) -> bool:
        return False  # Returns True if replaced

    @abc.abstractmethod
    def remove(self, collection: str, filt: Dict[str, Any]) -> int:
        return 0  # Returns the number of removed records

    @abc.abstractmethod
    def cleanup(self) -> None:
        pass


def _get_driver() -> BaseDriver:
    global _driver

    if _driver is None:
        driver_args = conf_utils.obj_to_dict(settings.persist)
        driver_class_path = driver_args.pop('driver')

        try:
            logger.debug('loading persistence driver %s', driver_class_path)
            driver_class = dynload_utils.load_attr(driver_class_path)
            _driver = driver_class(**driver_args)

        except Exception as e:
            logger.error('failed to load persistence driver %s: %s', driver_class_path, e, exc_info=True)

            raise

    return _driver


def query(
    collection: str,
    fields: Optional[List[str]] = None,
    filt: Optional[Dict[str, Any]] = None,
    limit: Optional[int] = None
) -> Iterable[Record]:

    if logger.getEffectiveLevel() <= logging.DEBUG:
        logger.debug(
            'querying %s (%s) where %s',
            collection,
            json_utils.dumps(fields) if fields else 'all fields',
            json_utils.dumps(filt, allow_extended_types=True)
        )

    return _get_driver().query(collection, fields, filt or {}, limit)


def get(collection: str, id_: Id) -> Optional[Record]:
    if logger.getEffectiveLevel() <= logging.DEBUG:
        logger.debug('getting record with id %s from %s', id_, collection)

    records = list(_get_driver().query(collection, fields=None, filt={'id': id_}, limit=1))
    if records:
        return records[0]

    return None


def get_value(name: str, default: Optional[Any] = None) -> Any:
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


def set_value(name: str, value: Any) -> None:
    if logger.getEffectiveLevel() <= logging.DEBUG:
        logger.debug('setting %s to %s', name, json_utils.dumps(value, allow_extended_types=True))

    record = {'value': value}
    _get_driver().replace(name, '', record, upsert=True)


def insert(collection: str, record: Record) -> Id:
    if logger.getEffectiveLevel() <= logging.DEBUG:
        logger.debug('inserting %s into %s', json_utils.dumps(record, allow_extended_types=True), collection)

    return _get_driver().insert(collection, record)


def update(collection: str, record_part: Record, filt: Optional[Dict[str, Any]] = None) -> int:
    if logger.getEffectiveLevel() <= logging.DEBUG:
        logger.debug(
            'updating %s where %s with %s',
            collection,
            json_utils.dumps(filt or {}, allow_extended_types=True),
            json_utils.dumps(record_part, allow_extended_types=True)
        )

    count = _get_driver().update(collection, record_part, filt or {})

    logger.debug('modified %s records in %s', count, collection)

    return count


def replace(collection: str, id_: Id, record: Record, upsert: bool = True) -> bool:
    if logger.getEffectiveLevel() <= logging.DEBUG:
        logger.debug(
            'replacing record with id %s with %s in %s',
            id_,
            json_utils.dumps(record, allow_extended_types=True),
            collection
        )

    record = dict(record, id=id_)  # Make sure the new record contains the id field
    replaced = _get_driver().replace(collection, id_, record, upsert)

    if replaced:
        logger.debug('replaced record with id %s in %s', id_, collection)

    return replaced


def remove(collection: str, filt: Optional[Dict[str, Any]] = None) -> int:
    if logger.getEffectiveLevel() <= logging.DEBUG:
        logger.debug('removing from %s where %s', collection, json_utils.dumps(filt or {}, allow_extended_types=True))

    count = _get_driver().remove(collection, filt or {})

    logger.debug('removed %s records from %s', count, collection)

    return count


async def cleanup() -> None:
    logger.debug('cleaning up')

    return _get_driver().cleanup()
