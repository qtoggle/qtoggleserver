
import logging
import re

from typing import Any, Dict, Iterable, List, Optional, Tuple, Union

import bson
import pymongo.database
import pymongo.errors

from qtoggleserver.persist import BaseDriver
from qtoggleserver.persist.typing import Id, Record


logger = logging.getLogger(__name__)

_OBJECT_ID_RE = re.compile('^[0-9a-f]{24}$')
DEFAULT_DB = 'qtoggleserver'

FILTER_OP_MAPPING = {
    'gt': '$gt',
    'ge': '$gte',
    'lt': '$lt',
    'le': '$lte',
    'in': '$in'
}


class MongoDriver(BaseDriver):
    def __init__(self, host: str = '127.0.0.1', port: str = 27017, db: str = DEFAULT_DB, **kwargs) -> None:
        logger.debug('connecting to %s:%s/%s', host, port, db)

        self._client: pymongo.MongoClient = pymongo.MongoClient(
            host,
            port,
            serverSelectionTimeoutMS=200,
            connectTimeoutMS=200
        )
        self._db: pymongo.database.Database = self._client[db]

    async def query(
        self,
        collection: str,
        fields: Optional[List[str]],
        filt: Dict[str, Any],
        sort: List[Tuple[str, bool]],
        limit: Optional[int]
    ) -> Iterable[Record]:

        if fields:
            fields = dict((f, 1) for f in fields)
            if 'id' in fields:
                fields['_id'] = 1

            else:
                fields['_id'] = 0

        if 'id' in filt:
            filt = dict(filt)
            filt['_id'] = self._id_to_db_rec(filt.pop('id'))

        db_filt = self._filt_to_db(filt)

        q = self._db[collection].find(db_filt, fields)

        if len(sort) > 0:
            sort = [(f, [pymongo.ASCENDING, pymongo.DESCENDING][r]) for f, r in sort]
            q = q.sort(sort)

        if limit is not None:
            q = q.limit(limit)

        return self._query_gen_wrapper(q)

    async def insert(self, collection: str, record: Record) -> Id:
        record = dict(record)
        if 'id' in record:
            record['_id'] = self._id_to_db(record.pop('id'))

        return self._id_from_db(self._db[collection].insert_one(record).inserted_id)

    async def update(self, collection: str, record_part: Record, filt: Dict[str, Any]) -> int:
        if 'id' in record_part:
            record_part = dict(record_part)
            record_part['_id'] = self._id_to_db(record_part.pop('id'))

        if 'id' in filt:
            filt = dict(filt)
            filt['_id'] = self._id_to_db_rec(filt.pop('id'))

        db_filt = self._filt_to_db(filt)

        return self._db[collection].update_many(db_filt, {'$set': record_part}, upsert=False).modified_count

    async def replace(self, collection: str, id_: Id, record: Record) -> bool:
        record = dict(record)
        id_ = self._id_to_db(id_)
        record['_id'] = id_

        matched = self._db[collection].replace_one({'_id': id_}, record, upsert=False).matched_count

        return matched > 0

    async def remove(self, collection: str, filt: Dict[str, Any]) -> int:
        if 'id' in filt:
            filt = dict(filt)
            filt['_id'] = self._id_to_db_rec(filt.pop('id'))

        db_filt = self._filt_to_db(filt)

        return self._db[collection].delete_many(db_filt).deleted_count

    async def ensure_index(self, collection: str, index: List[Tuple[str, bool]]) -> None:
        index = [(f, [pymongo.ASCENDING, pymongo.DESCENDING][r]) for f, r in index]

        try:
            self._db[collection].create_index(index)

        except pymongo.errors.DuplicateKeyError:
            logger.debug('index already exists')

    async def cleanup(self) -> None:
        logger.debug('disconnecting mongo client')

        self._client.close()

    def is_history_supported(self) -> bool:
        return True

    @classmethod
    def _query_gen_wrapper(cls, q: Iterable[Record]) -> Iterable[Record]:
        for r in q:
            if '_id' in r:
                r['id'] = cls._id_from_db(r.pop('_id'))

            yield r

    @staticmethod
    def _id_to_db(id_: str) -> Union[str, bson.ObjectId]:
        if isinstance(id_, str) and _OBJECT_ID_RE.match(id_):
            return bson.ObjectId(id_)

        else:
            return id_

    @staticmethod
    def _id_from_db(id_: Union[str, bson.ObjectId]) -> str:
        if isinstance(id_, bson.ObjectId):
            return str(id_)

        else:
            return id_

    def _id_to_db_rec(self, obj: Union[Dict, List, str]) -> Union[Dict, List, bson.ObjectId]:
        if isinstance(obj, dict):
            return {key: self._id_to_db_rec(value) for key, value in obj.items()}

        elif isinstance(obj, list):
            return [self._id_to_db(value) for value in obj]

        else:  # Assuming str
            return self._id_to_db(obj)

    @staticmethod
    def _filt_to_db(filt: Dict[str, Any]) -> Dict[str, Any]:
        db_filt = {}
        for key, value in filt.items():
            if isinstance(value, dict):  # filter with operators
                value = {FILTER_OP_MAPPING[k]: v for k, v in value.items()}

            db_filt[key] = value

        return db_filt
