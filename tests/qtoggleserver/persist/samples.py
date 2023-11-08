from qtoggleserver.persist import BaseDriver

from . import data


# The `save_sample` method is implicitly tested by the rest of the tests.


async def test_get_samples_slice_all(driver: BaseDriver) -> None:
    await driver.save_sample(data.COLL1, data.SAMPLE_OBJ_ID1, *data.SAMPLE1)
    await driver.save_sample(data.COLL1, data.SAMPLE_OBJ_ID1, *data.SAMPLE2)
    await driver.save_sample(data.COLL1, data.SAMPLE_OBJ_ID1, *data.SAMPLE3)
    await driver.save_sample(data.COLL1, data.SAMPLE_OBJ_ID1, *data.SAMPLE4)

    results = await driver.get_samples_slice(
        collection=data.COLL1,
        obj_id=data.SAMPLE_OBJ_ID1,
        from_timestamp=None,
        to_timestamp=None,
        limit=None,
        sort_desc=False,
    )
    results = list(results)

    assert results == [data.SAMPLE1, data.SAMPLE2, data.SAMPLE3, data.SAMPLE4]


async def test_get_samples_slice_from_timestamp(driver: BaseDriver) -> None:
    await driver.save_sample(data.COLL1, data.SAMPLE_OBJ_ID1, *data.SAMPLE1)
    await driver.save_sample(data.COLL1, data.SAMPLE_OBJ_ID1, *data.SAMPLE2)
    await driver.save_sample(data.COLL1, data.SAMPLE_OBJ_ID1, *data.SAMPLE3)
    await driver.save_sample(data.COLL1, data.SAMPLE_OBJ_ID1, *data.SAMPLE4)

    results = await driver.get_samples_slice(
        collection=data.COLL1,
        obj_id=data.SAMPLE_OBJ_ID1,
        from_timestamp=data.SAMPLE2[0],
        to_timestamp=None,
        limit=None,
        sort_desc=False,
    )
    results = list(results)

    assert results == [data.SAMPLE2, data.SAMPLE3, data.SAMPLE4]


async def test_get_samples_slice_to_timestamp(driver: BaseDriver) -> None:
    await driver.save_sample(data.COLL1, data.SAMPLE_OBJ_ID1, *data.SAMPLE1)
    await driver.save_sample(data.COLL1, data.SAMPLE_OBJ_ID1, *data.SAMPLE2)
    await driver.save_sample(data.COLL1, data.SAMPLE_OBJ_ID1, *data.SAMPLE3)
    await driver.save_sample(data.COLL1, data.SAMPLE_OBJ_ID1, *data.SAMPLE4)

    results = await driver.get_samples_slice(
        collection=data.COLL1,
        obj_id=data.SAMPLE_OBJ_ID1,
        from_timestamp=None,
        to_timestamp=data.SAMPLE4[0],
        limit=None,
        sort_desc=False,
    )
    results = list(results)

    assert results == [data.SAMPLE1, data.SAMPLE2, data.SAMPLE3]


async def test_get_samples_slice_from_to_timestamp(driver: BaseDriver) -> None:
    await driver.save_sample(data.COLL1, data.SAMPLE_OBJ_ID1, *data.SAMPLE1)
    await driver.save_sample(data.COLL1, data.SAMPLE_OBJ_ID1, *data.SAMPLE2)
    await driver.save_sample(data.COLL1, data.SAMPLE_OBJ_ID1, *data.SAMPLE3)
    await driver.save_sample(data.COLL1, data.SAMPLE_OBJ_ID1, *data.SAMPLE4)

    results = await driver.get_samples_slice(
        collection=data.COLL1,
        obj_id=data.SAMPLE_OBJ_ID1,
        from_timestamp=data.SAMPLE2[0],
        to_timestamp=data.SAMPLE4[0],
        limit=None,
        sort_desc=False,
    )
    results = list(results)

    assert results == [data.SAMPLE2, data.SAMPLE3]


