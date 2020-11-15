
from qtoggleserver.persist import BaseDriver

from . import data


def test_query_full(driver: BaseDriver) -> None:
    driver.insert(data.COLL1, data.RECORD1)
    driver.insert(data.COLL1, data.RECORD2)
    driver.insert(data.COLL1, data.RECORD3)

    result = driver.query(data.COLL1, fields=None, filt={}, sort=[], limit=None)
    assert len(list(result)) == 3


def test_query_filter_id(driver: BaseDriver) -> None:
    driver.insert(data.COLL1, data.RECORD1)
    driver.insert(data.COLL1, data.RECORD2)
    id3 = driver.insert(data.COLL1, data.RECORD3)

    results = driver.query(data.COLL1, fields=None, filt={'id': id3}, sort=[], limit=None)
    results = list(results)
    assert len(results) == 1

    record3 = dict(data.RECORD3, id=id3)
    assert results[0] == record3


def test_query_filter_simple(driver: BaseDriver) -> None:
    driver.insert(data.COLL1, data.RECORD1)
    driver.insert(data.COLL1, data.RECORD2)
    driver.insert(data.COLL1, data.RECORD3)

    results = driver.query(
        data.COLL1,
        fields=None,
        filt={'string_key': data.RECORD2['string_key']},
        sort=[],
        limit=None
    )
    results = list(results)
    assert len(results) == 1

    result0 = results[0]
    result0.pop('id', None)
    assert result0 == data.RECORD2


def test_query_filter_ge_lt(driver: BaseDriver) -> None:
    id1 = driver.insert(data.COLL1, data.RECORD1)
    id2 = driver.insert(data.COLL1, data.RECORD2)
    driver.insert(data.COLL1, data.RECORD3)

    results = driver.query(data.COLL1, fields=None, filt={'int_key': {'ge': 1, 'lt': 3}}, sort=[], limit=None)
    results = list(results)
    assert len(results) == 2

    results.sort(key=lambda r: r['int_key'])

    assert results[0] == dict(data.RECORD1, id=id1)
    assert results[1] == dict(data.RECORD2, id=id2)


def test_query_filter_gt_le(driver: BaseDriver) -> None:
    driver.insert(data.COLL1, data.RECORD1)
    id2 = driver.insert(data.COLL1, data.RECORD2)
    id3 = driver.insert(data.COLL1, data.RECORD3)

    results = driver.query(data.COLL1, fields=None, filt={'int_key': {'gt': 1, 'le': 3}}, sort=[], limit=None)
    results = list(results)
    assert len(results) == 2

    results.sort(key=lambda r: r['int_key'])

    assert results[0] == dict(data.RECORD2, id=id2)
    assert results[1] == dict(data.RECORD3, id=id3)


def test_query_filter_in(driver: BaseDriver) -> None:
    driver.insert(data.COLL1, data.RECORD1)
    id2 = driver.insert(data.COLL1, data.RECORD2)
    id3 = driver.insert(data.COLL1, data.RECORD3)

    results = driver.query(data.COLL1, fields=None, filt={'int_key': {'in': [2, 3]}}, sort=[], limit=None)
    results = list(results)
    assert len(results) == 2

    results.sort(key=lambda r: r['int_key'])

    assert results[0] == dict(data.RECORD2, id=id2)
    assert results[1] == dict(data.RECORD3, id=id3)


def test_query_sort_simple(driver: BaseDriver) -> None:
    id1 = driver.insert(data.COLL1, data.RECORD1)
    id2 = driver.insert(data.COLL1, data.RECORD2)
    id3 = driver.insert(data.COLL1, data.RECORD3)

    results = driver.query(data.COLL1, fields=None, filt={}, sort=[('int_key', False)], limit=None)
    results = list(results)
    assert len(results) == 3

    assert results[0]['id'] == id1
    assert results[1]['id'] == id2
    assert results[2]['id'] == id3


def test_query_sort_desc(driver: BaseDriver) -> None:
    id1 = driver.insert(data.COLL1, data.RECORD1)
    id2 = driver.insert(data.COLL1, data.RECORD2)
    id3 = driver.insert(data.COLL1, data.RECORD3)

    results = driver.query(data.COLL1, fields=None, filt={}, sort=[('int_key', True)], limit=None)
    results = list(results)
    assert len(results) == 3

    assert results[0]['id'] == id3
    assert results[1]['id'] == id2
    assert results[2]['id'] == id1


def test_query_sort_composite(driver: BaseDriver) -> None:
    id1 = driver.insert(data.COLL1, data.RECORD1)
    id2 = driver.insert(data.COLL1, data.RECORD2)
    id3 = driver.insert(data.COLL1, data.RECORD3)

    results = driver.query(
        data.COLL1,
        fields=None,
        filt={},
        sort=[('non_unique_key', False), ('int_key', True)],
        limit=None
    )
    results = list(results)
    assert len(results) == 3

    assert results[0]['id'] == id2
    assert results[1]['id'] == id3
    assert results[2]['id'] == id1


def test_query_limit(driver: BaseDriver) -> None:
    driver.insert(data.COLL1, data.RECORD1)
    driver.insert(data.COLL1, data.RECORD2)
    driver.insert(data.COLL1, data.RECORD3)

    results = driver.query(data.COLL1, fields=None, filt={}, sort=[], limit=2)
    results = list(results)
    assert len(results) == 2


def test_query_fields(driver: BaseDriver) -> None:
    driver.insert(data.COLL1, data.RECORD1)
    driver.insert(data.COLL1, data.RECORD2)
    driver.insert(data.COLL1, data.RECORD3)

    results = driver.query(data.COLL1, fields=['int_key', 'bool_key'], filt={}, sort=[], limit=None)
    results = list(results)
    assert len(results) == 3

    for result in results:
        assert len(result) == 2
        assert 'int_key' in result
        assert 'bool_key' in result


def test_query_filter_limit(driver: BaseDriver) -> None:
    driver.insert(data.COLL1, data.RECORD1)
    driver.insert(data.COLL1, data.RECORD2)
    driver.insert(data.COLL1, data.RECORD3)

    results = driver.query(data.COLL1, fields=None, filt={'int_key': {'gt': 1}}, sort=[], limit=1)
    results = list(results)
    assert len(results) == 1


def test_query_inexistent_field(driver: BaseDriver) -> None:
    driver.insert(data.COLL1, data.RECORD1)
    driver.insert(data.COLL1, data.RECORD2)
    driver.insert(data.COLL1, data.RECORD3)

    results = driver.query(data.COLL1, fields=['int_key', 'inexistent_key'], filt={}, sort=[], limit=None)
    assert len(list(results)) == 3

    for result in results:
        assert len(result) == 1
        assert 'int_key' in result
