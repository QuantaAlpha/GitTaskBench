# -*- coding: utf-8 -*-

"""
unit tests for eparse cli
"""

import pytest
from click.testing import CliRunner

from eparse.cli import main

kwargs = {"obj": {}, "catch_exceptions": False}


def test_main():
    runner = CliRunner()
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "Usage" in result.output


def test_scan():
    runner = CliRunner()
    result = runner.invoke(main, ["-f", "tests/", "scan"], **kwargs)
    assert result.exit_code == 0
    assert "eparse_unit_test_data" in result.output


def test_parse():
    runner = CliRunner()
    result = runner.invoke(main, ["-f", "tests/", "parse"], **kwargs)
    assert result.exit_code == 0
    assert "eparse_unit_test_data" in result.output


def test_query():
    runner = CliRunner()
    result = runner.invoke(main, ["-i", "sqlite3:///tests/test.db", "query"], **kwargs)
    assert result.exit_code == 0
    assert result.output == ""


def test_migrate():
    runner = CliRunner()
    result = runner.invoke(
        main,
        ["-i", "sqlite3:///tests/test.db", "migrate", "-m", "migration_000102_000200"],
        **kwargs,
    )
    assert result.exit_code == 1
    assert "duplicate column name: timestamp" in result.output


def test_outputs():
    runner = CliRunner()
    result = runner.invoke(main, ["-o", "null:///", "scan"], **kwargs)
    assert result.exit_code == 0
    assert result.output == ""
    result = runner.invoke(main, ["-o", "stdout:///", "scan"], **kwargs)
    assert result.exit_code == 0
    assert result.output == ""
    result = runner.invoke(main, ["-o", "sqlite3:///:memory:", "scan"], **kwargs)
    assert result.exit_code == 0
    assert result.output == ""
    result = runner.invoke(main, ["-o", "test", "scan"], **kwargs)
    assert result.exit_code == 1
    assert "test is not a recognized endpoint" in result.output
    with pytest.raises(ValueError):
        result = runner.invoke(main, ["-d", "-o", "test", "scan"], **kwargs)