async def test_get_samples_slice_from_to_timestamp_sort_desc(driver: BaseDriver) -> None:
    await driver.save_sample(data.COLL1, data.SAMPLE_OBJ_ID1, *data.SAMPLE1)
    await driver.save_sample(data.COLL1, data.SAMPLE_OBJ_ID1, *data.SAMPLE2)
    await driver.save_sample(data.COLL1, data.SAMPLE_OBJ_ID1, *data.SAMPLE3)
    await driver.save_sample(data.COLL1, data.SAMPLE_OBJ_ID1, *data.SAMPLE4)

    results = await driver.get_samples_slice(
        collection=data.COLL1,
        obj_id=data.SAMPLE_OBJ_ID1,
        from_timestamp=data.SAMPLE2[0],
        to_timestamp=data.SAMPLE4[0],
        limit=None,
        sort_desc=True,
    )
    results = list(results)

    assert results == [data.SAMPLE3, data.SAMPLE2]


async def test_get_samples_slice_from_timestamp_limit(driver: BaseDriver) -> None:
    await driver.save_sample(data.COLL1, data.SAMPLE_OBJ_ID1, *data.SAMPLE1)
    await driver.save_sample(data.COLL1, data.SAMPLE_OBJ_ID1, *data.SAMPLE2)
    await driver.save_sample(data.COLL1, data.SAMPLE_OBJ_ID1, *data.SAMPLE3)
    await driver.save_sample(data.COLL1, data.SAMPLE_OBJ_ID1, *data.SAMPLE4)

    results = await driver.get_samples_slice(
        collection=data.COLL1,
        obj_id=data.SAMPLE_OBJ_ID1,
        from_timestamp=data.SAMPLE2[0],
        to_timestamp=None,
        limit=2,
        sort_desc=False,
    )
    results = list(results)

    assert results == [data.SAMPLE2, data.SAMPLE3]


async def test_get_samples_slice_to_timestamp_limit(driver: BaseDriver) -> None:
    await driver.save_sample(data.COLL1, data.SAMPLE_OBJ_ID1, *data.SAMPLE1)
    await driver.save_sample(data.COLL1, data.SAMPLE_OBJ_ID1, *data.SAMPLE2)
    await driver.save_sample(data.COLL1, data.SAMPLE_OBJ_ID1, *data.SAMPLE3)
    await driver.save_sample(data.COLL1, data.SAMPLE_OBJ_ID1, *data.SAMPLE4)

    results = await driver.get_samples_slice(
        collection=data.COLL1,
        obj_id=data.SAMPLE_OBJ_ID1,
        from_timestamp=None,
        to_timestamp=data.SAMPLE4[0],
        limit=2,
        sort_desc=False,
    )
    results = list(results)

    assert results == [data.SAMPLE1, data.SAMPLE2]


async def test_get_samples_slice_all_sort_desc(driver: BaseDriver) -> None:
    await driver.save_sample(data.COLL1, data.SAMPLE_OBJ_ID1, *data.SAMPLE1)
    await driver.save_sample(data.COLL1, data.SAMPLE_OBJ_ID1, *data.SAMPLE2)
    await driver.save_sample(data.COLL1, data.SAMPLE_OBJ_ID1, *data.SAMPLE3)
    await driver.save_sample(data.COLL1, data.SAMPLE_OBJ_ID1, *data.SAMPLE4)

    results = await driver.get_samples_slice(
        collection=data.COLL1,
        obj_id=data.SAMPLE_OBJ_ID1,
        from_timestamp=None,
        to_timestamp=None,
        limit=None,
        sort_desc=True,
    )
    results = list(results)

    assert results == [data.SAMPLE4, data.SAMPLE3, data.SAMPLE2, data.SAMPLE1]


