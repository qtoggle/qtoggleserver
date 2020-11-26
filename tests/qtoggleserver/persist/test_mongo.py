
import mongomock
import pymongo
import pytest

from qtoggleserver.drivers.persist import mongo
from qtoggleserver.persist import BaseDriver

from . import insert
from . import misc
from . import remove
from . import replace
from . import query
from . import update


@pytest.fixture
def driver(monkeypatch) -> BaseDriver:
    monkeypatch.setattr(pymongo, 'MongoClient', mongomock.MongoClient)
    return mongo.MongoDriver()


def test_query_all(driver: BaseDriver) -> None:
    query.test_query_all(driver)


def test_query_fields(driver: BaseDriver) -> None:
    query.test_query_fields(driver)


def test_query_fields_inexistent(driver: BaseDriver) -> None:
    query.test_query_fields_inexistent(driver)


def test_query_filter_id(driver: BaseDriver) -> None:
    query.test_query_filter_id(driver)


def test_query_filter_id_inexistent(driver: BaseDriver) -> None:
    query.test_query_filter_id_inexistent(driver)


def test_query_filter_custom_id_inexistent(driver: BaseDriver) -> None:
    query.test_query_filter_custom_id_inexistent(driver)


def test_query_filter_simple(driver: BaseDriver) -> None:
    query.test_query_filter_simple(driver)


def test_query_filter_ge_lt(driver: BaseDriver) -> None:
    query.test_query_filter_ge_lt(driver)


def test_query_filter_gt_le(driver: BaseDriver) -> None:
    query.test_query_filter_gt_le(driver)


def test_query_filter_in(driver: BaseDriver) -> None:
    query.test_query_filter_in(driver)


def test_query_filter_id_in(driver: BaseDriver) -> None:
    query.test_query_filter_id_in(driver)


def test_query_sort_simple(driver: BaseDriver) -> None:
    query.test_query_sort_simple(driver)


def test_query_sort_desc(driver: BaseDriver) -> None:
    query.test_query_sort_desc(driver)


def test_query_sort_composite(driver: BaseDriver) -> None:
    query.test_query_sort_composite(driver)


def test_query_sort_id(driver: BaseDriver) -> None:
    query.test_query_sort_id(driver)


def test_query_limit(driver: BaseDriver) -> None:
    query.test_query_limit(driver)


def test_query_limit_more(driver: BaseDriver) -> None:
    query.test_query_limit_more(driver)


def test_query_fields_filter(driver: BaseDriver) -> None:
    query.test_query_fields_filter(driver)


def test_query_fields_sort_id(driver: BaseDriver) -> None:
    query.test_query_fields_sort_id(driver)


def test_query_filter_sort(driver: BaseDriver) -> None:
    query.test_query_filter_sort(driver)


def test_query_filter_limit(driver: BaseDriver) -> None:
    query.test_query_filter_limit(driver)


def test_query_sort_limit(driver: BaseDriver) -> None:
    query.test_query_sort_limit(driver)


def test_query_filter_sort_limit(driver: BaseDriver) -> None:
    query.test_query_filter_sort_limit(driver)


def test_insert_simple(driver: BaseDriver) -> None:
    insert.test_insert_simple(driver)


def test_insert_multiple(driver: BaseDriver) -> None:
    insert.test_insert_multiple(driver)


def test_insert_empty(driver: BaseDriver) -> None:
    insert.test_insert_empty(driver)


def test_insert_with_custom_id_simple(driver: BaseDriver) -> None:
    insert.test_insert_with_custom_id_simple(driver)


def test_insert_with_custom_id_complex(driver: BaseDriver) -> None:
    insert.test_insert_with_custom_id_complex(driver)


def test_remove_by_id(driver: BaseDriver) -> None:
    remove.test_remove_by_id(driver)


def test_remove_filter(driver: BaseDriver) -> None:
    remove.test_remove_filter(driver)


def test_remove_all(driver: BaseDriver) -> None:
    remove.test_remove_all(driver)


def test_remove_inexistent_record(driver: BaseDriver) -> None:
    remove.test_remove_inexistent_record(driver)


def test_remove_inexistent_field(driver: BaseDriver) -> None:
    remove.test_remove_inexistent_field(driver)


def test_remove_no_match(driver: BaseDriver) -> None:
    remove.test_remove_no_match(driver)


def test_remove_custom_id_simple(driver: BaseDriver) -> None:
    remove.test_remove_custom_id_simple(driver)


def test_remove_custom_id_complex(driver: BaseDriver) -> None:
    remove.test_remove_custom_id_complex(driver)


def test_remove_no_match_custom_id_simple(driver: BaseDriver) -> None:
    remove.test_remove_no_match_custom_id_simple(driver)


def test_remove_no_match_custom_id_complex(driver: BaseDriver) -> None:
    remove.test_remove_no_match_custom_id_complex(driver)


def test_replace_no_match(driver: BaseDriver) -> None:
    replace.test_replace_no_match(driver)


def test_replace_match(driver: BaseDriver) -> None:
    replace.test_replace_match(driver)


def test_replace_match_with_id(driver: BaseDriver) -> None:
    replace.test_replace_match_with_id(driver)


def test_replace_match_fewer_fields(driver: BaseDriver) -> None:
    replace.test_replace_match_fewer_fields(driver)


def test_replace_custom_id_simple(driver: BaseDriver) -> None:
    replace.test_replace_custom_id_simple(driver)


def test_replace_custom_id_complex(driver: BaseDriver) -> None:
    replace.test_replace_custom_id_complex(driver)


def test_replace_no_match_custom_id(driver: BaseDriver) -> None:
    replace.test_replace_no_match_custom_id(driver)


def test_update_match_id(driver: BaseDriver) -> None:
    update.test_update_match_id(driver)


def test_update_match_many(driver: BaseDriver) -> None:
    update.test_update_match_many(driver)


def test_update_no_match(driver: BaseDriver) -> None:
    update.test_update_no_match(driver)


def test_update_few_fields(driver: BaseDriver) -> None:
    update.test_update_few_fields(driver)


def test_update_new_fields(driver: BaseDriver) -> None:
    update.test_update_new_fields(driver)


def test_update_custom_id_simple(driver: BaseDriver) -> None:
    update.test_update_custom_id_simple(driver)


def test_update_custom_id_complex(driver: BaseDriver) -> None:
    update.test_update_custom_id_complex(driver)


def test_update_no_match_custom_id_simple(driver: BaseDriver) -> None:
    update.test_update_no_match_custom_id_simple(driver)


def test_update_no_match_custom_id_complex(driver: BaseDriver) -> None:
    update.test_update_no_match_custom_id_complex(driver)


def test_collection_separation(driver: BaseDriver) -> None:
    misc.test_collection_separation(driver)


def test_data_type_datetime(driver: BaseDriver) -> None:
    misc.test_data_type_datetime(driver)


def test_data_type_list(driver: BaseDriver) -> None:
    misc.test_data_type_list(driver)


def test_data_type_dict(driver: BaseDriver) -> None:
    misc.test_data_type_dict(driver)


def test_data_type_complex(driver: BaseDriver) -> None:
    misc.test_data_type_complex(driver)
