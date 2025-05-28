from qtoggleserver.persist import BaseDriver

from . import data


async def test_query_all(driver: BaseDriver) -> None:
    await driver.insert(data.COLL1, data.RECORD1)
    await driver.insert(data.COLL1, data.RECORD2)
    await driver.insert(data.COLL1, data.RECORD3)

    results = await driver.query(data.COLL1, fields=None, filt={}, sort=[], limit=None)
    results = list(results)

    assert len(results) == 3


async def test_query_fields(driver: BaseDriver) -> None:
    await driver.insert(data.COLL1, data.RECORD1)
    await driver.insert(data.COLL1, data.RECORD2)
    await driver.insert(data.COLL1, data.RECORD3)

    results = await driver.query(data.COLL1, fields=["int_key", "bool_key"], filt={}, sort=[], limit=None)
    results = list(results)
    assert len(results) == 3

    for result in results:
        assert len(result) == 2
        assert "int_key" in result
        assert "bool_key" in result


async def test_query_fields_inexistent(driver: BaseDriver) -> None:
    await driver.insert(data.COLL1, data.RECORD1)
    await driver.insert(data.COLL1, data.RECORD2)
    await driver.insert(data.COLL1, data.RECORD3)

    results = await driver.query(data.COLL1, fields=["int_key", "inexistent_key"], filt={}, sort=[], limit=None)
    assert len(list(results)) == 3

    for result in results:
        assert len(result) == 1
        assert "int_key" in result


async def test_query_filter_id(driver: BaseDriver) -> None:
    await driver.insert(data.COLL1, data.RECORD1)
    await driver.insert(data.COLL1, data.RECORD2)
    id3 = await driver.insert(data.COLL1, data.RECORD3)

    results = await driver.query(data.COLL1, fields=None, filt={"id": id3}, sort=[], limit=None)
    results = list(results)
    assert len(results) == 1

    record3 = dict(data.RECORD3, id=id3)
    assert results[0] == record3


async def test_query_filter_id_inexistent(driver: BaseDriver) -> None:
    await driver.insert(data.COLL1, data.RECORD1)
    await driver.insert(data.COLL1, data.RECORD2)
    await driver.insert(data.COLL1, data.RECORD3)

    results = await driver.query(data.COLL1, fields=None, filt={"id": "16384"}, sort=[], limit=None)
    results = list(results)
    assert len(results) == 0


async def test_query_filter_custom_id_inexistent(driver: BaseDriver) -> None:
    await driver.insert(data.COLL1, data.RECORD1)
    await driver.insert(data.COLL1, data.RECORD2)
    await driver.insert(data.COLL1, data.RECORD3)

    results = await driver.query(data.COLL1, fields=None, filt={"id": data.CUSTOM_ID_COMPLEX}, sort=[], limit=None)
    results = list(results)
    assert len(results) == 0


async def test_query_filter_simple(driver: BaseDriver) -> None:
    await driver.insert(data.COLL1, data.RECORD1)
    await driver.insert(data.COLL1, data.RECORD2)
    await driver.insert(data.COLL1, data.RECORD3)

    results = await driver.query(
        data.COLL1, fields=None, filt={"string_key": data.RECORD2["string_key"]}, sort=[], limit=None
    )
    results = list(results)
    assert len(results) == 1

    result0 = results[0]
    result0.pop("id", None)
    assert result0 == data.RECORD2


async def test_query_filter_ge_lt(driver: BaseDriver) -> None:
    id1 = await driver.insert(data.COLL1, data.RECORD1)
    id2 = await driver.insert(data.COLL1, data.RECORD2)
    await driver.insert(data.COLL1, data.RECORD3)

    results = await driver.query(data.COLL1, fields=None, filt={"int_key": {"ge": 1, "lt": 3}}, sort=[], limit=None)
    results = list(results)
    assert len(results) == 2

    results.sort(key=lambda r: r["int_key"])

    assert results[0] == dict(data.RECORD1, id=id1)
    assert results[1] == dict(data.RECORD2, id=id2)


