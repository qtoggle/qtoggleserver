
import abc

from typing import Any, Dict, Iterable, List, Optional

from .typing import Id, Record


class BaseDriver(metaclass=abc.ABCMeta):
    @abc.abstractmethod
    def query(
        self,
        collection: str,
        fields: Optional[List[str]],
        filt: Dict[str, Any],
        limit: Optional[int]
    ) -> Iterable[Record]:

        return []

    @abc.abstractmethod
    def insert(self, collection: str, record: Record) -> Id:
        return '1'  # Returns the inserted record id

    @abc.abstractmethod
    def update(self, collection: str, record_part: Record, filt: Dict[str, Any]) -> int:
        return 0  # Returns the number of updated records

    @abc.abstractmethod
    def replace(self, collection: str, id_: Id, record: Record, upsert: bool) -> bool:
        return False  # Returns True if replaced

    @abc.abstractmethod
    def remove(self, collection: str, filt: Dict[str, Any]) -> int:
        return 0  # Returns the number of removed records

    @abc.abstractmethod
    def cleanup(self) -> None:
        pass
