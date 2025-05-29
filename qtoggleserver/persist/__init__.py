import logging
import threading

from collections.abc import Iterable
from typing import Any

from qtoggleserver.conf import settings
from qtoggleserver.utils import conf as conf_utils
from qtoggleserver.utils import dynload as dynload_utils
from qtoggleserver.utils import json as json_utils

from .base import BaseDriver
from .typing import Id, Record, Sample, SampleValue


logger = logging.getLogger(__name__)

_thread_local: threading.local = threading.local()


async def _get_driver() -> BaseDriver:
    if not hasattr(_thread_local, "driver"):
        driver_args = conf_utils.obj_to_dict(settings.persist)
        driver_class_path = driver_args.pop("driver")

        try:
            logger.debug("loading persistence driver %s", driver_class_path)
            driver_class = dynload_utils.load_attr(driver_class_path)
            driver = driver_class(**driver_args)
            await driver.init()
            _thread_local.driver = driver
        except Exception as e:
            logger.error("failed to load persistence driver %s: %s", driver_class_path, e, exc_info=True)

            raise

    return _thread_local.driver


async def query(
    collection: str,
    fields: list[str] | None = None,
    filt: dict[str, Any] | None = None,
    sort: str | list[str] | None = None,
    limit: int | None = None,
) -> Iterable[Record]:
    """Return records from `collection`.

    Optionally project the returned records by only returning given `fields`.

    Filter records according to `filt`. Besides filtering by exact field value, the following filter operators are
    supported: `gt`, `ge`, `lt`, `le` and `in` (list of values).

    Sort results according to `sort` argument which is a list of fields optionally preceded by `-` for descending sort.

    Optionally limit the number of returned records to `limit`."""

    if logger.getEffectiveLevel() <= logging.DEBUG:
        logger.debug(
            "querying %s (%s) where %s (sort=%s, limit=%s)",
            collection,
            json_utils.dumps(fields) if fields else "all fields",
            json_utils.dumps(filt, extra_types=json_utils.EXTRA_TYPES_EXTENDED),
            json_utils.dumps(sort),
            json_utils.dumps(limit),
        )

    filt = filt or {}
    sort = sort or []
    if isinstance(sort, str):
        sort = [sort]

    # Transform '-field' into (field, descending)
    sort_tuples = [(s[1:], True) if s.startswith("-") else (s, False) for s in sort]

    driver = await _get_driver()
    return await driver.query(collection, fields, filt, sort_tuples, limit)


async def get(collection: str, id_: Id) -> Record | None:
    """Return the record with a given `id` from `collection`.

    If no such record is found, `None` is returned."""

    logger.debug("getting record with id %s from %s", id_, collection)

    driver = await _get_driver()
    records = list(await driver.query(collection, fields=None, filt={"id": id_}, sort=[], limit=1))
    if len(records) > 1:
        logger.warning("more than one record with same id %s found in collection %s", id_, collection)

    if records:
        return records[0]

    return None


async def get_value(name: str, default: Any | None = None) -> Any:
    """Return the value of object with name `name` by querying the collection with the same name and considering the
    first (and only) record.

    If no such record is found, `default` is returned."""

    logger.debug("getting value of %s", name)

    driver = await _get_driver()
    records = list(await driver.query(name, fields=None, filt={}, sort=[], limit=2))
    if len(records) > 1:
        logger.warning("more than one record found in single-value collection %s", name)
        record = records[0]
    elif len(records) > 0:
        record = records[0]
    else:
        return default

    return record["value"]


async def set_value(name: str, value: Any) -> None:
    """Set the value of object with name `name` by inserting into or updating the collection with the same name and
    considering the fist (and only) record."""

    if logger.getEffectiveLevel() <= logging.DEBUG:
        logger.debug("setting %s to %s", name, json_utils.dumps(value, extra_types=json_utils.EXTRA_TYPES_EXTENDED))

    driver = await _get_driver()
    record = {"value": value}

    records = list(await driver.query(name, fields=["id"], filt={}, sort=[], limit=2))
    if len(records) > 1:
        logger.warning("more than one record found in single-value collection %s", name)

        id_ = records[0]["id"]
    elif len(records) > 0:
        id_ = records[0]["id"]

    else:
        id_ = None

    if id_ is None:
        await driver.insert(name, record)

    else:
        await driver.replace(name, id_, record)


