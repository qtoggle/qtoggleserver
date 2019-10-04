
import logging
import pymongo
import re

from bson import ObjectId

from qtoggleserver.persist import BaseDriver


logger = logging.getLogger(__name__)

_OBJECT_ID_RE = re.compile('^[0-9a-f]{24}$')


class MongoDriver(BaseDriver):
    def __init__(self, host, port, db, **kwargs):
        logger.debug('connecting to %s:%s/%s', host, port, db)

        self._client = pymongo.MongoClient(host, port, serverSelectionTimeoutMS=200)
        self._db = self._client[db]

    def query(self, collection, fields, filt, limit):
        if fields:
            fields = dict((f, 1) for f in fields)
            if 'id' in fields:
                fields['_id'] = 1

            else:
                fields['_id'] = 0

        if 'id' in filt:
            filt = dict(filt)
            filt['_id'] = self._id_to_db(filt.pop('id'))

        q = self._db[collection].find(filt, fields)
        if limit is not None:
            q = q.limit(limit)

        return self._query_gen_wrapper(q)

    def insert(self, collection, record):
        if 'id' in record:
            record = dict(record)
            record['_id'] = self._id_to_db(record.pop('id'))

        return self._db[collection].insert_one(record).inserted_id

    def update(self, collection, record_part, filt):
        if 'id' in record_part:
            record_part = dict(record_part)
            record_part['_id'] = self._id_to_db(record_part.pop('id'))

        if 'id' in filt:
            filt = dict(filt)
            filt['_id'] = self._id_to_db(filt.pop('id'))

        return self._db[collection].update_many(filt, {'$set': record_part}, upsert=False).modified_count

    def replace(self, collection, _id, record, upsert):
        record = dict(record)
        record.pop('id', None)
        record['_id'] = self._id_to_db(_id)

        return bool(self._db[collection].replace_one({'_id': record['_id']}, record, upsert=upsert).modified_count)

    def remove(self, collection, filt=None):
        if 'id' in filt:
            filt = dict(filt)
            filt['_id'] = self._id_to_db(filt.pop('id'))

        return self._db[collection].delete_many(filt).deleted_count

    def close(self):
        logger.debug('disconnecting mongo client')

        self._client.close()

    @classmethod
    def _query_gen_wrapper(cls, q):
        for r in q:
            if '_id' in r:
                r['id'] = cls._id_from_db(r.pop('_id'))

            yield r

    @staticmethod
    def _id_to_db(_id):
        if isinstance(_id, str) and _OBJECT_ID_RE.match(_id):
            return ObjectId(_id)

        else:
            return _id

    @staticmethod
    def _id_from_db(_id):
        if isinstance(_id, ObjectId):
            return str(_id)

        else:
            return _id