async def test_query_filter_gt_le(driver: BaseDriver) -> None:
    await driver.insert(data.COLL1, data.RECORD1)
    id2 = await driver.insert(data.COLL1, data.RECORD2)
    id3 = await driver.insert(data.COLL1, data.RECORD3)

    results = await driver.query(data.COLL1, fields=None, filt={"int_key": {"gt": 1, "le": 3}}, sort=[], limit=None)
    results = list(results)
    assert len(results) == 2

    results.sort(key=lambda r: r["int_key"])

    assert results[0] == dict(data.RECORD2, id=id2)
    assert results[1] == dict(data.RECORD3, id=id3)


async def test_query_filter_in(driver: BaseDriver) -> None:
    await driver.insert(data.COLL1, data.RECORD1)
    id2 = await driver.insert(data.COLL1, data.RECORD2)
    id3 = await driver.insert(data.COLL1, data.RECORD3)

    results = await driver.query(data.COLL1, fields=None, filt={"int_key": {"in": [2, 3, 4]}}, sort=[], limit=None)
    results = list(results)
    assert len(results) == 2

    results.sort(key=lambda r: r["int_key"])

    assert results[0] == dict(data.RECORD2, id=id2)
    assert results[1] == dict(data.RECORD3, id=id3)


async def test_query_filter_id_in(driver: BaseDriver) -> None:
    id1 = await driver.insert(data.COLL1, data.RECORD1)
    await driver.insert(data.COLL1, data.RECORD2)
    id3 = await driver.insert(data.COLL1, data.RECORD3)

    results = await driver.query(data.COLL1, fields=None, filt={"id": {"in": [id1, id3]}}, sort=[], limit=None)
    results = list(results)
    assert len(results) == 2

    results.sort(key=lambda r: r["int_key"])

    assert results[0] == dict(data.RECORD1, id=id1)
    assert results[1] == dict(data.RECORD3, id=id3)


async def test_query_sort_simple(driver: BaseDriver) -> None:
    id1 = await driver.insert(data.COLL1, data.RECORD1)
    id2 = await driver.insert(data.COLL1, data.RECORD2)
    id3 = await driver.insert(data.COLL1, data.RECORD3)

    results = await driver.query(data.COLL1, fields=None, filt={}, sort=[("int_key", False)], limit=None)
    results = list(results)
    assert len(results) == 3

    assert results[0]["id"] == id1
    assert results[1]["id"] == id2
    assert results[2]["id"] == id3


async def test_query_sort_desc(driver: BaseDriver) -> None:
    id1 = await driver.insert(data.COLL1, data.RECORD1)
    id2 = await driver.insert(data.COLL1, data.RECORD2)
    id3 = await driver.insert(data.COLL1, data.RECORD3)

    results = await driver.query(data.COLL1, fields=None, filt={}, sort=[("int_key", True)], limit=None)
    results = list(results)
    assert len(results) == 3

    assert results[0]["id"] == id3
    assert results[1]["id"] == id2
    assert results[2]["id"] == id1


async def test_query_sort_composite(driver: BaseDriver) -> None:
    id1 = await driver.insert(data.COLL1, data.RECORD1)
    id2 = await driver.insert(data.COLL1, data.RECORD2)
    id3 = await driver.insert(data.COLL1, data.RECORD3)

    results = await driver.query(
        data.COLL1, fields=None, filt={}, sort=[("non_unique_key", False), ("int_key", True)], limit=None
    )
    results = list(results)
    assert len(results) == 3

    assert results[0]["id"] == id2
    assert results[1]["id"] == id3
    assert results[2]["id"] == id1


async def test_query_sort_id(driver: BaseDriver) -> None:
    # Ensure autogenerated ids are sortable

    ids = []
    for i in range(20):
        ids.append(await driver.insert(data.COLL1, data.RECORD1))

    results = await driver.query(data.COLL1, fields=None, filt={}, sort=[("id", False)], limit=None)
    results = list(results)
    assert len(results) == len(ids)

    for i, id_ in enumerate(ids):
        assert results[i]["id"] == id_