async def insert(collection: str, record: Record) -> Id:
    """Insert `record` into `collection`.

    Return the associated record ID."""

    if logger.getEffectiveLevel() <= logging.DEBUG:
        logger.debug(
            "inserting %s into %s", json_utils.dumps(record, extra_types=json_utils.EXTRA_TYPES_EXTENDED), collection
        )

    driver = await _get_driver()
    return await driver.insert(collection, record)


async def update(collection: str, record_part: Record, filt: dict[str, Any] | None = None) -> int:
    """Update records from `collection` with fields given in `record_part`.

    Only records that match the `filt` filter will be updated. Besides filtering by exact field value, the following
    filter operators are supported: `gt`, `ge`, `lt`, `le` and `in` (list of values).

    Return the total number of records that were updated."""

    if logger.getEffectiveLevel() <= logging.DEBUG:
        logger.debug(
            "updating %s where %s with %s",
            collection,
            json_utils.dumps(filt or {}, extra_types=json_utils.EXTRA_TYPES_EXTENDED),
            json_utils.dumps(record_part, extra_types=json_utils.EXTRA_TYPES_EXTENDED),
        )

    driver = await _get_driver()
    count = await driver.update(collection, record_part, filt or {})

    logger.debug("modified %s records in %s", count, collection)

    return count


async def replace(collection: str, id_: Id, record: Record) -> bool:
    """Replace record with `id` in `collection`.

    Return `True` if matched and replaced."""

    if logger.getEffectiveLevel() <= logging.DEBUG:
        logger.debug(
            "replacing record with id %s with %s in %s",
            id_,
            json_utils.dumps(record, extra_types=json_utils.EXTRA_TYPES_EXTENDED),
            collection,
        )

    record = dict(record, id=id_)  # make sure the new record contains the id field
    driver = await _get_driver()
    replaced = await driver.replace(collection, id_, record)
    if replaced:
        logger.debug("replaced record with id %s in %s", id_, collection)

        return False

    else:
        await driver.insert(collection, dict(record, id=id_))
        logger.debug("inserted record with id %s in %s", id_, collection)

        return True


async def remove(collection: str, filt: dict[str, Any] | None = None) -> int:
    """Remove records from `collection`.

    Only records that match the `filt` filter will be removed. Besides filtering by exact field value, the following
    filter operators are supported: `gt`, `ge`, `lt`, `le` and `in` (list of values).

    Return the total number of records that were removed."""

    if logger.getEffectiveLevel() <= logging.DEBUG:
        logger.debug(
            "removing from %s where %s",
            collection,
            json_utils.dumps(filt or {}, extra_types=json_utils.EXTRA_TYPES_EXTENDED),
        )

    driver = await _get_driver()
    count = await driver.remove(collection, filt or {})

    logger.debug("removed %s records from %s", count, collection)

    return count


async def get_samples_slice(
    collection: str,
    obj_id: Id,
    from_timestamp: int | None = None,
    to_timestamp: int | None = None,
    limit: int | None = None,
    sort_desc: bool = False,
) -> Iterable[Sample]:
    """Return the samples of `obj_id` from `collection`.

    Filter results by an interval of time, if `from_timestamp` and/or `to_timestamp` are not `None`.
    `from_timestamp` is inclusive, while `to_timestamp` is exclusive.

    Optionally limit results to `limit` number of records, if not `None`.

    Sort the results by timestamp according to the value of `sort_desc`."""

    if logger.getEffectiveLevel() <= logging.DEBUG:
        logger.debug(
            "getting samples of object %s from %s between %s and %s (sort=%s, limit=%s)",
            obj_id,
            collection,
            json_utils.dumps(from_timestamp),
            json_utils.dumps(to_timestamp),
            ["asc", "desc"][sort_desc],
            json_utils.dumps(limit),
        )

    driver = await _get_driver()
    return await driver.get_samples_slice(collection, obj_id, from_timestamp, to_timestamp, limit, sort_desc)


