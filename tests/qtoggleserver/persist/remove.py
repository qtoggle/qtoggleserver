
from qtoggleserver.persist import BaseDriver

from . import data


def test_remove_by_id(driver: BaseDriver) -> None:
    id1 = driver.insert(data.COLL1, data.RECORD1)
    id2 = driver.insert(data.COLL1, data.RECORD2)
    id3 = driver.insert(data.COLL1, data.RECORD3)

    removed = driver.remove(data.COLL1, filt={'id': id2})
    assert removed == 1

    results = driver.query(data.COLL1, fields=None, filt={}, sort=[], limit=None)
    results = list(results)
    assert len(results) == 2

    assert results[0] == dict(data.RECORD1, id=id1)
    assert results[1] == dict(data.RECORD3, id=id3)


def test_remove_filter(driver: BaseDriver) -> None:
    id1 = driver.insert(data.COLL1, data.RECORD1)
    driver.insert(data.COLL1, data.RECORD2)
    driver.insert(data.COLL1, data.RECORD3)

    removed = driver.remove(data.COLL1, filt={'int_key': {'gt': 1}})
    assert removed == 2

    results = driver.query(data.COLL1, fields=None, filt={}, sort=[], limit=None)
    results = list(results)
    assert len(results) == 1

    assert results[0] == dict(data.RECORD1, id=id1)


def test_remove_all(driver: BaseDriver) -> None:
    driver.insert(data.COLL1, data.RECORD1)
    driver.insert(data.COLL1, data.RECORD2)
    driver.insert(data.COLL1, data.RECORD3)

    removed = driver.remove(data.COLL1, filt={})
    assert removed == 3

    results = driver.query(data.COLL1, fields=None, filt={}, sort=[], limit=None)
    results = list(results)
    assert len(results) == 0


def test_remove_inexistent_record(driver: BaseDriver) -> None:
    driver.insert(data.COLL1, data.RECORD1)
    driver.insert(data.COLL1, data.RECORD2)
    driver.insert(data.COLL1, data.RECORD3)

    removed = driver.remove(data.COLL1, filt={'int_key': 4})
    assert removed == 0

    results = driver.query(data.COLL1, fields=None, filt={}, sort=[], limit=None)
    results = list(results)
    assert len(results) == 3


def test_remove_inexistent_field(driver: BaseDriver) -> None:
    driver.insert(data.COLL1, data.RECORD1)
    driver.insert(data.COLL1, data.RECORD2)
    driver.insert(data.COLL1, data.RECORD3)

    removed = driver.remove(data.COLL1, filt={'inexistent_key': 1})
    assert removed == 0

    results = driver.query(data.COLL1, fields=None, filt={}, sort=[], limit=None)
    results = list(results)
    assert len(results) == 3
