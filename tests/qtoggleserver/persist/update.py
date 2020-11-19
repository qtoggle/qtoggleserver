
from qtoggleserver.persist import BaseDriver

from . import data


def test_update_match_id(driver: BaseDriver) -> None:
    id1 = driver.insert(data.COLL1, data.RECORD1)
    id2 = driver.insert(data.COLL1, data.RECORD2)

    updated = driver.update(data.COLL1, record_part=data.RECORD3, filt={'id': id2})
    assert updated == 1

    results = driver.query(data.COLL1, fields=None, filt={}, sort=[('int_key', False)], limit=None)
    results = list(results)
    assert len(results) == 2

    assert results[0] == dict(data.RECORD1, id=id1)
    assert results[1] == dict(data.RECORD3, id=id2)


def test_update_match_many(driver: BaseDriver) -> None:
    id1 = driver.insert(data.COLL1, data.RECORD1)
    id2 = driver.insert(data.COLL1, data.RECORD2)
    id3 = driver.insert(data.COLL1, data.RECORD3)

    record_part = dict(data.RECORD3, string_key='value4')
    updated = driver.update(data.COLL1, record_part=record_part, filt={'int_key': {'gt': 1}})
    assert updated == 2

    results = driver.query(data.COLL1, fields=None, filt={}, sort=[('int_key', False)], limit=None)
    results = list(results)
    assert len(results) == 3

    assert results[0] == dict(data.RECORD1, id=id1)
    assert results[1] == dict(data.RECORD3, id=id2, string_key='value4')
    assert results[2] == dict(data.RECORD3, id=id3, string_key='value4')


def test_update_no_match(driver: BaseDriver) -> None:
    id1 = driver.insert(data.COLL1, data.RECORD1)
    id2 = driver.insert(data.COLL1, data.RECORD2)
    id3 = driver.insert(data.COLL1, data.RECORD3)

    record_part = dict(data.RECORD3, string_key='value4')
    updated = driver.update(data.COLL1, record_part=record_part, filt={'int_key': {'gt': 5}})
    assert updated == 0

    results = driver.query(data.COLL1, fields=None, filt={}, sort=[('int_key', False)], limit=None)
    results = list(results)
    assert len(results) == 3

    assert results[0] == dict(data.RECORD1, id=id1)
    assert results[1] == dict(data.RECORD2, id=id2)
    assert results[2] == dict(data.RECORD3, id=id3)


def test_update_new_fields(driver: BaseDriver) -> None:
    id1 = driver.insert(data.COLL1, data.RECORD1)
    id2 = driver.insert(data.COLL1, data.RECORD2)

    record_part = {'string_key': 'value4', 'new_key': 'new_value'}
    updated = driver.update(data.COLL1, record_part=record_part, filt={'id': id2})
    assert updated == 1

    results = driver.query(data.COLL1, fields=None, filt={}, sort=[('int_key', False)], limit=None)
    results = list(results)
    assert len(results) == 2

    assert results[0] == dict(data.RECORD1, id=id1)
    assert results[1] == dict(data.RECORD2, id=id2, **record_part)