async def test_get_samples_slice_limit(driver: BaseDriver) -> None:
    await driver.save_sample(data.COLL1, data.SAMPLE_OBJ_ID1, *data.SAMPLE1)
    await driver.save_sample(data.COLL1, data.SAMPLE_OBJ_ID1, *data.SAMPLE2)
    await driver.save_sample(data.COLL1, data.SAMPLE_OBJ_ID1, *data.SAMPLE3)
    await driver.save_sample(data.COLL1, data.SAMPLE_OBJ_ID1, *data.SAMPLE4)

    results = await driver.get_samples_slice(
        collection=data.COLL1,
        obj_id=data.SAMPLE_OBJ_ID1,
        from_timestamp=None,
        to_timestamp=None,
        limit=2,
        sort_desc=False,
    )
    results = list(results)

    assert results == [data.SAMPLE1, data.SAMPLE2]


async def test_get_samples_slice_limit_more(driver: BaseDriver) -> None:
    await driver.save_sample(data.COLL1, data.SAMPLE_OBJ_ID1, *data.SAMPLE1)
    await driver.save_sample(data.COLL1, data.SAMPLE_OBJ_ID1, *data.SAMPLE2)
    await driver.save_sample(data.COLL1, data.SAMPLE_OBJ_ID1, *data.SAMPLE3)
    await driver.save_sample(data.COLL1, data.SAMPLE_OBJ_ID1, *data.SAMPLE4)

    results = await driver.get_samples_slice(
        collection=data.COLL1,
        obj_id=data.SAMPLE_OBJ_ID1,
        from_timestamp=None,
        to_timestamp=None,
        limit=6,
        sort_desc=False,
    )
    results = list(results)

    assert results == [data.SAMPLE1, data.SAMPLE2, data.SAMPLE3, data.SAMPLE4]


async def test_get_samples_slice_limit_sort_desc(driver: BaseDriver) -> None:
    await driver.save_sample(data.COLL1, data.SAMPLE_OBJ_ID1, *data.SAMPLE1)
    await driver.save_sample(data.COLL1, data.SAMPLE_OBJ_ID1, *data.SAMPLE2)
    await driver.save_sample(data.COLL1, data.SAMPLE_OBJ_ID1, *data.SAMPLE3)
    await driver.save_sample(data.COLL1, data.SAMPLE_OBJ_ID1, *data.SAMPLE4)

    results = await driver.get_samples_slice(
        collection=data.COLL1,
        obj_id=data.SAMPLE_OBJ_ID1,
        from_timestamp=None,
        to_timestamp=None,
        limit=2,
        sort_desc=True,
    )
    results = list(results)

    assert results == [data.SAMPLE4, data.SAMPLE3]


async def test_get_samples_slice_from_to_timestamp_limit_sort_desc(driver: BaseDriver) -> None:
    await driver.save_sample(data.COLL1, data.SAMPLE_OBJ_ID1, *data.SAMPLE1)
    await driver.save_sample(data.COLL1, data.SAMPLE_OBJ_ID1, *data.SAMPLE2)
    await driver.save_sample(data.COLL1, data.SAMPLE_OBJ_ID1, *data.SAMPLE3)
    await driver.save_sample(data.COLL1, data.SAMPLE_OBJ_ID1, *data.SAMPLE4)

    results = await driver.get_samples_slice(
        collection=data.COLL1,
        obj_id=data.SAMPLE_OBJ_ID1,
        from_timestamp=data.SAMPLE2[0],
        to_timestamp=data.SAMPLE4[0],
        limit=1,
        sort_desc=True,
    )
    results = list(results)

    assert results == [data.SAMPLE3]


