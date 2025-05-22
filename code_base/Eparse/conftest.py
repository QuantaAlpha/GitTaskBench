# -*- coding: utf-8 -*-

"""
unit test fixtures
"""

import pandas as pd
import pytest
from peewee import SqliteDatabase

from eparse.interfaces import DATABASE, ExcelParse


@pytest.fixture
def ctx():
    """
    click style ctx object fixture
    """

    class Obj:
        obj = {}

    return Obj()


@pytest.fixture
def data():
    """
    serialized data fixture
    """

    return dict(
        row=0,
        column=0,
        value="test",
        type="test",
        c_header="test",
        r_header="test",
        excel_RC="A1",
        name="test",
        sheet="test",
        f_name="test",
    )


@pytest.fixture
def sqlite3_db(data):
    """
    sqlite3 in-memory database fixture
    """

    db = ":memory:"
    DATABASE.initialize(SqliteDatabase(db))
    DATABASE.connect()
    DATABASE.create_tables([ExcelParse])

    ExcelParse.create(**data)

    return DATABASE.obj


@pytest.fixture
def xlsx():
    """
    excel file fixture
    """

    return pd.read_excel(
        "tests/eparse_unit_test_data.xlsx",
        header=None,
        index_col=None,
    )
