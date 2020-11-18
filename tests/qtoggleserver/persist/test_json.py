
import pathlib

from typing import Callable

import pytest

from qtoggleserver.drivers.persist import json
from qtoggleserver.persist import BaseDriver

from . import query


@pytest.fixture
def make_driver(tmp_path: pathlib.Path) -> Callable[..., BaseDriver]:
    def driver(pretty_format: bool = True, use_backup: bool = True) -> BaseDriver:
        f = tmp_path / 'dummy.json'
        return json.JSONDriver(str(f), pretty_format=pretty_format, use_backup=use_backup)

    return driver


@pytest.fixture
def driver(make_driver: Callable[..., BaseDriver]) -> BaseDriver:
    return make_driver()


def test_query_full(driver: BaseDriver) -> None:
    query.test_query_full(driver)


def test_query_filter_id(driver: BaseDriver) -> None:
    query.test_query_filter_id(driver)


def test_query_filter_simple(driver: BaseDriver) -> None:
    query.test_query_filter_simple(driver)


def test_query_filter_ge_lt(driver: BaseDriver) -> None:
    query.test_query_filter_ge_lt(driver)


def test_query_filter_gt_le(driver: BaseDriver) -> None:
    query.test_query_filter_gt_le(driver)


def test_query_filter_in(driver: BaseDriver) -> None:
    query.test_query_filter_in(driver)


def test_query_sort_simple(driver: BaseDriver) -> None:
    query.test_query_sort_simple(driver)


def test_query_sort_desc(driver: BaseDriver) -> None:
    query.test_query_sort_desc(driver)


def test_query_sort_composite(driver: BaseDriver) -> None:
    query.test_query_sort_composite(driver)


def test_query_limit(driver: BaseDriver) -> None:
    query.test_query_limit(driver)


def test_query_fields(driver: BaseDriver) -> None:
    query.test_query_fields(driver)


def test_query_filter_limit(driver: BaseDriver) -> None:
    query.test_query_filter_limit(driver)


def test_query_inexistent_field(driver: BaseDriver) -> None:
    query.test_query_inexistent_field(driver)
