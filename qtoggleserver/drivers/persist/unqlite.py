
import asyncio
import datetime
import logging
import operator

from typing import Any, Dict, Iterable, List, Optional, Set, Tuple, Union

import unqlite

from qtoggleserver.core.typing import GenericJSONDict
from qtoggleserver.persist import BaseDriver
from qtoggleserver.persist.typing import Id, Record
from qtoggleserver.utils import json as json_utils


DEFAULT_FILE_PATH = 'qtoggleserver-data.unqlite'
DEFAULT_COMMIT_INTERVAL = 1  # seconds

FILTER_OP_MAPPING = {
    'gt': operator.gt,
    'ge': operator.ge,
    'lt': operator.lt,
    'le': operator.le,
    'in': lambda a, b: a in b
}

logger = logging.getLogger(__name__)


class DuplicateRecordId(Exception):
    pass


class UnQLiteDriver(BaseDriver):
    def __init__(
        self,
        file_path: str = DEFAULT_FILE_PATH,
        commit_interval: int = DEFAULT_COMMIT_INTERVAL,
        **kwargs
    ) -> None:
        logger.debug('using file %s', file_path)

        self._db: unqlite.UnQLite = unqlite.UnQLite(filename=file_path)
        self._commit_task: asyncio.Task = asyncio.create_task(self._commit_loop())
        self._commit_interval: int = commit_interval

    def query(
        self,
        collection: str,
        fields: Optional[List[str]],
        filt: Dict[str, Any],
        sort: List[Tuple[str, bool]],
        limit: Optional[int]
    ) -> Iterable[Record]:

        coll = self._get_collection(collection, create=False)
        if coll is None:
            return []

        if isinstance(filt.get('id'), Id):  # Look for specific record id
            filt = self._filter_to_db(filt)
            id_ = filt.pop('__id')
            db_record = coll.fetch(id_)

            # Apply filter criteria
            db_records = []
            if db_record and self._filter_matches(db_record, filt):
                db_records = [db_record]

        else:  # No single specific id in filt
            filt = self._filter_to_db(filt)

            # Look through all records from this collection
            db_records = coll.filter(lambda dbr: self._filter_matches(dbr, filt))

        # Sort
        for field, rev in reversed(sort):
            if not isinstance(db_records, list):
                db_records = list(db_records)

            if field == 'id':
                db_records.sort(key=lambda r: r['__id'], reverse=rev)

            else:
                db_records.sort(key=lambda r: self._value_from_db(r.get(field)), reverse=rev)

        # Apply limit
        if limit is not None:
            if not isinstance(db_records, list):
                db_records = list(db_records)

            db_records = db_records[:limit]

        # Transform from db record and return
        if fields is not None:
            fields = set(fields)
            if 'id' in fields:
                fields.remove('id')
                fields.add('__id')

        return self._query_gen_wrapper(self._record_from_db(dbr, fields) for dbr in db_records)

    def insert(self, collection: str, record: Record) -> Id:
        coll = self._get_collection(collection)

        # Adapt the record to db
        db_record = self._record_to_db(record)
        if 'id' in db_record:
            db_record['__id'] = self._id_to_db(db_record.pop('id'))

        # Actually insert the record
        if len(db_record) == 0:  # We can't insert empty objects into UnQLite
            db_record['__dummy'] = None

        id_ = coll.store(db_record, return_id=True)

        return self._id_from_db(id_)

    def update(self, collection: str, record_part: Record, filt: Dict[str, Any]) -> int:
        coll = self._get_collection(collection)

        # Adapt the record part to db
        db_record_part = self._record_to_db(record_part)

        modified_count = 0

        if isinstance(filt.get('id'), Id):
            filt = self._filter_to_db(filt)
            id_ = filt.pop('__id')
            db_record = coll.fetch(id_)

            # Apply filter criteria
            if db_record and self._filter_matches(db_record, filt):
                db_record.update(db_record_part)
                if coll.update(id_, db_record):
                    modified_count = 1

        else:  # No single specific id in filt
            filt = self._filter_to_db(filt)

            # Look through all records from this collection
            for db_record in coll.filter(lambda dbr: self._filter_matches(dbr, filt)):
                # Actually update the record
                db_record.update(db_record_part)
                coll.update(db_record['__id'], db_record)

                modified_count += 1

        return modified_count

    def replace(self, collection: str, id_: Id, record: Record) -> bool:
        coll = self._get_collection(collection)

        # Adapt the record to db
        db_record = self._record_to_db(record)
        db_record.pop('id', None)  # Never add the id together with other fields
        id_ = self._id_to_db(id_)

        return coll.update(id_, db_record)

    def remove(self, collection: str, filt: Dict[str, Any]) -> int:
        coll = self._get_collection(collection)

        removed_count = 0

        if isinstance(filt.get('id'), Id):
            filt = self._filter_to_db(filt)
            id_ = filt.pop('__id')

            db_record = coll.fetch(id_)
            if db_record and self._filter_matches(db_record, filt):
                try:
                    coll.delete(id_)
                    removed_count = 1

                except KeyError:
                    pass

        else:  # No single specific id in filt
            # Look through all records from this collection
            filt = self._filter_to_db(filt)

            for db_record in coll.filter(lambda dbr: self._filter_matches(dbr, filt)):
                # Apply filter criteria
                if not self._filter_matches(db_record, filt):
                    continue

                # Actually remove the record
                coll.delete(db_record['__id'])
                removed_count += 1

        return removed_count

    async def cleanup(self) -> None:
        if self._commit_task:
            self._commit_task.cancel()
            await self._commit_task

        self._db.close()

    def is_history_supported(self) -> bool:
        return True

    async def _commit_loop(self) -> None:
        while True:
            try:
                await asyncio.sleep(self._commit_interval)
                logger.debug('committing database')
                self._db.commit()

            except asyncio.CancelledError:
                logger.debug('commit task cancelled')
                break

            except Exception as e:
                logger.error('commit task error: %s', e, exc_info=True)

    def _get_collection(self, collection: str, create: bool = True) -> Optional[unqlite.Collection]:
        coll = self._db.collection(collection)
        if not coll.exists():
            if not create:
                return

            coll.create()

        return coll

    def _filter_matches(self, db_record: GenericJSONDict, filt: Dict[str, Any]) -> bool:
        for key, value in filt.items():
            try:
                db_record_value = db_record[key]

            except KeyError:
                return False

            record_value = self._value_from_db(db_record_value)
            if not self._filter_value_matches(record_value, value):
                return False

        return True

    @classmethod
    def _query_gen_wrapper(cls, q: Iterable[Record]) -> Iterable[Record]:
        for r in q:
            if '__id' in r:
                r['id'] = cls._id_from_db(r.pop('__id'))

            yield r

    @staticmethod
    def _id_to_db(id_: str) -> int:
        return int(id_)

    @staticmethod
    def _id_from_db(id_: int) -> str:
        return str(id_)

    def _id_to_db_rec(self, obj: Union[Dict, List, str]) -> Union[Dict, List, int]:
        if isinstance(obj, dict):
            return {key: self._id_to_db_rec(value) for key, value in obj.items()}

        elif isinstance(obj, list):
            return [self._id_to_db(value) for value in obj]

        else:  # Assuming str
            return self._id_to_db(obj)

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

    def _filter_to_db(self, filt: Dict[str, Any]) -> Dict[str, Any]:
        filt = dict(filt)
        for key, value in filt.items():
            if isinstance(value, dict):  # filter with operators
                for k, v in value.items():
                    value[k] = self._value_to_db(v)

        if 'id' in filt:
            filt['__id'] = self._id_to_db_rec(filt.pop('id'))

        return filt

    @classmethod
    def _record_from_db(cls, db_record: GenericJSONDict, fields: Optional[Set[str]] = None) -> Record:
        if fields is not None:
            return {k: (cls._value_from_db(v) if k != 'id' else v) for k, v in db_record.items() if k in fields}

        else:
            return {k: (cls._value_from_db(v) if k != 'id' else v) for k, v in db_record.items() if k != '__dummy'}

    @classmethod
    def _record_to_db(cls, record: Record) -> GenericJSONDict:
        return {k: (cls._value_to_db(v) if k != 'id' else v) for k, v in record.items()}

    @staticmethod
    def _value_to_db(value: Any) -> Any:
        # Special treatment for date/time objects
        if isinstance(value, (datetime.date, datetime.datetime)):
            return json_utils.encode_default_json(value)

        return value

    @staticmethod
    def _value_from_db(value: str) -> Any:
        # Special treatment for date/time objects
        if isinstance(value, dict):
            return json_utils.decode_json_hook(value)

        return value
