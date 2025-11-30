import mongomock
import pymongo
import pytest

from qtoggleserver.drivers.persist import mongo
from qtoggleserver.persist import BaseDriver

from . import insert, misc, query, remove, replace, samples, update


@pytest.fixture
async def driver(monkeypatch) -> BaseDriver:
    monkeypatch.setattr(pymongo, "MongoClient", mongomock.MongoClient)
    driver = mongo.MongoDriver()
    await driver.init()
    return driver


async def test_query_all(driver: BaseDriver) -> None:
    await query.test_query_all(driver)


async def test_query_fields(driver: BaseDriver) -> None:
    await query.test_query_fields(driver)


async def test_query_fields_inexistent(driver: BaseDriver) -> None:
    await query.test_query_fields_inexistent(driver)


async def test_query_filter_id(driver: BaseDriver) -> None:
    await query.test_query_filter_id(driver)


async def test_query_filter_id_inexistent(driver: BaseDriver) -> None:
    await query.test_query_filter_id_inexistent(driver)


async def test_query_filter_custom_id_inexistent(driver: BaseDriver) -> None:
    await query.test_query_filter_custom_id_inexistent(driver)


async def test_query_filter_simple(driver: BaseDriver) -> None:
    await query.test_query_filter_simple(driver)


async def test_query_filter_ge_lt(driver: BaseDriver) -> None:
    await query.test_query_filter_ge_lt(driver)


async def test_query_filter_gt_le(driver: BaseDriver) -> None:
    await query.test_query_filter_gt_le(driver)


async def test_query_filter_in(driver: BaseDriver) -> None:
    await query.test_query_filter_in(driver)


async def test_query_filter_id_in(driver: BaseDriver) -> None:
    await query.test_query_filter_id_in(driver)


async def test_query_sort_simple(driver: BaseDriver) -> None:
    await query.test_query_sort_simple(driver)


async def test_query_sort_desc(driver: BaseDriver) -> None:
    await query.test_query_sort_desc(driver)


async def test_query_sort_composite(driver: BaseDriver) -> None:
    await query.test_query_sort_composite(driver)


async def test_query_sort_id(driver: BaseDriver) -> None:
    await query.test_query_sort_id(driver)


async def test_query_limit(driver: BaseDriver) -> None:
    await query.test_query_limit(driver)


async def test_query_limit_more(driver: BaseDriver) -> None:
    await query.test_query_limit_more(driver)


async def test_query_fields_filter(driver: BaseDriver) -> None:
    await query.test_query_fields_filter(driver)


async def test_query_fields_sort_id(driver: BaseDriver) -> None:
    await query.test_query_fields_sort_id(driver)


async def test_query_filter_sort(driver: BaseDriver) -> None:
    await query.test_query_filter_sort(driver)


async def test_query_filter_limit(driver: BaseDriver) -> None:
    await query.test_query_filter_limit(driver)


async def test_query_sort_limit(driver: BaseDriver) -> None:
    await query.test_query_sort_limit(driver)


async def test_query_filter_sort_limit(driver: BaseDriver) -> None:
    await query.test_query_filter_sort_limit(driver)


async def test_insert_simple(driver: BaseDriver) -> None:
    await insert.test_insert_simple(driver)


async def test_insert_multiple(driver: BaseDriver) -> None:
    await insert.test_insert_multiple(driver)


async def test_insert_empty(driver: BaseDriver) -> None:
    await insert.test_insert_empty(driver)


async def test_insert_with_custom_id_simple(driver: BaseDriver) -> None:
    await insert.test_insert_with_custom_id_simple(driver)


async def test_insert_with_custom_id_complex(driver: BaseDriver) -> None:
    await insert.test_insert_with_custom_id_complex(driver)


async def test_remove_by_id(driver: BaseDriver) -> None:
    await remove.test_remove_by_id(driver)


async def test_remove_filter(driver: BaseDriver) -> None:
    await remove.test_remove_filter(driver)


async def test_remove_all(driver: BaseDriver) -> None:
    await remove.test_remove_all(driver)


async def test_remove_inexistent_record(driver: BaseDriver) -> None:
    await remove.test_remove_inexistent_record(driver)


async def test_remove_inexistent_field(driver: BaseDriver) -> None:
    await remove.test_remove_inexistent_field(driver)


async def test_remove_no_match(driver: BaseDriver) -> None:
    await remove.test_remove_no_match(driver)


async def test_remove_custom_id_simple(driver: BaseDriver) -> None:
    await remove.test_remove_custom_id_simple(driver)


async def test_remove_custom_id_complex(driver: BaseDriver) -> None:
    await remove.test_remove_custom_id_complex(driver)


async def test_remove_no_match_custom_id_simple(driver: BaseDriver) -> None:
    await remove.test_remove_no_match_custom_id_simple(driver)


async def test_remove_no_match_custom_id_complex(driver: BaseDriver) -> None:
    await remove.test_remove_no_match_custom_id_complex(driver)


async def test_replace_no_match(driver: BaseDriver) -> None:
    await replace.test_replace_no_match(driver)


async def test_replace_match(driver: BaseDriver) -> None:
    await replace.test_replace_match(driver)


async def test_replace_match_with_id(driver: BaseDriver) -> None:
    await replace.test_replace_match_with_id(driver)


async def test_replace_match_fewer_fields(driver: BaseDriver) -> None:
    await replace.test_replace_match_fewer_fields(driver)


async def test_replace_custom_id_simple(driver: BaseDriver) -> None:
    await replace.test_replace_custom_id_simple(driver)


