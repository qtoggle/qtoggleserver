
from qtoggleserver.persist import BaseDriver

from . import data


def test_replace_no_match(driver: BaseDriver) -> None:
    id1 = driver.insert(data.COLL1, data.RECORD1)
    id2 = driver.insert(data.COLL1, data.RECORD2)

    replaced = driver.replace(data.COLL1, id_='inexistent_id', record=data.RECORD3)
    assert not replaced

    results = driver.query(data.COLL1, fields=None, filt={}, sort=[('int_key', False)], limit=None)
    results = list(results)
    assert len(results) == 2

    assert results[0] == dict(data.RECORD1, id=id1)
    assert results[1] == dict(data.RECORD2, id=id2)


def test_replace_match(driver: BaseDriver) -> None:
    id1 = driver.insert(data.COLL1, data.RECORD1)
    id2 = driver.insert(data.COLL1, data.RECORD2)

    replaced = driver.replace(data.COLL1, id_=id1, record=data.RECORD3)
    assert replaced

    results = driver.query(data.COLL1, fields=None, filt={}, sort=[('int_key', False)], limit=None)
    results = list(results)
    assert len(results) == 2

    assert results[0] == dict(data.RECORD2, id=id2)
    assert results[1] == dict(data.RECORD3, id=id1)


def test_replace_match_with_id(driver: BaseDriver) -> None:
    id1 = driver.insert(data.COLL1, data.RECORD1)
    id2 = driver.insert(data.COLL1, data.RECORD2)

    replaced = driver.replace(data.COLL1, id_=id1, record=dict(data.RECORD3, id='new_id'))
    assert replaced

    results = driver.query(data.COLL1, fields=None, filt={}, sort=[('int_key', False)], limit=None)
    results = list(results)
    assert len(results) == 2

    assert results[0] == dict(data.RECORD2, id=id2)
    assert results[1] == dict(data.RECORD3, id=id1)


def test_replace_match_fewer_fields(driver: BaseDriver) -> None:
    id1 = driver.insert(data.COLL1, data.RECORD1)
    id2 = driver.insert(data.COLL1, data.RECORD2)
    id3 = driver.insert(data.COLL1, data.RECORD3)

    new_record = {'field1': 'one', 'int_key': 0}
    replaced = driver.replace(data.COLL1, id_=id1, record=new_record)
    assert replaced

    results = driver.query(data.COLL1, fields=None, filt={}, sort=[('int_key', False)], limit=None)
    results = list(results)
    assert len(results) == 3

    assert results[0] == dict(new_record, id=id1)
    assert results[1] == dict(data.RECORD2, id=id2)
    assert results[2] == dict(data.RECORD3, id=id3)
