
from qtoggleserver.persist import BaseDriver

from . import data


def test_insert_simple(driver: BaseDriver) -> None:
    id1 = driver.insert(data.COLL1, data.RECORD1)

    results = driver.query(data.COLL1, fields=None, filt={}, sort=[], limit=None)
    results = list(results)
    assert len(results) == 1

    assert results[0] == dict(data.RECORD1, id=id1)


def test_insert_multiple(driver: BaseDriver) -> None:
    id1 = driver.insert(data.COLL1, data.RECORD1)
    id2 = driver.insert(data.COLL1, data.RECORD2)
    id3 = driver.insert(data.COLL1, data.RECORD3)

    results = driver.query(data.COLL1, fields=None, filt={}, sort=[('id', False)], limit=None)
    results = list(results)
    assert len(results) == 3

    assert results[0] == dict(data.RECORD1, id=id1)
    assert results[1] == dict(data.RECORD2, id=id2)
    assert results[2] == dict(data.RECORD3, id=id3)


def test_insert_empty(driver: BaseDriver) -> None:
    id_ = driver.insert(data.COLL1, {})

    results = driver.query(data.COLL1, fields=None, filt={}, sort=[], limit=None)
    results = list(results)
    assert len(results) == 1

    assert results[0] == {'id': id_}


def test_insert_with_custom_id_simple(driver: BaseDriver) -> None:
    id_ = driver.insert(data.COLL1, dict(data.RECORD1, id=data.CUSTOM_ID_SIMPLE))
    driver.insert(data.COLL1, data.RECORD2)
    assert id_ == data.CUSTOM_ID_SIMPLE

    results = driver.query(data.COLL1, fields=None, filt={'id': id_}, sort=[], limit=None)
    results = list(results)
    assert len(results) == 1

    assert results[0] == dict(data.RECORD1, id=id_)


def test_insert_with_custom_id_complex(driver: BaseDriver) -> None:
    id_ = driver.insert(data.COLL1, dict(data.RECORD1, id=data.CUSTOM_ID_COMPLEX))
    driver.insert(data.COLL1, data.RECORD2)
    assert id_ == data.CUSTOM_ID_COMPLEX

    results = driver.query(data.COLL1, fields=None, filt={'id': id_}, sort=[], limit=None)
    results = list(results)
    assert len(results) == 1

    assert results[0] == dict(data.RECORD1, id=id_)
