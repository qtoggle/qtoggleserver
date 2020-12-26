
import logging
import threading

from typing import Any, Dict, Iterable, List, Optional, Union

from qtoggleserver.conf import settings
from qtoggleserver.utils import conf as conf_utils
from qtoggleserver.utils import dynload as dynload_utils
from qtoggleserver.utils import json as json_utils

from .base import BaseDriver
from .typing import Id, Record


logger = logging.getLogger(__name__)

_thread_local: threading.local = threading.local()


def _get_driver() -> BaseDriver:
    if not hasattr(_thread_local, 'driver'):
        driver_args = conf_utils.obj_to_dict(settings.persist)
        driver_class_path = driver_args.pop('driver')

        try:
            logger.debug('loading persistence driver %s', driver_class_path)
            driver_class = dynload_utils.load_attr(driver_class_path)
            _thread_local.driver = driver_class(**driver_args)

        except Exception as e:
            logger.error('failed to load persistence driver %s: %s', driver_class_path, e, exc_info=True)

            raise

    return _thread_local.driver


def is_history_supported() -> bool:
    return _get_driver().is_history_supported()


async def query(
    collection: str,
    fields: Optional[List[str]] = None,
    filt: Optional[Dict[str, Any]] = None,
    sort: Optional[Union[str, List[str]]] = None,
    limit: Optional[int] = None
) -> Iterable[Record]:

    if logger.getEffectiveLevel() <= logging.DEBUG:
        logger.debug(
            'querying %s (%s) where %s (sort=%s, limit=%s)',
            collection,
            json_utils.dumps(fields) if fields else 'all fields',
            json_utils.dumps(filt, allow_extended_types=True),
            json_utils.dumps(sort),
            json_utils.dumps(limit),
        )

    filt = filt or {}
    sort = sort or []
    if isinstance(sort, str):
        sort = [sort]

    # Transform '-field' into (field, reverse)
    sort = [
        (s[1:], True) if s.startswith('-') else (s, False)
        for s in sort
    ]

    return await _get_driver().query(collection, fields, filt, sort, limit)


async def get(collection: str, id_: Id) -> Optional[Record]:
    logger.debug('getting record with id %s from %s', id_, collection)

    records = list(await _get_driver().query(collection, fields=None, filt={'id': id_}, sort=[], limit=1))
    if len(records) > 1:
        logger.warning('more than one record with same id %s found in collection %s', id_, collection)

    if records:
        return records[0]

    return None


async def get_value(name: str, default: Optional[Any] = None) -> Any:
    logger.debug('getting value of %s', name)

    records = list(await _get_driver().query(name, fields=None, filt={}, sort=[], limit=2))
    if len(records) > 1:
        logger.warning('more than one record found in single-value collection %s', name)

        record = records[0]

    elif len(records) > 0:
        record = records[0]

    else:
        return default

    return record['value']


async def set_value(name: str, value: Any) -> None:
    if logger.getEffectiveLevel() <= logging.DEBUG:
        logger.debug('setting %s to %s', name, json_utils.dumps(value, allow_extended_types=True))

    driver = _get_driver()
    record = {'value': value}

    records = list(await driver.query(name, fields=['id'], filt={}, sort=[], limit=2))
    if len(records) > 1:
        logger.warning('more than one record found in single-value collection %s', name)

        id_ = records[0]['id']

    elif len(records) > 0:
        id_ = records[0]['id']

    else:
        id_ = None

    if id_ is None:
        await driver.insert(name, record)

    else:
        await driver.replace(name, id_, record)


async def insert(collection: str, record: Record) -> Id:
    if logger.getEffectiveLevel() <= logging.DEBUG:
        logger.debug('inserting %s into %s', json_utils.dumps(record, allow_extended_types=True), collection)

    return await _get_driver().insert(collection, record)


async def update(collection: str, record_part: Record, filt: Optional[Dict[str, Any]] = None) -> int:
    if logger.getEffectiveLevel() <= logging.DEBUG:
        logger.debug(
            'updating %s where %s with %s',
            collection,
            json_utils.dumps(filt or {}, allow_extended_types=True),
            json_utils.dumps(record_part, allow_extended_types=True)
        )

    count = await _get_driver().update(collection, record_part, filt or {})

    logger.debug('modified %s records in %s', count, collection)

    return count


async def replace(collection: str, id_: Id, record: Record) -> bool:
    if logger.getEffectiveLevel() <= logging.DEBUG:
        logger.debug(
            'replacing record with id %s with %s in %s',
            id_,
            json_utils.dumps(record, allow_extended_types=True),
            collection
        )

    record = dict(record, id=id_)  # Make sure the new record contains the id field
    replaced = await _get_driver().replace(collection, id_, record)
    if replaced:
        logger.debug('replaced record with id %s in %s', id_, collection)

        return False

    else:
        await _get_driver().insert(collection, dict(record, id=id_))
        logger.debug('inserted record with id %s in %s', id_, collection)

        return True


async def remove(collection: str, filt: Optional[Dict[str, Any]] = None) -> int:
    if logger.getEffectiveLevel() <= logging.DEBUG:
        logger.debug('removing from %s where %s', collection, json_utils.dumps(filt or {}, allow_extended_types=True))

    count = await _get_driver().remove(collection, filt or {})

    logger.debug('removed %s records from %s', count, collection)

    return count


async def ensure_index(collection: str, index: Union[str, List[str]]) -> None:
    if isinstance(index, str):
        index = [index]

    # Transform '-field' into (field, reverse)
    index = [
        (i[1:], True) if i.startswith('-') else (i, False)
        for i in index
    ]

    if logger.getEffectiveLevel() <= logging.DEBUG:
        logger.debug('ensuring index %s in %s', json_utils.dumps(index), collection)

    await _get_driver().ensure_index(collection, index)


async def cleanup() -> None:
    logger.debug('cleaning up')

    return await _get_driver().cleanup()
