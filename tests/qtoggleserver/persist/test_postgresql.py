import asyncpg
import pytest
import testing.postgresql

from qtoggleserver.drivers.persist import postgresql
from qtoggleserver.persist import BaseDriver

from . import insert, misc, query, remove, replace, update


TestingPostgreSQL = testing.postgresql.PostgresqlFactory(cache_initialized_db=True)

pg_server = None


@pytest.fixture
async def driver() -> BaseDriver:
    global pg_server

    if pg_server is None:
        pg_server = TestingPostgreSQL()

    params = pg_server.dsn()
    db = params['database']

    conn = await asyncpg.connect(**dict(params, database='postgres'))
    await conn.execute(f'DROP DATABASE IF EXISTS {db}')
    await conn.execute(f'CREATE DATABASE {db}')
    await conn.close()

    driver = postgresql.PostgreSQLDriver(
        host=params['host'],
        port=params['port'],
        db=params['database'],
        username=params['user'],
        password=params.get('password')
    )
    await driver.init()

    yield driver

    await driver.cleanup()


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
