# -*- coding: utf-8 -*-

"""
unit tests for eparse interfaces
"""

import pandas as pd
from peewee import SqliteDatabase

from eparse.interfaces import (
    DATABASE,
    BaseInterface,
    ExcelParse,
    HtmlInterface,
    NullInterface,
    Sqlite3Interface,
    StdoutInterface,
    i_factory,
)


def test_sqlite3_db(sqlite3_db):
    assert isinstance(sqlite3_db, SqliteDatabase)
    assert DATABASE.table_exists("excelparse")
    assert len(ExcelParse.select()) == 1


def test_ExcelParse_model(sqlite3_db):
    assert ExcelParse.get_queryset().shape == (1, 12)
    assert ExcelParse.get_column("c_header").shape == (1, 4)


def test_null_interface():
    obj = i_factory("null:///")
    assert isinstance(obj, NullInterface)
    assert obj.input().empty
    assert obj.output(True) is None


def test_stdout_interface():
    obj = i_factory("stdout:///")
    assert isinstance(obj, StdoutInterface)
    assert obj.input().empty
    assert obj.output({"foo": 1}) is None


def test_sqlite3_interface(data, ctx):
    obj = i_factory("sqlite3:///:memory:", ExcelParse)
    obj.output([], ctx)
    obj.output([data], ctx)
    assert isinstance(obj, Sqlite3Interface)
    assert DATABASE.table_exists("excelparse")
    assert len(ExcelParse.select()) == 1


def test_html_interface(data, ctx):
    pd.DataFrame.from_records([data]).to_html()
    obj = i_factory("html:///:memory:", ExcelParse)
    obj.output([], ctx)
    obj.output([data], ctx)
    assert isinstance(obj, HtmlInterface)
    assert isinstance(obj, Sqlite3Interface)
    assert DATABASE.table_exists("excelparse")
    assert len(ExcelParse.select()) == 1


def test_parse_uri():
    db = "endpoint://user:password@host:port/name"
    p = BaseInterface.parse_uri(db)
    keys = ("endpoint", "user", "password", "host", "port", "name")
    not_keys = ()
    assert all([k in p.keys() for k in (keys + not_keys)])
    assert all([k in p.values() for k in keys])
    assert all([k not in p.values() for k in not_keys])
    db = "endpoint://user@host/name"
    p = BaseInterface.parse_uri(db)
    keys = ("endpoint", "user", "host", "name")
    not_keys = ("password", "port")
    assert all([k in p.keys() for k in (keys + not_keys)])
    assert all([k in p.values() for k in keys])
    assert all([k not in p.values() for k in not_keys])
    db = "endpoint:///name"
    p = BaseInterface.parse_uri(db)
    keys = ("endpoint", "name")
    not_keys = ("user", "password", "host", "port")
    assert all([k in p.keys() for k in (keys + not_keys)])
    assert all([k in p.values() for k in keys])
    assert all([k not in p.values() for k in not_keys])
    db = "endpoint:///"
    p = BaseInterface.parse_uri(db)
    keys = ("endpoint",)
    not_keys = ("user", "password", "host", "port", "name")
    assert all([k in p.keys() for k in (keys + not_keys)])
    assert all([k in p.values() for k in keys])
    assert all([k not in p.values() for k in not_keys])