async def test_replace_custom_id_complex(driver: BaseDriver) -> None:
    await replace.test_replace_custom_id_complex(driver)


async def test_replace_no_match_custom_id(driver: BaseDriver) -> None:
    await replace.test_replace_no_match_custom_id(driver)


async def test_update_match_id(driver: BaseDriver) -> None:
    await update.test_update_match_id(driver)


async def test_update_match_many(driver: BaseDriver) -> None:
    await update.test_update_match_many(driver)


async def test_update_no_match(driver: BaseDriver) -> None:
    await update.test_update_no_match(driver)


async def test_update_few_fields(driver: BaseDriver) -> None:
    await update.test_update_few_fields(driver)


async def test_update_new_fields(driver: BaseDriver) -> None:
    await update.test_update_new_fields(driver)


async def test_update_custom_id_simple(driver: BaseDriver) -> None:
    await update.test_update_custom_id_simple(driver)


async def test_update_custom_id_complex(driver: BaseDriver) -> None:
    await update.test_update_custom_id_complex(driver)


async def test_update_no_match_custom_id_simple(driver: BaseDriver) -> None:
    await update.test_update_no_match_custom_id_simple(driver)


async def test_update_no_match_custom_id_complex(driver: BaseDriver) -> None:
    await update.test_update_no_match_custom_id_complex(driver)


async def test_get_samples_slice_all(driver: BaseDriver) -> None:
    await samples.test_get_samples_slice_all(driver)


async def test_get_samples_slice_from_timestamp(driver: BaseDriver) -> None:
    await samples.test_get_samples_slice_from_timestamp(driver)


async def test_get_samples_slice_to_timestamp(driver: BaseDriver) -> None:
    await samples.test_get_samples_slice_to_timestamp(driver)


async def test_get_samples_slice_from_to_timestamp(driver: BaseDriver) -> None:
    await samples.test_get_samples_slice_from_to_timestamp(driver)


async def test_get_samples_slice_from_to_timestamp_sort_desc(driver: BaseDriver) -> None:
    await samples.test_get_samples_slice_from_to_timestamp_sort_desc(driver)


async def test_get_samples_slice_from_timestamp_limit(driver: BaseDriver) -> None:
    await samples.test_get_samples_slice_from_timestamp_limit(driver)


async def test_get_samples_slice_to_timestamp_limit(driver: BaseDriver) -> None:
    await samples.test_get_samples_slice_to_timestamp_limit(driver)


async def test_get_samples_slice_all_sort_desc(driver: BaseDriver) -> None:
    await samples.test_get_samples_slice_all_sort_desc(driver)


async def test_get_samples_slice_limit(driver: BaseDriver) -> None:
    await samples.test_get_samples_slice_limit(driver)


async def test_get_samples_slice_limit_more(driver: BaseDriver) -> None:
    await samples.test_get_samples_slice_limit_more(driver)


async def test_get_samples_slice_limit_sort_desc(driver: BaseDriver) -> None:
    await samples.test_get_samples_slice_limit_sort_desc(driver)


async def test_get_samples_slice_from_to_timestamp_limit_sort_desc(driver: BaseDriver) -> None:
    await samples.test_get_samples_slice_from_to_timestamp_limit_sort_desc(driver)


async def test_get_samples_slice_obj_id_separation(driver: BaseDriver) -> None:
    await samples.test_get_samples_slice_obj_id_separation(driver)


async def test_get_samples_by_timestamp_exact(driver: BaseDriver) -> None:
    await samples.test_get_samples_by_timestamp_exact(driver)


async def test_get_samples_by_timestamp_after(driver: BaseDriver) -> None:
    await samples.test_get_samples_by_timestamp_after(driver)


async def test_get_samples_by_timestamp_unsorted(driver: BaseDriver) -> None:
    await samples.test_get_samples_by_timestamp_unsorted(driver)


async def test_get_samples_by_timestamp_same_value(driver: BaseDriver) -> None:
    await samples.test_get_samples_by_timestamp_same_value(driver)


async def test_get_samples_by_timestamp_obj_id_separation(driver: BaseDriver) -> None:
    await samples.test_get_samples_by_timestamp_obj_id_separation(driver)


async def test_remove_samples_all(driver: BaseDriver) -> None:
    await samples.test_remove_samples_all(driver)


async def test_remove_samples_from_timestamp(driver: BaseDriver) -> None:
    await samples.test_remove_samples_from_timestamp(driver)


async def test_remove_samples_to_timestamp(driver: BaseDriver) -> None:
    await samples.test_remove_samples_to_timestamp(driver)


async def test_remove_samples_from_to_timestamp(driver: BaseDriver) -> None:
    await samples.test_remove_samples_from_to_timestamp(driver)


async def test_remove_samples_obj_id_separation(driver: BaseDriver) -> None:
    await samples.test_remove_samples_obj_id_separation(driver)


async def test_collection_separation(driver: BaseDriver) -> None:
    await misc.test_collection_separation(driver)


async def test_data_type_datetime(driver: BaseDriver) -> None:
    await misc.test_data_type_datetime(driver)


async def test_data_type_list(driver: BaseDriver) -> None:
    await misc.test_data_type_list(driver)


async def test_data_type_dict(driver: BaseDriver) -> None:
    await misc.test_data_type_dict(driver)


async def test_data_type_complex(driver: BaseDriver) -> None:
    await misc.test_data_type_complex(driver)


async def test_filter_sort_datetime(driver: BaseDriver) -> None:
    await misc.test_filter_sort_datetime(driver)
