from qtoggleserver.persist import BaseDriver

from . import data


async def test_insert_simple(driver: BaseDriver) -> None:
    id1 = await driver.insert(data.COLL1, data.RECORD1)

    results = await driver.query(data.COLL1, fields=None, filt={}, sort=[], limit=None)
    results = list(results)
    assert len(results) == 1

    assert results[0] == dict(data.RECORD1, id=id1)


async def test_insert_multiple(driver: BaseDriver) -> None:
    id1 = await driver.insert(data.COLL1, data.RECORD1)
    id2 = await driver.insert(data.COLL1, data.RECORD2)
    id3 = await driver.insert(data.COLL1, data.RECORD3)

    results = await driver.query(data.COLL1, fields=None, filt={}, sort=[("id", False)], limit=None)
    results = list(results)
    assert len(results) == 3

    assert results[0] == dict(data.RECORD1, id=id1)
    assert results[1] == dict(data.RECORD2, id=id2)
    assert results[2] == dict(data.RECORD3, id=id3)


async def test_insert_empty(driver: BaseDriver) -> None:
    id_ = await driver.insert(data.COLL1, {})

    results = await driver.query(data.COLL1, fields=None, filt={}, sort=[], limit=None)
    results = list(results)
    assert len(results) == 1

    assert results[0] == {"id": id_}


async def test_insert_with_custom_id_simple(driver: BaseDriver) -> None:
    id_ = await driver.insert(data.COLL1, dict(data.RECORD1, id=data.CUSTOM_ID_SIMPLE))
    await driver.insert(data.COLL1, data.RECORD2)
    assert id_ == data.CUSTOM_ID_SIMPLE

    results = await driver.query(data.COLL1, fields=None, filt={"id": id_}, sort=[], limit=None)
    results = list(results)
    assert len(results) == 1

    assert results[0] == dict(data.RECORD1, id=id_)


async def test_insert_with_custom_id_complex(driver: BaseDriver) -> None:
    id_ = await driver.insert(data.COLL1, dict(data.RECORD1, id=data.CUSTOM_ID_COMPLEX))
    await driver.insert(data.COLL1, data.RECORD2)
    assert id_ == data.CUSTOM_ID_COMPLEX

    results = await driver.query(data.COLL1, fields=None, filt={"id": id_}, sort=[], limit=None)
    results = list(results)
    assert len(results) == 1

    assert results[0] == dict(data.RECORD1, id=id_)
