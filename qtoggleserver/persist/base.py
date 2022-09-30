import abc

from typing import Any, Iterable, Optional

from .typing import Id, Record


class BaseDriver(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    async def query(
        self,
        collection: str,
        fields: Optional[list[str]],
        filt: dict[str, Any],
        sort: list[tuple[str, bool]],
        limit: Optional[int]
    ) -> Iterable[Record]:
        return []

    @abc.abstractmethod
    async def insert(self, collection: str, record: Record) -> Id:
        return '1'  # returns the inserted record id

    @abc.abstractmethod
    async def update(self, collection: str, record_part: Record, filt: dict[str, Any]) -> int:
        return 0  # returns the number of updated records

    @abc.abstractmethod
    async def replace(self, collection: str, id_: Id, record: Record) -> bool:
        return False  # returns True if matched and replaced

    @abc.abstractmethod
    async def remove(self, collection: str, filt: dict[str, Any]) -> int:
        return 0  # returns the number of removed records

    async def ensure_index(self, collection: str, index: list[tuple[str, bool]]) -> None:
        pass

    async def cleanup(self) -> None:
        pass

    def is_history_supported(self) -> bool:
        return False