async def test_get_samples_slice_obj_id_separation(driver: BaseDriver) -> None:
    await driver.save_sample(data.COLL1, data.SAMPLE_OBJ_ID1, *data.SAMPLE1)
    await driver.save_sample(data.COLL1, data.SAMPLE_OBJ_ID1, *data.SAMPLE2)
    await driver.save_sample(data.COLL1, data.SAMPLE_OBJ_ID2, *data.SAMPLE3)
    await driver.save_sample(data.COLL1, data.SAMPLE_OBJ_ID2, *data.SAMPLE4)

    results = await driver.get_samples_slice(
        collection=data.COLL1,
        obj_id=data.SAMPLE_OBJ_ID1,
        from_timestamp=None,
        to_timestamp=None,
        limit=None,
        sort_desc=False,
    )
    results = list(results)

    assert results == [data.SAMPLE1, data.SAMPLE2]


async def test_get_samples_by_timestamp_exact(driver: BaseDriver) -> None:
    await driver.save_sample(data.COLL1, data.SAMPLE_OBJ_ID1, *data.SAMPLE1)
    await driver.save_sample(data.COLL1, data.SAMPLE_OBJ_ID1, *data.SAMPLE2)
    await driver.save_sample(data.COLL1, data.SAMPLE_OBJ_ID1, *data.SAMPLE3)
    await driver.save_sample(data.COLL1, data.SAMPLE_OBJ_ID1, *data.SAMPLE4)

    results = await driver.get_samples_by_timestamp(
        collection=data.COLL1,
        obj_id=data.SAMPLE_OBJ_ID1,
        timestamps=[data.SAMPLE1[0], data.SAMPLE2[0], data.SAMPLE3[0], data.SAMPLE4[0]]
    )
    results = list(results)

    assert results == [data.SAMPLE1[1], data.SAMPLE2[1], data.SAMPLE3[1], data.SAMPLE4[1]]


async def test_get_samples_by_timestamp_after(driver: BaseDriver) -> None:
    await driver.save_sample(data.COLL1, data.SAMPLE_OBJ_ID1, *data.SAMPLE1)
    await driver.save_sample(data.COLL1, data.SAMPLE_OBJ_ID1, *data.SAMPLE2)
    await driver.save_sample(data.COLL1, data.SAMPLE_OBJ_ID1, *data.SAMPLE3)
    await driver.save_sample(data.COLL1, data.SAMPLE_OBJ_ID1, *data.SAMPLE4)

    results = await driver.get_samples_by_timestamp(
        collection=data.COLL1,
        obj_id=data.SAMPLE_OBJ_ID1,
        timestamps=[data.SAMPLE1[0] + 1, data.SAMPLE2[0] + 1, data.SAMPLE3[0] + 1, data.SAMPLE4[0] + 1]
    )
    results = list(results)

    assert results == [data.SAMPLE1[1], data.SAMPLE2[1], data.SAMPLE3[1], data.SAMPLE4[1]]


async def test_get_samples_by_timestamp_unsorted(driver: BaseDriver) -> None:
    await driver.save_sample(data.COLL1, data.SAMPLE_OBJ_ID1, *data.SAMPLE1)
    await driver.save_sample(data.COLL1, data.SAMPLE_OBJ_ID1, *data.SAMPLE2)
    await driver.save_sample(data.COLL1, data.SAMPLE_OBJ_ID1, *data.SAMPLE3)
    await driver.save_sample(data.COLL1, data.SAMPLE_OBJ_ID1, *data.SAMPLE4)

    results = await driver.get_samples_by_timestamp(
        collection=data.COLL1,
        obj_id=data.SAMPLE_OBJ_ID1,
        timestamps=[data.SAMPLE4[0] + 1, data.SAMPLE1[0], data.SAMPLE3[0], data.SAMPLE2[0] + 1]
    )
    results = list(results)

    assert results == [data.SAMPLE4[1], data.SAMPLE1[1], data.SAMPLE3[1], data.SAMPLE2[1]]


