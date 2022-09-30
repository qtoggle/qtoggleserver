from qtoggleserver.persist import BaseDriver

from . import data


async def test_update_match_id(driver: BaseDriver) -> None:
    id1 = await driver.insert(data.COLL1, data.RECORD1)
    id2 = await driver.insert(data.COLL1, data.RECORD2)

    updated = await driver.update(data.COLL1, record_part=data.RECORD3, filt={'id': id2})
    assert updated == 1

    results = await driver.query(data.COLL1, fields=None, filt={}, sort=[('int_key', False)], limit=None)
    results = list(results)
    assert len(results) == 2

    assert results[0] == dict(data.RECORD1, id=id1)
    assert results[1] == dict(data.RECORD3, id=id2)


async def test_update_match_many(driver: BaseDriver) -> None:
    id1 = await driver.insert(data.COLL1, data.RECORD1)
    id2 = await driver.insert(data.COLL1, data.RECORD2)
    id3 = await driver.insert(data.COLL1, data.RECORD3)

    record_part = dict(data.RECORD3, string_key='value4')
    updated = await driver.update(data.COLL1, record_part=record_part, filt={'int_key': {'gt': 1}})
    assert updated == 2

    results = await driver.query(data.COLL1, fields=None, filt={}, sort=[('int_key', False)], limit=None)
    results = list(results)
    assert len(results) == 3

    assert results[0] == dict(data.RECORD1, id=id1)
    assert results[1] == dict(data.RECORD3, id=id2, string_key='value4')
    assert results[2] == dict(data.RECORD3, id=id3, string_key='value4')


async def test_update_no_match(driver: BaseDriver) -> None:
    id1 = await driver.insert(data.COLL1, data.RECORD1)
    id2 = await driver.insert(data.COLL1, data.RECORD2)
    id3 = await driver.insert(data.COLL1, data.RECORD3)

    record_part = dict(data.RECORD3, string_key='value4')
    updated = await driver.update(data.COLL1, record_part=record_part, filt={'int_key': {'gt': 5}})
    assert updated == 0

    results = await driver.query(data.COLL1, fields=None, filt={}, sort=[('int_key', False)], limit=None)
    results = list(results)
    assert len(results) == 3

    assert results[0] == dict(data.RECORD1, id=id1)
    assert results[1] == dict(data.RECORD2, id=id2)
    assert results[2] == dict(data.RECORD3, id=id3)


async def test_update_few_fields(driver: BaseDriver) -> None:
    id1 = await driver.insert(data.COLL1, data.RECORD1)
    id2 = await driver.insert(data.COLL1, data.RECORD2)
    id3 = await driver.insert(data.COLL1, data.RECORD3)

    record_part = {'string_key': 'value4'}
    updated = await driver.update(data.COLL1, record_part=record_part, filt={'int_key': {'gt': 1}})
    assert updated == 2

    results = await driver.query(data.COLL1, fields=None, filt={}, sort=[('int_key', False)], limit=None)
    results = list(results)
    assert len(results) == 3

    assert results[0] == dict(data.RECORD1, id=id1)
    assert results[1] == dict(data.RECORD2, id=id2, string_key='value4')
    assert results[2] == dict(data.RECORD3, id=id3, string_key='value4')


async def test_update_new_fields(driver: BaseDriver) -> None:
    id1 = await driver.insert(data.COLL1, data.RECORD1)
    id2 = await driver.insert(data.COLL1, data.RECORD2)

    record_part = {'string_key': 'value4', 'new_key': 'new_value'}
    updated = await driver.update(data.COLL1, record_part=record_part, filt={'id': id2})
    assert updated == 1

    results = await driver.query(data.COLL1, fields=None, filt={}, sort=[('int_key', False)], limit=None)
    results = list(results)
    assert len(results) == 2

    assert results[0] == dict(data.RECORD1, id=id1)
    assert results[1] == dict(data.RECORD2, id=id2, **record_part)


async def test_update_custom_id_simple(driver: BaseDriver) -> None:
    await driver.insert(data.COLL1, dict(data.RECORD1, id=data.CUSTOM_ID_SIMPLE))
    id2 = await driver.insert(data.COLL1, data.RECORD2)

    record_part = {'string_key': 'value4', 'new_key': 'new_value'}
    updated = await driver.update(data.COLL1, filt={'id': data.CUSTOM_ID_SIMPLE}, record_part=record_part)
    assert updated == 1

    results = await driver.query(data.COLL1, fields=None, filt={}, sort=[('int_key', False)], limit=None)
    results = list(results)
    assert len(results) == 2
    assert results[0] == dict(data.RECORD1, id=data.CUSTOM_ID_SIMPLE, **record_part)
    assert results[1] == dict(data.RECORD2, id=id2)


async def test_update_custom_id_complex(driver: BaseDriver) -> None:
    await driver.insert(data.COLL1, dict(data.RECORD1, id=data.CUSTOM_ID_COMPLEX))
    id2 = await driver.insert(data.COLL1, data.RECORD2)

    record_part = {'string_key': 'value4', 'new_key': 'new_value'}
    updated = await driver.update(data.COLL1, filt={'id': data.CUSTOM_ID_COMPLEX}, record_part=record_part)
    assert updated == 1

    results = await driver.query(data.COLL1, fields=None, filt={}, sort=[('int_key', False)], limit=None)
    results = list(results)
    assert len(results) == 2
    assert results[0] == dict(data.RECORD1, id=data.CUSTOM_ID_COMPLEX, **record_part)
    assert results[1] == dict(data.RECORD2, id=id2)


async def test_update_no_match_custom_id_simple(driver: BaseDriver) -> None:
    await driver.insert(data.COLL1, data.RECORD1)
    await driver.insert(data.COLL1, data.RECORD2)

    record_part = {'string_key': 'value4', 'new_key': 'new_value'}
    updated = await driver.update(data.COLL1, filt={'id': data.CUSTOM_ID_SIMPLE}, record_part=record_part)
    assert updated == 0


async def test_update_no_match_custom_id_complex(driver: BaseDriver) -> None:
    await driver.insert(data.COLL1, data.RECORD1)
    await driver.insert(data.COLL1, data.RECORD2)

    record_part = {'string_key': 'value4', 'new_key': 'new_value'}
    updated = await driver.update(data.COLL1, filt={'id': data.CUSTOM_ID_COMPLEX}, record_part=record_part)
    assert updated == 0
