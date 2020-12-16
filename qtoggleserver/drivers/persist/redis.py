
import logging
import operator

from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

import redis

from qtoggleserver.core.typing import GenericJSONDict
from qtoggleserver.persist import BaseDriver
from qtoggleserver.persist.typing import Id, Record
from qtoggleserver.utils import json as json_utils


FILTER_OP_MAPPING = {
    'gt': operator.gt,
    'ge': operator.ge,
    'lt': operator.lt,
    'le': operator.le,
    'in': lambda a, b: a in b
}

logger = logging.getLogger(__name__)


class DuplicateRecordId(redis.RedisError):
    pass


class RedisDriver(BaseDriver):
    def __init__(
        self,
        host: str = '127.0.0.1',
        port: int = 6379,
        db: int = 0,
        history_support: bool = False,
        **kwargs
    ) -> None:
        logger.debug('connecting to %s:%s/%s', host, port, db)

        self._client: redis.Redis = redis.StrictRedis(
            host=host,
            port=port,
            db=db,
            encoding='utf8',
            decode_responses=True
        )

        self._history_support: bool = history_support

    async def query(
        self,
        collection: str,
        fields: Optional[List[str]],
        filt: Dict[str, Any],
        sort: List[Tuple[str, bool]],
        limit: Optional[int]
    ) -> Iterable[Record]:

        db_records = []

        if isinstance(filt.get('id'), Id):  # Look for specific record id
            filt = dict(filt)
            id_ = filt.pop('id')
            db_record = self._client.hgetall(self._make_record_key(collection, id_))

            # Apply filter criteria
            if db_record and self._filter_matches(db_record, filt):
                db_record['id'] = id_
                db_records.append(db_record)

        else:  # No single specific id in filt
            # Look through all records from this collection, iterating through set
            for id_ in self._client.sscan_iter(self._make_set_key(collection)):
                # Retrieve the db record
                db_record = self._client.hgetall(self._make_record_key(collection, id_))
                db_record['id'] = id_

                # Apply filter criteria
                if self._filter_matches(db_record, filt):
                    db_records.append(db_record)

        # Sort
        for field, rev in reversed(sort):
            if field == 'id':
                db_records.sort(key=lambda r: int(r['id']), reverse=rev)

            else:
                db_records.sort(key=lambda r: self._value_from_db(r.get(field)), reverse=rev)

        # Apply limit
        if limit is not None:
            db_records = db_records[:limit]

        # Transform from db record and return
        if fields is not None:
            fields = set(fields)

        return (self._record_from_db(dbr, fields) for dbr in db_records)

    async def insert(self, collection: str, record: Record) -> Id:
        # Make sure we have an id
        record = dict(record)
        id_ = record.pop('id', None)
        if id_ is None:
            id_ = self._get_next_id(collection)

        key = self._make_record_key(collection, id_)
        set_key = self._make_set_key(collection)

        # Check for duplicates
        if self._client.sismember(set_key, id_):
            raise DuplicateRecordId(id_)

        # Adapt the record to db
        db_record = self._record_to_db(record)

        # Actually insert the record, but only if it's not empty
        if db_record:
            self._client.hset(key, mapping=db_record)

        # Add the id to set
        self._client.sadd(set_key, id_)

        return id_

    async def update(self, collection: str, record_part: Record, filt: Dict[str, Any]) -> int:
        # Adapt the record part to db
        db_record_part = self._record_to_db(record_part)

        modified_count = 0

        if isinstance(filt.get('id'), Id):
            filt = dict(filt)
            id_ = filt.pop('id')
            key = self._make_record_key(collection, id_)

            # Retrieve the db record
            db_record = self._client.hgetall(key)
            if db_record and self._filter_matches(db_record, filt):
                self._client.hset(key, mapping=db_record_part)
                modified_count = 1

        else:  # No single specific id in filt
            # Look through all records from this collection, iterating through set
            for id_ in self._client.sscan_iter(self._make_set_key(collection)):
                key = self._make_record_key(collection, id_)

                # Retrieve the db record
                db_record = self._client.hgetall(key)
                db_record['id'] = id_

                # Apply filter criteria
                if not self._filter_matches(db_record, filt):
                    continue

                # Actually update the record
                if db_record_part:
                    self._client.hset(key, mapping=db_record_part)

                else:
                    self._client.delete(key)

                modified_count += 1

        return modified_count

    async def replace(self, collection: str, id_: Id, record: Record) -> bool:
        # Adapt the record to db
        new_db_record = self._record_to_db(record)
        new_db_record.pop('id', None)  # Never add the id together with other fields

        skey = self._make_set_key(collection)
        key = self._make_record_key(collection, id_)

        if not self._client.sismember(skey, id_):
            return False  # No record found, no replacing

        # Remove existing record
        self._client.delete(key)

        # Insert the new record, if not empty
        if new_db_record:
            self._client.hset(key, mapping=new_db_record)

        # Make sure the id is present in set
        self._client.sadd(skey, id_)

        return True

    async def remove(self, collection: str, filt: Dict[str, Any]) -> int:
        removed_count = 0

        if isinstance(filt.get('id'), Id):
            filt = dict(filt)
            id_ = filt.pop('id')
            key = self._make_record_key(collection, id_)
            db_record = self._client.hgetall(key)

            # Actually remove the record
            if db_record and self._filter_matches(db_record, filt):
                self._client.delete(key)
                removed_count = 1

            # Remove the id from set
            self._client.srem(self._make_set_key(collection), id_)

        else:  # No single specific id in filt
            ids_to_remove = set()

            # Look through all records from this collection, iterating through set
            for id_ in self._client.sscan_iter(self._make_set_key(collection)):
                key = self._make_record_key(collection, id_)

                # Retrieve the db record
                db_record = self._client.hgetall(key)
                db_record['id'] = id_

                # Apply filter criteria
                if not self._filter_matches(db_record, filt):
                    continue

                # Actually remove the record
                self._client.delete(key)

                # Remember ids to remove from set
                ids_to_remove.add(id_)

                removed_count += 1

            # Remove the ids from set
            for id_ in ids_to_remove:
                self._client.srem(self._make_set_key(collection), id_)

        return removed_count

    async def cleanup(self) -> None:
        logger.debug('disconnecting redis client')

        self._client.close()

    def is_history_supported(self) -> bool:
        return self._history_support

    def _filter_matches(self, db_record: GenericJSONDict, filt: Dict[str, Any]) -> bool:
        for key, value in filt.items():
            try:
                db_record_value = db_record[key]

            except KeyError:
                return False

            if key == 'id':
                record_value = db_record_value

            else:
                record_value = self._value_from_db(db_record_value)

            if not self._filter_value_matches(record_value, value):
                return False

        return True

    @staticmethod
    def _filter_value_matches(record_value: Any, filt_value: Any) -> bool:
        if isinstance(filt_value, dict):  # filter with operators
            for op, v in filt_value.items():
                op_func = FILTER_OP_MAPPING[op]
                if not op_func(record_value, v):
                    return False

            return True

        else:  # Assuming simple value
            return record_value == filt_value

    def _get_next_id(self, collection: str) -> Id:
        return str(self._client.incr(self._make_sequence_key(collection)))

    @classmethod
    def _record_from_db(cls, db_record: GenericJSONDict, fields: Optional[Set[str]] = None) -> Record:
        if fields is not None:
            return {k: (cls._value_from_db(v) if k != 'id' else v) for k, v in db_record.items() if k in fields}

        else:
            return {k: (cls._value_from_db(v) if k != 'id' else v) for k, v in db_record.items()}

    @classmethod
    def _record_to_db(cls, record: Record) -> GenericJSONDict:
        return {k: (cls._value_to_db(v) if k != 'id' else v) for k, v in record.items()}

    @staticmethod
    def _value_to_db(value: Any) -> str:
        return json_utils.dumps(value, allow_extended_types=True)

    @staticmethod
    def _value_from_db(value: str) -> Any:
        return json_utils.loads(value, allow_extended_types=True)

    @staticmethod
    def _make_record_key(collection: str, id_: Id) -> str:
        if id_:
            return f'{collection}:{id_}'

        else:
            return collection

    @staticmethod
    def _make_set_key(collection: str) -> str:
        return f'{collection}-id-set'

    @staticmethod
    def _make_sequence_key(collection: str) -> str:
        return f'{collection}-id-sequence'