async def test_get_samples_by_timestamp_same_value(driver: BaseDriver) -> None:
    await driver.save_sample(data.COLL1, data.SAMPLE_OBJ_ID1, *data.SAMPLE1)
    await driver.save_sample(data.COLL1, data.SAMPLE_OBJ_ID1, *data.SAMPLE2)
    await driver.save_sample(data.COLL1, data.SAMPLE_OBJ_ID1, *data.SAMPLE3)
    await driver.save_sample(data.COLL1, data.SAMPLE_OBJ_ID1, *data.SAMPLE4)

    results = await driver.get_samples_by_timestamp(
        collection=data.COLL1,
        obj_id=data.SAMPLE_OBJ_ID1,
        timestamps=[data.SAMPLE2[0], data.SAMPLE2[0] + 1, data.SAMPLE2[0] + 2]
    )
    results = list(results)

    assert results == [data.SAMPLE2[1], data.SAMPLE2[1], data.SAMPLE2[1]]


async def test_get_samples_by_timestamp_obj_id_separation(driver: BaseDriver) -> None:
    await driver.save_sample(data.COLL1, data.SAMPLE_OBJ_ID1, *data.SAMPLE1)
    await driver.save_sample(data.COLL1, data.SAMPLE_OBJ_ID1, *data.SAMPLE2)
    await driver.save_sample(data.COLL1, data.SAMPLE_OBJ_ID2, *data.SAMPLE3)
    await driver.save_sample(data.COLL1, data.SAMPLE_OBJ_ID2, *data.SAMPLE4)

    results = await driver.get_samples_by_timestamp(
        collection=data.COLL1,
        obj_id=data.SAMPLE_OBJ_ID1,
        timestamps=[data.SAMPLE1[0], data.SAMPLE2[0], data.SAMPLE3[0], data.SAMPLE4[0]]
    )
    results = list(results)

    assert results == [data.SAMPLE1[1], data.SAMPLE2[1], data.SAMPLE2[1], data.SAMPLE2[1]]


async def test_remove_samples_all(driver: BaseDriver) -> None:
    await driver.save_sample(data.COLL1, data.SAMPLE_OBJ_ID1, *data.SAMPLE1)
    await driver.save_sample(data.COLL1, data.SAMPLE_OBJ_ID1, *data.SAMPLE2)
    await driver.save_sample(data.COLL1, data.SAMPLE_OBJ_ID2, *data.SAMPLE3)
    await driver.save_sample(data.COLL1, data.SAMPLE_OBJ_ID2, *data.SAMPLE4)

    result = await driver.remove_samples(
        collection=data.COLL1,
        obj_ids=None,
        from_timestamp=None,
        to_timestamp=None,
    )
    assert result == 4

    results = await driver.get_samples_slice(
        collection=data.COLL1,
        obj_id=data.SAMPLE_OBJ_ID1,
        from_timestamp=None,
        to_timestamp=None,
        limit=None,
        sort_desc=False,
    )
    results = list(results)
    assert results == []

    results = await driver.get_samples_slice(
        collection=data.COLL1,
        obj_id=data.SAMPLE_OBJ_ID2,
        from_timestamp=None,
        to_timestamp=None,
        limit=None,
        sort_desc=False,
    )
    results = list(results)
    assert results == []


async def test_remove_samples_from_timestamp(driver: BaseDriver) -> None:
    await driver.save_sample(data.COLL1, data.SAMPLE_OBJ_ID1, *data.SAMPLE1)
    await driver.save_sample(data.COLL1, data.SAMPLE_OBJ_ID1, *data.SAMPLE2)
    await driver.save_sample(data.COLL1, data.SAMPLE_OBJ_ID1, *data.SAMPLE3)
    await driver.save_sample(data.COLL1, data.SAMPLE_OBJ_ID1, *data.SAMPLE4)

    result = await driver.remove_samples(
        collection=data.COLL1,
        obj_ids=[data.SAMPLE_OBJ_ID1],
        from_timestamp=data.SAMPLE2[0],
        to_timestamp=None,
    )
    assert result == 3

    results = await driver.get_samples_slice(
        collection=data.COLL1,
        obj_id=data.SAMPLE_OBJ_ID1,
        from_timestamp=None,
        to_timestamp=None,
        limit=None,
        sort_desc=False,
    )
    results = list(results)
    assert results == [data.SAMPLE1]


