# -*- coding: utf-8 -*-

"""
excel parser interfaces
"""

import importlib
import re
from abc import abstractmethod
from collections.abc import Iterable, Mapping
from datetime import datetime
from pprint import PrettyPrinter
from typing import Dict, Optional
from uuid import uuid4

import pandas as pd
from peewee import (
    AutoField,
    CharField,
    DatabaseProxy,
    DateTimeField,
    IntegerField,
    Model,
    PostgresqlDatabase,
    SqliteDatabase,
    fn,
)

from .core import html_to_serialized_data

DATABASE = DatabaseProxy()


class ExcelParse(Model):
    """
    excel parse model
    """

    id = AutoField()
    row = IntegerField()
    column = IntegerField()
    value = CharField()
    type = CharField()
    c_header = CharField(index=True)
    r_header = CharField(index=True)
    excel_RC = CharField(index=True)
    name = CharField(index=True)
    sheet = CharField(index=True)
    f_name = CharField(index=True)
    timestamp = DateTimeField(default=datetime.utcnow)

    @classmethod
    def get_queryset(cls, *args, **kwargs):
        """
        return queryset with filters applied
        """

        query = cls.filter(**kwargs)
        return pd.DataFrame(query.dicts())

    @classmethod
    def get_column(cls, column, *args, **kwargs):
        """
        return distinct values from column with aggregations
        """

        query = (
            cls.filter(**kwargs)
            .select(
                getattr(cls, column),
                fn.COUNT(cls.id).alias("Total Rows"),
                fn.COUNT(cls.type.distinct()).alias("Data Types"),
                fn.COUNT(cls.value.distinct()).alias("Distinct Values"),
            )
            .group_by(getattr(cls, column))
        )
        return pd.DataFrame(query.dicts())

    class Meta:
        database = DATABASE
        indexes = ((("f_name", "sheet", "name"), False),)


class BaseInterface:
    """
    base interface class
    """

    endpoint = ""
    user = ""
    password = ""
    host = ""
    port = 0
    name = ""

    Database = None
    Model = None

    def __init__(self, uri: str, Model: Optional[Model] = None):
        for k, v in self.parse_uri(uri).items():
            setattr(self, k, v)
        self.Model = Model

    @abstractmethod
    def input(self):
        """
        from_X override with input handler
        """

        pass

    @abstractmethod
    def output(self, data: pd.DataFrame, obj: Dict) -> pd.DataFrame:
        """
        to_X override with output handler
        """

        pass

    @abstractmethod
    def migrate(self, migration: str):
        """
        override with migration handler
        """

        pass

    @classmethod
    def parse_uri(self, uri: str) -> Dict:
        """
        parse eparse URI string
        """

        patt = r"^(?P<endpoint>.*)://(?P<user>.*?)(:(?P<password>.*?))?(@(?P<host>.*?)(:(?P<port>.*?))?)?/(?P<name>.*)?$"  # noqa
        return re.match(patt, uri).groupdict()


class NullInterface(BaseInterface):
    """
    null interface
    """

    def input(self):
        return pd.DataFrame()

    def output(self, *args, **kwargs):
        pass

    def migrate(self, *args, **kwargs):
        pass


class StdoutInterface(BaseInterface):
    """
    stdout interface
    """

    def input(self):
        return pd.DataFrame()

    def output(self, data, *args, **kwargs):
        PrettyPrinter().pprint(data)

    def migrate(self, *args, **kwargs):
        pass


class BaseDatabaseInterface(BaseInterface):
    """
    base database interface
    """

    @abstractmethod
    def initialize(self, *args, **kwargs):
        """
        override with db-specific initialization
        """

        pass

    def input(self, method, **kwargs):
        m = getattr(self.Model, method, None)

        # if no explicit method is available, try get_column
        if m is None:
            m = self.Model.get_column
            patt = r"^(?:get_)?(?P<column>.*)$"
            kwargs["column"] = re.match(patt, method).group("column")

        self.initialize(DATABASE)
        DATABASE.connect()

        return m(**kwargs)

    def output(self, data, *args, **kwargs):
        # skip empty data
        if hasattr(data, "empty") and data.empty:
            return
        elif not hasattr(data, "empty") and not data:
            return

        # check that data is serialized
        try:
            assert isinstance(data, Iterable)
            assert isinstance(data[0], Mapping)
        except Exception:
            raise ValueError("bad data - did you serialize it first?")

        self.initialize(DATABASE)
        DATABASE.connect()
        DATABASE.create_tables([self.Model])

        # insert data into Model
        with DATABASE.atomic():
            self.Model.insert_many(data).execute()

        # DATABASE.close()

    def migrate(self, migration):
        try:
            m = importlib.import_module("eparse.migrations")
            migration_fcn = getattr(m, migration)
        except AttributeError:
            msg = f"migration error - there is no {migration}"
            raise AttributeError(msg)

        self.initialize(DATABASE)
        DATABASE.connect()
        migration_fcn(self.Model)


class Sqlite3Interface(BaseDatabaseInterface):
    """
    sqlite3 interface
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if not self.name:
            self.name = f".files/{uuid4()}.db"

    def initialize(self, db):
        db.initialize(SqliteDatabase(self.name))


class PostgresInterface(BaseDatabaseInterface):
    """
    postgres interface
    """

    def initialize(self, db):
        db.initialize(
            PostgresqlDatabase(
                self.name,
                user=self.user,
                password=self.password,
                host=self.host,
                port=self.port,
            )
        )


class HtmlInterface(Sqlite3Interface):
    """
    html data interface using sqlite3
    """

    def __init__(self, *args, html: Optional[str] = None, **kwargs):
        super().__init__(*args, **kwargs)

        if html is not None:
            self.output(html_to_serialized_data(html))


def i_factory(uri, Model=None, **kwargs):
    """
    return interface object based on uri
    """

    if uri.startswith("null"):
        return NullInterface(uri, **kwargs)
    elif uri.startswith("stdout"):
        return StdoutInterface(uri, **kwargs)
    elif uri.startswith("sqlite3"):
        return Sqlite3Interface(uri, Model, **kwargs)
    elif uri.startswith("postgres"):
        return PostgresInterface(uri, Model, **kwargs)
    elif uri.startswith("html"):
        _uri = uri.replace("html", "sqlite3")
        return HtmlInterface(_uri, Model, **kwargs)

    raise ValueError(f"{uri} is not a recognized endpoint")
