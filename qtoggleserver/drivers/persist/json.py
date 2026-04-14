import copy
import logging
import operator
import os

from collections.abc import Iterable
from typing import Any

from qtoggleserver.conf import settings
from qtoggleserver.persist import BaseDriver
from qtoggleserver.persist.typing import Id, Record
from qtoggleserver.utils import json as json_utils


DEFAULT_FILE_PATH = "qtoggleserver-data.json"

FILTER_OP_MAPPING = {
    "gt": operator.gt,
    "ge": operator.ge,
    "lt": operator.lt,
    "le": operator.le,
    "in": lambda a, b: a in b,
}


logger = logging.getLogger(__name__)

Collection = dict[str, Record]
IndexedData = dict[str, Collection]
UnindexedData = dict[str, list[Record]]


class JSONPersistError(Exception):
    pass


class DuplicateRecordId(JSONPersistError):
    pass


class JSONDriver(BaseDriver):
    def __init__(
        self,
        file_path: str | None = DEFAULT_FILE_PATH,
        pretty_format: bool | None = None,
        use_backup: bool = True,
        **kwargs,
    ) -> None:
        if file_path:
            logger.debug("using file %s", file_path)
        else:
            logger.warning("using in-memory storage")

        # Pretty formatting follows general debug flag, by default
        if pretty_format is None:
            pretty_format = settings.debug

        self._file_path: str | None = file_path
        self._pretty_format: bool = pretty_format
        self._use_backup: bool = use_backup

        self._data: IndexedData = self._index(self._load())
        self._max_ids: dict[str, int] = self._compute_max_ids(self._data)

    async def query(
        self,
        collection: str,
        fields: list[str] | None,
        filt: dict[str, Any],
        sort: list[tuple[str, bool]],
        limit: int | None,
    ) -> Iterable[Record]:
        coll = self._data.get(collection, {})
        records = []

        if isinstance(filt.get("id"), Id):  # look for specific record id
            filt = filt.copy()
            id_ = filt.pop("id")
            record = coll.get(id_)

            # Apply filter criteria
            if record is not None and self._filter_matches(record, filt):
                records.append(record)
        else:  # no single specific id in filt
            for id_, record in coll.items():
                # Apply filter criteria
                if self._filter_matches(dict(record, id=id_), filt):
                    records.append(record)

        # Sort
        for field, rev in reversed(sort):
            if field == "id":
                records.sort(key=lambda r: int(r["id"]), reverse=rev)
            else:
                records.sort(key=lambda r: r.get(field), reverse=rev)

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

    async def insert(self, collection: str, record: Record) -> Id:
        coll = self._data.setdefault(collection, {})

        id_ = record.get("id")
        if id_ is None:
            next_id = self._max_ids.get(collection, 0) + 1
            self._max_ids[collection] = next_id
            id_ = str(next_id)
            record = dict(record, id=id_)
        elif id_ in coll:
            raise DuplicateRecordId(id_)
        else:
            try:
                self._max_ids[collection] = max(self._max_ids.get(collection, 0), int(id_))
            except (ValueError, TypeError):
                pass

        coll[id_] = record

        self._save(self._unindex(self._data))

        return id_

    async def update(self, collection: str, record_part: Record, filt: dict[str, Any]) -> int:
        coll = self._data.setdefault(collection, {})
        modified_count = 0

        if isinstance(filt.get("id"), Id):
            filt = filt.copy()
            id_ = filt.pop("id")

            record = coll.get(id_)
            if record is not None:
                record.update(record_part)
                modified_count = 1
        else:  # no single specific id in filt
            for id_, record in coll.items():
                # Apply filter criteria
                if not self._filter_matches(dict(record, id=id_), filt):
                    continue

                # Actually update the record
                record.update(record_part)
                modified_count += 1

        self._save(self._unindex(self._data))

        return modified_count

    async def replace(self, collection: str, id_: Id, record: Record) -> bool:
        coll = self._data.setdefault(collection, {})

        if coll.get(id_) is None:
            return False  # no record found, no replacing

        record = record.copy()

        # Never change record id with replace
        record["id"] = id_
        coll[id_] = record

        self._save(self._unindex(self._data))

        return True

    async def remove(self, collection: str, filt: dict[str, Any]) -> int:
        coll = self._data.setdefault(collection, {})
        removed_count = 0

        if isinstance(filt.get("id"), Id):
            filt = filt.copy()
            id_ = filt.pop("id")

            record = coll.get(id_)
            if (record is not None) and self._filter_matches(record, filt):
                coll.pop(id_)
                removed_count = 1
        else:  # no single specific id in filt
            for id_, record in list(coll.items()):
                # Apply filter criteria
                if not self._filter_matches(dict(record, id=id_), filt):
                    continue

                # Actually remove the record
                coll.pop(id_)
                removed_count += 1

        self._save(self._unindex(self._data))

        return removed_count

    def _filter_matches(self, record: Record, filt: dict[str, Any]) -> bool:
        for key, value in filt.items():
            try:
                db_record_value = record[key]
            except KeyError:
                return False

            if not self._filter_value_matches(db_record_value, value):
                return False

        return True

    @staticmethod
    def _filter_value_matches(db_record_value: Any, filt_value: Any) -> bool:
        if isinstance(filt_value, dict):  # filter with operators
            for op, v in filt_value.items():
                op_func = FILTER_OP_MAPPING[op]
                if not op_func(db_record_value, v):
                    return False

            return True
        else:  # assuming simple value
            return db_record_value == filt_value

    @staticmethod
    def _compute_max_ids(data: IndexedData) -> dict[str, int]:
        max_ids: dict[str, int] = {}
        for coll, records in data.items():
            max_id = 0
            for id_ in records:
                try:
                    max_id = max(max_id, int(id_))
                except (ValueError, TypeError):
                    pass
            max_ids[coll] = max_id
        return max_ids

    def _get_backup_file_path(self) -> str | None:
        if not self._file_path:
            return None
        path, ext = os.path.splitext(self._file_path)
        return f"{path}_backup{ext}"

    def _load(self) -> UnindexedData:
        if not self._file_path:
            return {}

        logger.debug("loading from %s", self._file_path)

        try:
            # If the file is accessible but empty, consider data loaded and return empty dictionary
            if os.stat(self._file_path).st_size == 0:
                logger.debug("file %s is empty", self._file_path)
                return {}
        except FileNotFoundError:
            # If the file does not exist, consider data loaded and return empty dictionary
            logger.debug("file %s does not exist", self._file_path)
            return {}

        try:
            with open(self._file_path, "rb") as f:
                data = f.read()
                return json_utils.loads(data, extra_types=json_utils.EXTRA_TYPES_EXTENDED)
        except Exception as e:
            if not self._use_backup:
                raise

            # Upon failure, if using a backup, simply log the error and attempt to load from backup file
            logger.error("failed to load from %s: %s", self._file_path, e, exc_info=True)

            backup_file_path = self._get_backup_file_path()
            if backup_file_path:
                logger.warning("loading from backup %s", backup_file_path)

                with open(backup_file_path, "rb") as f:
                    return json_utils.loads(f.read(), extra_types=json_utils.EXTRA_TYPES_EXTENDED)

        return {}

    def _save(self, data: UnindexedData) -> None:
        if not self._file_path:
            return

        if self._use_backup and os.path.exists(self._file_path):
            backup_file_path = self._get_backup_file_path()
            if not backup_file_path:
                return
            logger.debug("backing up %s to %s", self._file_path, backup_file_path)
            os.rename(self._file_path, backup_file_path)

        logger.debug("saving to %s", self._file_path)

        with open(self._file_path, "wb") as f:
            data = json_utils.dumps(
                data, extra_types=json_utils.EXTRA_TYPES_EXTENDED, indent=4 if self._pretty_format else None
            )
            f.write(data.encode())

    @staticmethod
    def _index(data: UnindexedData) -> IndexedData:
        indexed_data = {}
        for coll, records in data.items():
            indexed_data[coll] = {r.get("id", ""): r for r in records}

        return indexed_data

    @staticmethod
    def _unindex(data: IndexedData) -> UnindexedData:
        unindexed_data = {}
        for coll, records in data.items():
            unindexed_data[coll] = list(records.values())

        return unindexed_data