async def test_remove_samples_to_timestamp(driver: BaseDriver) -> None:
    await driver.save_sample(data.COLL1, data.SAMPLE_OBJ_ID1, *data.SAMPLE1)
    await driver.save_sample(data.COLL1, data.SAMPLE_OBJ_ID1, *data.SAMPLE2)
    await driver.save_sample(data.COLL1, data.SAMPLE_OBJ_ID1, *data.SAMPLE3)
    await driver.save_sample(data.COLL1, data.SAMPLE_OBJ_ID1, *data.SAMPLE4)

    result = await driver.remove_samples(
        collection=data.COLL1,
        obj_ids=[data.SAMPLE_OBJ_ID1],
        from_timestamp=None,
        to_timestamp=data.SAMPLE4[0],
    )
    assert result == 3

    results = await driver.get_samples_slice(
        collection=data.COLL1,
        obj_id=data.SAMPLE_OBJ_ID1,
        from_timestamp=None,
        to_timestamp=None,
        limit=None,
        sort_desc=False,
    )
    results = list(results)
    assert results == [data.SAMPLE4]


async def test_remove_samples_from_to_timestamp(driver: BaseDriver) -> None:
    await driver.save_sample(data.COLL1, data.SAMPLE_OBJ_ID1, *data.SAMPLE1)
    await driver.save_sample(data.COLL1, data.SAMPLE_OBJ_ID1, *data.SAMPLE2)
    await driver.save_sample(data.COLL1, data.SAMPLE_OBJ_ID1, *data.SAMPLE3)
    await driver.save_sample(data.COLL1, data.SAMPLE_OBJ_ID1, *data.SAMPLE4)

    result = await driver.remove_samples(
        collection=data.COLL1,
        obj_ids=[data.SAMPLE_OBJ_ID1],
        from_timestamp=data.SAMPLE2[0],
        to_timestamp=data.SAMPLE4[0],
    )
    assert result == 2

    results = await driver.get_samples_slice(
        collection=data.COLL1,
        obj_id=data.SAMPLE_OBJ_ID1,
        from_timestamp=None,
        to_timestamp=None,
        limit=None,
        sort_desc=False,
    )
    results = list(results)
    assert results == [data.SAMPLE1, data.SAMPLE4]


async def test_remove_samples_obj_id_separation(driver: BaseDriver) -> None:
    await driver.save_sample(data.COLL1, data.SAMPLE_OBJ_ID1, *data.SAMPLE1)
    await driver.save_sample(data.COLL1, data.SAMPLE_OBJ_ID1, *data.SAMPLE2)
    await driver.save_sample(data.COLL1, data.SAMPLE_OBJ_ID2, *data.SAMPLE3)
    await driver.save_sample(data.COLL1, data.SAMPLE_OBJ_ID2, *data.SAMPLE4)

    result = await driver.remove_samples(
        collection=data.COLL1,
        obj_ids=[data.SAMPLE_OBJ_ID1],
        from_timestamp=None,
        to_timestamp=None,
    )
    assert result == 2

    results = await driver.get_samples_slice(
        collection=data.COLL1,
        obj_id=data.SAMPLE_OBJ_ID1,
        from_timestamp=None,
        to_timestamp=None,
        limit=None,
        sort_desc=False,
    )
    results = list(results)
    assert results == []

    results = await driver.get_samples_slice(
        collection=data.COLL1,
        obj_id=data.SAMPLE_OBJ_ID2,
        from_timestamp=None,
        to_timestamp=None,
        limit=None,
        sort_desc=False,
    )
    results = list(results)
    assert results == [data.SAMPLE3, data.SAMPLE4]
