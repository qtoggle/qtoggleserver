
from qtoggleserver.persist import BaseDriver

from . import data


def test_query_full(driver: BaseDriver) -> None:
    driver.insert(data.COLL1, data.RECORD1)
    driver.insert(data.COLL1, data.RECORD2)
    driver.insert(data.COLL1, data.RECORD3)

    result = driver.query(data.COLL1, fields=None, filt={}, limit=None)
    assert len(list(result)) == 3


def test_query_specific_id(driver: BaseDriver) -> None:
    driver.insert(data.COLL1, data.RECORD1)
    driver.insert(data.COLL1, data.RECORD2)
    id3 = driver.insert(data.COLL1, data.RECORD3)

    results = driver.query(data.COLL1, fields=None, filt={'id': id3}, limit=None)
    results = list(results)
    assert len(results) == 1

    record3 = dict(data.RECORD3, id=id3)
    assert results[0] == record3


def test_query_simple_filter(driver: BaseDriver) -> None:
    driver.insert(data.COLL1, data.RECORD1)
    driver.insert(data.COLL1, data.RECORD2)
    driver.insert(data.COLL1, data.RECORD3)

    results = driver.query(data.COLL1, fields=None, filt={'string_key': data.RECORD2['string_key']}, limit=None)
    results = list(results)
    assert len(results) == 1

    result0 = results[0]
    result0.pop('id', None)
    assert result0 == data.RECORD2


def test_query_fields(driver: BaseDriver) -> None:
    driver.insert(data.COLL1, data.RECORD1)
    driver.insert(data.COLL1, data.RECORD2)
    driver.insert(data.COLL1, data.RECORD3)

    results = driver.query(data.COLL1, fields=['int_key', 'bool_key'], filt={}, limit=None)
    results = list(results)
    assert len(results) == 3

    for result in results:
        assert len(result) == 2
        assert 'int_key' in result
        assert 'bool_key' in result
