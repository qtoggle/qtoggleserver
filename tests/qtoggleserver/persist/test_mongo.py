
import mongomock
import pytest

from qtoggleserver.drivers.persist import mongo
from qtoggleserver.persist import BaseDriver

from . import query


@pytest.fixture
def driver(monkeypatch) -> BaseDriver:
    monkeypatch.setattr(mongo, 'MongoClient', mongomock.MongoClient)
    return mongo.MongoDriver()


def test_query_full(driver: BaseDriver) -> None:
    query.test_query_full(driver)


def test_query_specific_id(driver: BaseDriver) -> None:
    query.test_query_specific_id(driver)


def test_query_simple_filter(driver: BaseDriver) -> None:
    query.test_query_simple_filter(driver)


def test_query_fields(driver: BaseDriver) -> None:
    query.test_query_fields(driver)
