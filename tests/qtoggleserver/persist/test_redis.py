
import fakeredis
import pytest
import redis as python_redis


from qtoggleserver.drivers.persist import redis
from qtoggleserver.persist import BaseDriver

from . import query


@pytest.fixture
def driver(monkeypatch) -> BaseDriver:
    monkeypatch.setattr(python_redis, 'StrictRedis', fakeredis.FakeStrictRedis)
    return redis.RedisDriver()


def test_query_full(driver: BaseDriver) -> None:
    query.test_query_full(driver)


def test_query_specific_id(driver: BaseDriver) -> None:
    query.test_query_specific_id(driver)


def test_query_simple_filter(driver: BaseDriver) -> None:
    query.test_query_simple_filter(driver)


def test_query_fields(driver: BaseDriver) -> None:
    query.test_query_fields(driver)
