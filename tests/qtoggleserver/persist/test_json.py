
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


def test_query_specific_id(driver: BaseDriver) -> None:
    query.test_query_specific_id(driver)


def test_query_simple_filter(driver: BaseDriver) -> None:
    query.test_query_simple_filter(driver)


def test_query_fields(driver: BaseDriver) -> None:
    query.test_query_fields(driver)
