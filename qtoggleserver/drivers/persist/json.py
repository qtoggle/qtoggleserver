
import copy
import logging
import os

from typing import Any, Dict, Iterable, List, Optional

from qtoggleserver.conf import settings
from qtoggleserver.persist import BaseDriver, Id, Record
from qtoggleserver.utils import json as json_utils


DEFAULT_FILE_PATH = 'qtoggleserver-data.json'

logger = logging.getLogger(__name__)

Collection = Dict[int, Record]
IndexedData = Dict[str, Collection]
UnindexedData = Dict[str, List[Record]]


class JSONPersistError(Exception):
    pass


class DuplicateRecordId(JSONPersistError):
    pass


class JSONDriver(BaseDriver):
    def __init__(
        self,
        file_path: str = DEFAULT_FILE_PATH,
        pretty_format: Optional[bool] = None,
        use_backup: bool = True,
        **kwargs
    ) -> None:

        # Pretty formatting follows general debug flag, by default
        if pretty_format is None:
            pretty_format = settings.debug

        self._file_path: str = file_path
        self._pretty_format: bool = pretty_format
        self._use_backup: bool = use_backup

        self._data: IndexedData = self._index(self._load())

    def query(
        self,
        collection: str,
        fields: Optional[List[str]],
        filt: Dict[str, Any],
        limit: Optional[int]
    ) -> Iterable[Record]:

        coll = self._data.get(collection, {})
        records = []

        if 'id' in filt:  # Look for specific record id
            filt = dict(filt)
            id_ = filt.pop('id')
            record = coll.get(id_)

            # Apply filter criteria
            if record is not None and self._filter_matches(record, filt):
                records.append(record)

        else:
            for record in coll.values():
                # Apply filter criteria
                if self._filter_matches(record, filt):
                    records.append(record)

        # Apply limit
        if limit is not None:
            records = records[:limit]

        # Apply projection
        if fields is not None:
            fields = set(fields)
            projected_records = []
            for record in records:
                projected_record = {k: v for k, v in record.items() if k in fields}
                projected_records.append(projected_record)

            records = projected_records

        return copy.deepcopy(records)

    def insert(self, collection: str, record: Record) -> Id:
        coll = self._data.setdefault(collection, {})

        id_ = record.get('id')
        if id_ is None:
            id_ = self._find_next_id(coll)
            record = dict(record, id=id_)

        elif id_ in coll:
            raise DuplicateRecordId(id_)

        coll[id_] = record

        self._save(self._unindex(self._data))

        return id_

    def update(self, collection: str, record_part: Record, filt: Dict[str, Any]) -> int:
        coll = self._data.setdefault(collection, {})
        modified_count = 0

        if 'id' in filt:
            filt = dict(filt)
            id_ = filt.pop('id')

            record = coll.get(id_)
            if record is not None:
                record.update(record_part)
                modified_count = 1

        else:  # No id in filt
            for record in coll.values():
                # Apply filter criteria
                if not self._filter_matches(record, filt):
                    continue

                # Actually update the record
                record.update(record_part)
                modified_count += 1

        self._save(self._unindex(self._data))

        return modified_count

    def replace(self, collection: str, id_: Id, record: Record, upsert: bool) -> bool:
        coll = self._data.setdefault(collection, {})

        record_existed = coll.get(id_) is not None
        if record_existed is None and not upsert:
            return False  # No record found, no replacing

        # Remove old id if a new id is supplied
        new_id = record.get('id', None)
        if (new_id is not None) and (new_id != id_) and record_existed:
            coll.pop(id_)

        if new_id is None:
            new_id = id_
            record['id'] = id_

        coll[new_id] = record

        self._save(self._unindex(self._data))

        return record_existed

    def remove(self, collection: str, filt: Dict[str, Any]) -> int:
        coll = self._data.setdefault(collection, {})
        removed_count = 0

        if 'id' in filt:
            filt = dict(filt)
            id_ = filt.pop('id')

            record = coll.get(id_)
            if (record is not None) and self._filter_matches(record, filt):
                coll.pop(id_)
                removed_count = 1

        else:  # No id in filt
            for id_, record in list(coll.items()):
                # Apply filter criteria
                if not self._filter_matches(record, filt):
                    continue

                # Actually remove the record
                coll.pop(id_)
                removed_count += 1

        self._save(self._unindex(self._data))

        return removed_count

    def cleanup(self) -> None:
        pass

    @staticmethod
    def _filter_matches(record: Record, filt: Dict[str, Any]) -> bool:
        for key, value in filt.items():
            try:
                if record[key] != value:
                    return False

            except KeyError:
                return False

        return True

    @staticmethod
    def _find_next_id(coll: Collection) -> Id:
        int_ids = [int(id_) for id_ in coll.keys() if id_]
        int_ids.append(0)

        return str(max(int_ids) + 1)

    def _get_backup_file_path(self) -> str:
        path, ext = os.path.splitext(self._file_path)
        return f'{path}_backup{ext}'

    def _load(self) -> UnindexedData:
        logger.debug('loading from %s', self._file_path)

        try:
            # If the file is accessible but empty, consider data loaded and return empty dictionary
            if os.stat(self._file_path).st_size == 0:
                logger.debug('file %s is empty', self._file_path)
                return {}

        except FileNotFoundError:
            # If the file does not exist, consider data loaded and return empty dictionary
            logger.debug('file %s does not exist', self._file_path)
            return {}

        try:
            with open(self._file_path, 'rb') as f:
                data = f.read()
                return json_utils.loads(data, allow_extended_types=True)

        except Exception as e:
            if not self._use_backup:
                raise

            # Upon failure, if using a backup, simply log the error and attempt to load from backup file
            logger.error('failed to load from %s: %s', self._file_path, e, exc_info=True)

            backup_file_path = self._get_backup_file_path()
            logger.warning('loading from backup %s', backup_file_path)

            with open(backup_file_path, 'rb') as f:
                return json_utils.loads(f.read(), allow_extended_types=True)

    def _save(self, data: UnindexedData) -> None:
        if self._use_backup and os.path.exists(self._file_path):
            backup_file_path = self._get_backup_file_path()
            logger.debug('backing up %s to %s', self._file_path, backup_file_path)
            os.rename(self._file_path, backup_file_path)

        logger.debug('saving to %s', self._file_path)

        with open(self._file_path, 'wb') as f:
            data = json_utils.dumps(data, allow_extended_types=True, indent=4 if self._pretty_format else None)
            f.write(data.encode())

    @staticmethod
    def _index(data: UnindexedData) -> IndexedData:
        indexed_data = {}
        for coll, records in data.items():
            indexed_data[coll] = {r.get('id', ''): r for r in records}

        return indexed_data

    @staticmethod
    def _unindex(data: IndexedData) -> UnindexedData:
        unindexed_data = {}
        for coll, records in data.items():
            unindexed_data[coll] = list(records.values())

        return unindexed_data