async def get_samples_by_timestamp(collection: str, obj_id: Id, timestamps: list[int]) -> Iterable[SampleValue]:
    """For each timestamp in `timestamps`, return the sample of `obj_id` from `collection` that was saved right
    before the (or at the exact) timestamp.
    """

    if logger.getEffectiveLevel() <= logging.DEBUG:
        logger.debug(
            "getting samples of object %s from %s for %d timestamps",
            obj_id,
            collection,
            len(timestamps),
        )

    driver = await _get_driver()
    return await driver.get_samples_by_timestamp(collection, obj_id, timestamps)


async def save_sample(collection: str, obj_id: Id, timestamp: int, value: SampleValue) -> None:
    """Save a sample of an object with `obj_id` at a given `timestamp` to a specified `collection`."""

    if logger.getEffectiveLevel() <= logging.DEBUG:
        logger.debug(
            "saving sample value %s of object %s at %s into %s",
            json_utils.dumps(value),
            obj_id,
            timestamp,
            collection,
        )

    driver = await _get_driver()
    return await driver.save_sample(collection, obj_id, timestamp, value)


async def remove_samples(
    collection: str,
    obj_ids: list[Id] | None = None,
    from_timestamp: int | None = None,
    to_timestamp: int | None = None,
) -> int:
    """Remove samples from `collection`.

    If `obj_ids` is not `None`, only remove samples of given object ids.

    If `from_timestamp` and/or `to_timestamp` are not `None`, only remove samples within specified interval of time.
    `from_timestamp` is inclusive, while `to_timestamp` is exclusive.

    Return the number of removed samples."""

    if logger.getEffectiveLevel() <= logging.DEBUG:
        logger.debug(
            "removing samples of objects (%s) between %s and %s from %s",
            ", ".join(obj_ids) if obj_ids else "all objects",
            json_utils.dumps(from_timestamp),
            json_utils.dumps(to_timestamp),
            collection,
        )

    driver = await _get_driver()
    count = await driver.remove_samples(collection, obj_ids, from_timestamp, to_timestamp)
    logger.debug("removed %s samples", count, collection)

    return count


def is_samples_supported() -> bool:
    """Tell whether samples are supported by the current persistence driver or not."""

    # We need this function to *not* be async, therefore we try to obtain a reference to the existing driver rather than
    # calling the async function `_get_driver()`. We rely on the fact that it will always be called after driver
    # initialization and thus the `_thread_local` variable will have the `driver` attribute set.
    driver = getattr(_thread_local, "driver", None)
    if not driver:
        return False

    return driver.is_samples_supported()


async def ensure_index(collection: str, index: str | list[str] | None = None) -> None:
    """Create an index on `collection` if not already present.

    `index` is a list of field names optionally preceded by a `-` sign for a descending index.

    If `index` is `None`, the collection is assumed to be a collection of samples where the index is considered to
    be ascending on the timestamp field."""

    if isinstance(index, str):
        index = [index]

    # Transform '-field' into (field, descending)
    index_tuples = []
    if index:
        index_tuples = [(i[1:], True) if i.startswith("-") else (i, False) for i in index]

    if logger.getEffectiveLevel() <= logging.DEBUG:
        logger.debug("ensuring index %s in %s", json_utils.dumps(index_tuples), collection)

    driver = await _get_driver()
    await driver.ensure_index(collection, index_tuples)


async def init() -> None:
    """Initialize the persistence subsystem."""

    driver = await _get_driver()

    # Do a dummy query so that if there's any problem in querying the collection, an exception is raised now.
    await driver.query("device", fields=None, filt={}, sort=[], limit=1)


async def cleanup() -> None:
    """Clean up the persistence subsystem."""

    driver = await _get_driver()
    await driver.cleanup()
    _thread_local.driver = None
