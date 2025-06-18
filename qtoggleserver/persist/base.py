import abc
import asyncio

from collections.abc import Iterable
from typing import Any

from .typing import Id, Record, Sample, SampleValue


class BaseDriver(metaclass=abc.ABCMeta):
    async def init(self) -> None:
        """Perform any initialization necessary to use this driver."""

        pass

    async def cleanup(self) -> None:
        """Perform any cleanups necessary to decommission this driver."""

        pass

    @abc.abstractmethod
    async def query(
        self,
        collection: str,
        fields: list[str] | None,
        filt: dict[str, Any],
        sort: list[tuple[str, bool]],
        limit: int | None,
    ) -> Iterable[Record]:
        """Return records from `collection`.

        Optionally project the returned records by only returning given `fields`, if not `None`.

        Filter records according to `filt`. Besides filtering by exact field value, the following filter operators are
        supported: `gt`, `ge`, `lt`, `le` and `in` (list of values).

        Sort results according to `sort` argument which is a list of pairs of fields and "descending" flags, if not an
        empty list.

        Optionally limit the number of returned records to `limit`, if not None."""

        return []

    @abc.abstractmethod
    async def insert(self, collection: str, record: Record) -> Id:
        """Insert `record` into `collection`.

        Return the associated record ID."""

        return "1"

    @abc.abstractmethod
    async def update(self, collection: str, record_part: Record, filt: dict[str, Any]) -> int:
        """Update records from `collection` with fields given in `record_part`.

        Only records that match the `filt` filter will be updated. Besides filtering by exact field value, the following
        filter operators are supported: `gt`, `ge`, `lt`, `le` and `in` (list of values).

        Return the total number of records that were updated."""

        return 0

    @abc.abstractmethod
    async def replace(self, collection: str, id_: Id, record: Record) -> bool:
        """Replace record with `id` in `collection`.

        Return `True` if matched and replaced."""

        return False

    @abc.abstractmethod
    async def remove(self, collection: str, filt: dict[str, Any]) -> int:
        """Remove records from `collection`.

        Only records that match the `filt` filter will be removed. Besides filtering by exact field value, the following
        filter operators are supported: `gt`, `ge`, `lt`, `le` and `in` (list of values).

        Return the total number of records that were removed."""

        return 0

    async def get_samples_slice(
        self,
        collection: str,
        obj_id: Id,
        from_timestamp: int | None,
        to_timestamp: int | None,
        limit: int | None,
        sort_desc: bool,
    ) -> Iterable[Sample]:
        """Return the samples of `obj_id` from `collection`.

        Filter results by an interval of time, if `from_timestamp` and/or `to_timestamp` are not `None`.
        `from_timestamp` is inclusive, while `to_timestamp` is exclusive.

        Optionally limit results to `limit` number of records, if not `None`. Limiting is done always with respect to
        the order of samples (i.e. chronologically ascending or descending).

        Sort the results by timestamp according to the value of `sort_desc`."""

        filt: dict[str, Any] = {
            "oid": obj_id,
        }

        if from_timestamp is not None:
            filt.setdefault("ts", {})["ge"] = from_timestamp

        if to_timestamp is not None:
            filt.setdefault("ts", {})["lt"] = to_timestamp

        sort = [("ts", sort_desc)]

        results = await self.query(collection, fields=None, filt=filt, sort=sort, limit=limit)

        return ((r["ts"], r["val"]) for r in results)

    async def get_samples_by_timestamp(
        self,
        collection: str,
        obj_id: Id,
        timestamps: list[int],
    ) -> Iterable[SampleValue]:
        """For each timestamp in `timestamps`, return the sample of `obj_id` from `collection` that was saved right
        before the (or at the exact) timestamp."""

        object_filter: dict[str, Any] = {
            "oid": obj_id,
        }

        query_tasks = []
        for timestamp in timestamps:
            filt = dict(object_filter, ts={"le": timestamp})
            task = self.query(collection, fields=None, filt=filt, sort=[("ts", True)], limit=1)
            query_tasks.append(task)

        task_results = await asyncio.gather(*query_tasks)

        samples = []
        for i, task_result in enumerate(task_results):
            query_results = list(task_result)
            if query_results:
                sample = query_results[0]["val"]
                samples.append(sample)
            else:
                samples.append(None)

        return samples

    async def save_sample(self, collection: str, obj_id: Id, timestamp: int, value: SampleValue) -> None:
        """Save a sample of an object with `obj_id` at a given `timestamp` to a specified `collection`."""

        record = {"oid": obj_id, "val": value, "ts": timestamp}

        await self.insert(collection, record)

    async def remove_samples(
        self,
        collection: str,
        obj_ids: list[Id] | None,
        from_timestamp: int | None,
        to_timestamp: int | None,
    ) -> int:
        """Remove samples from `collection`.

        If `obj_ids` is not `None`, only remove samples of given object ids.

        If `from_timestamp` and/or `to_timestamp` are not `None`, only remove samples within specified interval of time.
        `from_timestamp` is inclusive, while `to_timestamp` is exclusive.

        Return the number of removed samples."""

        filt: dict[str, Any] = {}
        if obj_ids:
            filt["oid"] = {"in": obj_ids}

        if from_timestamp is not None:
            filt.setdefault("ts", {})["ge"] = from_timestamp

        if to_timestamp is not None:
            filt.setdefault("ts", {})["lt"] = to_timestamp

        return await self.remove(collection, filt)

    def is_samples_supported(self) -> bool:
        """Tell whether samples are supported by this driver or not."""

        return False

    async def ensure_index(self, collection: str, index: list[tuple[str, bool]] | None) -> None:
        """Create an index on `collection` if not already present. `index` is a list of pairs of field names and
        "descending" direction flags.

        If `index` is `None`, the collection is assumed to be a collection of samples where the index is considered to
        be ascending on the timestamp field."""

        pass
