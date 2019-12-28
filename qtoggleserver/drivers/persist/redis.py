
import logging
import redis

from qtoggleserver.persist import BaseDriver
from qtoggleserver.utils import json as json_utils


logger = logging.getLogger(__name__)


class DuplicateRecordId(redis.RedisError):
    pass


class RedisDriver(BaseDriver):
    def __init__(self, host, port, db, **kwargs):
        logger.debug('connecting to %s:%s/%s', host, port, db)

        self._client = redis.StrictRedis(host=host, port=port, db=db, encoding='utf8', decode_responses=True)

    def query(self, collection, fields, filt, limit):
        db_records = []

        if 'id' in filt:  # Look for specific record id
            filt = dict(filt)
            _id = filt.pop('id')
            db_record = self._client.hgetall(self._make_record_key(collection, _id))

            # Apply filter criteria
            if db_record and self._filter_matches(db_record, filt):
                db_record['id'] = _id
                db_records.append(db_record)

        else:
            # Look through all records from this collection, iterating through set
            for _id in self._client.sscan_iter(self._make_set_key(collection)):
                # Retrieve the db record
                db_record = self._client.hgetall(self._make_record_key(collection, _id))
                db_record['id'] = _id

                # Apply filter criteria
                if self._filter_matches(db_record, filt):
                    db_records.append(db_record)

        # Apply limit
        if limit is not None:
            db_records = db_records[:limit]

        # Transform from db record and return
        return (self._record_from_db(dbr) for dbr in db_records)

    def insert(self, collection, record):
        # Make sure we have an id
        record = dict(record)
        _id = record.pop('id', None)
        if _id is None:
            _id = self._get_next_id(collection)

        key = self._make_record_key(collection, _id)
        set_key = self._make_set_key(collection)

        # Check for duplicates
        if self._client.sismember(set_key, _id):
            raise DuplicateRecordId(_id)

        # Adapt the record to db
        db_record = self._record_to_db(record)

        # Actually insert the record
        self._client.hmset(key, db_record)

        # Add the id to set
        self._client.sadd(set_key, _id)

    def update(self, collection, record_part, filt):
        # Adapt the record part to db
        db_record_part = self._record_to_db(record_part)

        modified_count = 0

        if 'id' in filt:
            filt = dict(filt)
            _id = filt.pop('id')
            key = self._make_record_key(collection, _id)

            # Retrieve the db record
            db_record = self._client.hgetall(key)
            if db_record and self._filter_matches(db_record, filt):
                self._client.hmset(key, db_record_part)

            modified_count = 1

        else:  # No id in filt
            # Look through all records from this collection, iterating through set
            for _id in self._client.sscan_iter(self._make_set_key(collection)):
                key = self._make_record_key(collection, _id)

                # Retrieve the db record
                db_record = self._client.hgetall(key)

                # Apply filter criteria
                if not self._filter_matches(db_record, filt):
                    continue

                # Actually update the record
                self._client.hmset(key, db_record_part)

                modified_count += 1

        return modified_count

    def replace(self, collection, _id, record, upsert):
        # Adapt the record to db
        new_db_record = self._record_to_db(record)
        new_db_record.pop('id', None)  # Never add the id together with other fields

        key = self._make_record_key(collection, _id)
        old_db_record = self._client.hgetall(key)

        if not old_db_record and not upsert:
            return False  # No record found, no replacing

        # Remove any existing record
        self._client.delete(key)

        # Insert the new record
        self._client.hmset(key, new_db_record)

        # Make sure the id is present in set
        self._client.sadd(self._make_set_key(collection), _id)

        return True

    def remove(self, collection, filt):
        removed_count = 0

        if 'id' in filt:
            filt = dict(filt)
            _id = filt.pop('id')
            key = self._make_record_key(collection, _id)
            db_record = self._client.hgetall(key)

            # Actually remove the record
            if db_record and self._filter_matches(db_record, filt):
                self._client.delete(key)
                removed_count = 1

            # Remove the id from set
            self._client.srem(self._make_set_key(collection), _id)

        else:  # No id in filt
            ids_to_remove = set()

            # Look through all records from this collection, iterating through set
            for _id in self._client.sscan_iter(self._make_set_key(collection)):
                key = self._make_record_key(collection, _id)

                # Retrieve the db record
                db_record = self._client.hgetall(key)

                # Apply filter criteria
                if not self._filter_matches(db_record, filt):
                    continue

                # Actually remove the record
                self._client.delete(key)

                # Remember ids to remove from set
                ids_to_remove.add(_id)

                removed_count += 1

            # Remove the ids from set
            for _id in ids_to_remove:
                self._client.srem(self._make_set_key(collection), _id)

        return removed_count

    def close(self):
        pass

    def _filter_matches(self, db_record, filt):
        for key, value in filt.items():
            try:
                if db_record[key] != self._value_to_db(value):
                    return False

            except KeyError:
                return False

        return True

    def _get_next_id(self, collection):
        return int(self._client.incr(self._make_sequence_key(collection)))

    @classmethod
    def _record_from_db(cls, db_record):
        return {k: (cls._value_from_db(v) if k != 'id' else v) for k, v in db_record.items()}

    @classmethod
    def _record_to_db(cls, record):
        return {k: (cls._value_to_db(v) if k != 'id' else v) for k, v in record.items()}

    @staticmethod
    def _value_to_db(value):
        return json_utils.dumps(value)

    @staticmethod
    def _value_from_db(value):
        return json_utils.loads(value)

    @staticmethod
    def _make_record_key(collection, _id):
        if _id:
            return '{}:{}'.format(collection, _id)

        else:
            return collection

    @staticmethod
    def _make_set_key(collection):
        return '{}-id-set'.format(collection)

    @staticmethod
    def _make_sequence_key(collection):
        return '{}-id-sequence'.format(collection)
