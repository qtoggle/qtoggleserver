
from qtoggleserver.persist import BaseDriver

from . import data


async def test_remove_by_id(driver: BaseDriver) -> None:
    id1 = await driver.insert(data.COLL1, data.RECORD1)
    id2 = await driver.insert(data.COLL1, data.RECORD2)
    id3 = await driver.insert(data.COLL1, data.RECORD3)

    removed = await driver.remove(data.COLL1, filt={'id': id2})
    assert removed == 1

    results = await driver.query(data.COLL1, fields=None, filt={}, sort=[], limit=None)
    results = list(results)
    assert len(results) == 2

    assert results[0] == dict(data.RECORD1, id=id1)
    assert results[1] == dict(data.RECORD3, id=id3)


async def test_remove_filter(driver: BaseDriver) -> None:
    id1 = await driver.insert(data.COLL1, data.RECORD1)
    await driver.insert(data.COLL1, data.RECORD2)
    await driver.insert(data.COLL1, data.RECORD3)

    removed = await driver.remove(data.COLL1, filt={'int_key': {'gt': 1}})
    assert removed == 2

    results = await driver.query(data.COLL1, fields=None, filt={}, sort=[], limit=None)
    results = list(results)
    assert len(results) == 1

    assert results[0] == dict(data.RECORD1, id=id1)


async def test_remove_all(driver: BaseDriver) -> None:
    await driver.insert(data.COLL1, data.RECORD1)
    await driver.insert(data.COLL1, data.RECORD2)
    await driver.insert(data.COLL1, data.RECORD3)

    removed = await driver.remove(data.COLL1, filt={})
    assert removed == 3

    results = await driver.query(data.COLL1, fields=None, filt={}, sort=[], limit=None)
    results = list(results)
    assert len(results) == 0


async def test_remove_inexistent_record(driver: BaseDriver) -> None:
    await driver.insert(data.COLL1, data.RECORD1)
    await driver.insert(data.COLL1, data.RECORD2)
    await driver.insert(data.COLL1, data.RECORD3)

    removed = await driver.remove(data.COLL1, filt={'id': '34'})
    assert removed == 0

    results = await driver.query(data.COLL1, fields=None, filt={}, sort=[], limit=None)
    results = list(results)
    assert len(results) == 3


async def test_remove_inexistent_field(driver: BaseDriver) -> None:
    await driver.insert(data.COLL1, data.RECORD1)
    await driver.insert(data.COLL1, data.RECORD2)
    await driver.insert(data.COLL1, data.RECORD3)

    removed = await driver.remove(data.COLL1, filt={'inexistent_key': 1})
    assert removed == 0

    results = await driver.query(data.COLL1, fields=None, filt={}, sort=[], limit=None)
    results = list(results)
    assert len(results) == 3


async def test_remove_no_match(driver: BaseDriver) -> None:
    await driver.insert(data.COLL1, data.RECORD1)
    await driver.insert(data.COLL1, data.RECORD2)
    await driver.insert(data.COLL1, data.RECORD3)

    removed = await driver.remove(data.COLL1, filt={'int_key': 4})
    assert removed == 0

    results = await driver.query(data.COLL1, fields=None, filt={}, sort=[], limit=None)
    results = list(results)
    assert len(results) == 3


async def test_remove_custom_id_simple(driver: BaseDriver) -> None:
    await driver.insert(data.COLL1, dict(data.RECORD1, id=data.CUSTOM_ID_SIMPLE))
    id2 = await driver.insert(data.COLL1, data.RECORD2)

    removed = await driver.remove(data.COLL1, filt={'id': data.CUSTOM_ID_SIMPLE})
    assert removed == 1

    results = await driver.query(data.COLL1, fields=None, filt={}, sort=[], limit=None)
    results = list(results)
    assert len(results) == 1
    assert results[0] == dict(data.RECORD2, id=id2)


async def test_remove_custom_id_complex(driver: BaseDriver) -> None:
    await driver.insert(data.COLL1, dict(data.RECORD1, id=data.CUSTOM_ID_COMPLEX))
    id2 = await driver.insert(data.COLL1, data.RECORD2)

    removed = await driver.remove(data.COLL1, filt={'id': data.CUSTOM_ID_COMPLEX})
    assert removed == 1

    results = await driver.query(data.COLL1, fields=None, filt={}, sort=[], limit=None)
    results = list(results)
    assert len(results) == 1
    assert results[0] == dict(data.RECORD2, id=id2)


async def test_remove_no_match_custom_id_simple(driver: BaseDriver) -> None:
    await driver.insert(data.COLL1, data.RECORD1)
    await driver.insert(data.COLL1, data.RECORD2)

    removed = await driver.remove(data.COLL1, filt={'id': data.CUSTOM_ID_SIMPLE})
    assert removed == 0

    results = await driver.query(data.COLL1, fields=None, filt={}, sort=[], limit=None)
    results = list(results)
    assert len(results) == 2


async def test_remove_no_match_custom_id_complex(driver: BaseDriver) -> None:
    await driver.insert(data.COLL1, data.RECORD1)
    await driver.insert(data.COLL1, data.RECORD2)

    removed = await driver.remove(data.COLL1, filt={'id': data.CUSTOM_ID_COMPLEX})
    assert removed == 0

    results = await driver.query(data.COLL1, fields=None, filt={}, sort=[], limit=None)
    results = list(results)
    assert len(results) == 2