async def test_query_limit(driver: BaseDriver) -> None:
    await driver.insert(data.COLL1, data.RECORD1)
    await driver.insert(data.COLL1, data.RECORD2)
    await driver.insert(data.COLL1, data.RECORD3)

    results = await driver.query(data.COLL1, fields=None, filt={}, sort=[], limit=2)
    results = list(results)
    assert len(results) == 2


async def test_query_limit_more(driver: BaseDriver) -> None:
    await driver.insert(data.COLL1, data.RECORD1)
    await driver.insert(data.COLL1, data.RECORD2)
    await driver.insert(data.COLL1, data.RECORD3)

    results = await driver.query(data.COLL1, fields=None, filt={}, sort=[], limit=4)
    results = list(results)
    assert len(results) == 3


async def test_query_fields_filter(driver: BaseDriver) -> None:
    await driver.insert(data.COLL1, data.RECORD1)
    await driver.insert(data.COLL1, data.RECORD2)
    await driver.insert(data.COLL1, data.RECORD3)

    results = await driver.query(data.COLL1, fields=["string_key"], filt={"int_key": {"gt": 1}}, sort=[], limit=None)
    results = list(results)
    assert len(results) == 2

    results.sort(key=lambda r: r["string_key"])
    assert results[0] == {"string_key": data.RECORD2["string_key"]}
    assert results[1] == {"string_key": data.RECORD3["string_key"]}


async def test_query_fields_sort_id(driver: BaseDriver) -> None:
    id1 = await driver.insert(data.COLL1, data.RECORD1)
    id2 = await driver.insert(data.COLL1, data.RECORD2)
    id3 = await driver.insert(data.COLL1, data.RECORD3)

    results = await driver.query(data.COLL1, fields=["id"], filt={}, sort=[("id", False)], limit=None)
    results = list(results)
    assert len(results) == 3

    assert results[0] == {"id": id1}
    assert results[1] == {"id": id2}
    assert results[2] == {"id": id3}


async def test_query_filter_sort(driver: BaseDriver) -> None:
    await driver.insert(data.COLL1, data.RECORD1)
    id2 = await driver.insert(data.COLL1, data.RECORD2)
    id3 = await driver.insert(data.COLL1, data.RECORD3)

    results = await driver.query(
        data.COLL1, fields=None, filt={"int_key": {"gt": 1}}, sort=[("float_key", True)], limit=None
    )
    results = list(results)

    assert results[0] == dict(data.RECORD3, id=id3)
    assert results[1] == dict(data.RECORD2, id=id2)


async def test_query_filter_limit(driver: BaseDriver) -> None:
    await driver.insert(data.COLL1, data.RECORD1)
    id2 = await driver.insert(data.COLL1, data.RECORD2)
    await driver.insert(data.COLL1, data.RECORD3)

    results = await driver.query(data.COLL1, fields=None, filt={"int_key": {"gt": 1}}, sort=[], limit=1)
    results = list(results)
    assert len(results) == 1

    assert results[0] == dict(data.RECORD2, id=id2)


async def test_query_sort_limit(driver: BaseDriver) -> None:
    id1 = await driver.insert(data.COLL1, data.RECORD1)
    await driver.insert(data.COLL1, data.RECORD2)
    id3 = await driver.insert(data.COLL1, data.RECORD3)

    results = await driver.query(data.COLL1, fields=None, filt={}, sort=[("float_key", True)], limit=2)
    results = list(results)
    assert len(results) == 2

    assert results[0] == dict(data.RECORD1, id=id1)
    assert results[1] == dict(data.RECORD3, id=id3)


async def test_query_filter_sort_limit(driver: BaseDriver) -> None:
    await driver.insert(data.COLL1, data.RECORD1)
    id2 = await driver.insert(data.COLL1, data.RECORD2)
    await driver.insert(data.COLL1, data.RECORD3)

    results = await driver.query(
        data.COLL1, fields=None, filt={"int_key": {"gt": 1}}, sort=[("float_key", False)], limit=1
    )
    results = list(results)
    assert len(results) == 1

    assert results[0] == dict(data.RECORD2, id=id2)
