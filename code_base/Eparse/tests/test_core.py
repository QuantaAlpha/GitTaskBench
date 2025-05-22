#!/usr/bin/env python

"""
unit tests for eparse core
"""

import pandas as pd

from eparse.core import (
    df_find_tables,
    df_parse_table,
    df_serialize_table,
    get_df_from_file,
    get_table_digest,
    html_to_df,
    html_to_serialized_data,
)


def test_df_find_tables(xlsx):
    t = df_find_tables(xlsx)
    assert len(t) == 2
    assert (2, 2, "C3", "ID") in t


def test_df_find_tables_loose(xlsx):
    t = df_find_tables(xlsx, loose=True)
    assert len(t) == 10
    assert (2, 2, "C3", "ID") in t
    assert (102, 2, "C103", "Schedule of Principal Repayments:") in t


def test_df_parse_table(xlsx):
    t = df_parse_table(xlsx, 102, 2)
    assert t.shape == (11, 8)
    assert t.iloc[0, 2] == "Date"


def test_df_parse_table_na_tolerance(xlsx):
    t = df_parse_table(xlsx, 2, 2)
    assert t.shape == (9, 2)
    t = df_parse_table(
        xlsx,
        2,
        2,
        na_tolerance_r=2,
        na_tolerance_c=2,
        na_strip=True,
    )
    assert t.shape == (9, 8)


def test_df_serialize_table(xlsx):
    t = df_serialize_table(df_parse_table(xlsx, 102, 2), foo="bar")
    assert len(t) == 11 * 8
    assert isinstance(t[22], dict)
    assert "c_header" in t[22].keys()
    assert t[22]["c_header"] == "Date"


def test_get_df_from_file():
    filename = "tests/eparse_unit_test_data.xlsx"
    df_a, *_ = next(get_df_from_file(filename))
    with open(filename, "rb") as file:
        df_b, *_ = next(get_df_from_file(file))
    assert isinstance(df_a, pd.DataFrame)
    assert isinstance(df_b, pd.DataFrame)
    assert df_a.shape == df_b.shape


def test_get_table_digest(xlsx):
    parse = df_parse_table(xlsx, 26, 1)
    serialized_table = df_serialize_table(parse)
    digest = get_table_digest(serialized_table, table_name="Financials")
    assert isinstance(digest, str)
    assert f"{parse.shape[1]} column(s)" in digest
    assert f"{parse.shape[0]} row(s)" in digest
    assert "Last Price Discovery:  03/01/2022" in digest
    assert "Interest Expense" in digest
    assert "float" in digest


def test_html_to_df_and_serialized_data(xlsx):
    table = df_parse_table(xlsx, 102, 2)
    html = table.to_html(index=False, header=False, na_rep="")
    df = html_to_df(html)[0]
    assert isinstance(df, pd.DataFrame)
    assert df.shape == table.shape
    st = html_to_serialized_data(html)
    assert isinstance(st, list)
    assert isinstance(st[0], dict)
    assert len(st) == 11 * 8
