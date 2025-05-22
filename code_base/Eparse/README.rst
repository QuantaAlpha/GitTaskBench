======
eparse
======


.. image:: https://img.shields.io/pypi/v/eparse.svg
        :target: https://pypi.python.org/pypi/eparse

.. image:: https://img.shields.io/badge/License-MIT-blue.svg
        :target: https://opensource.org/licenses/MIT
        :alt: License: MIT


Description
===========
Excel spreadsheet crawler and table parser for data extraction
and querying.


Features
========
* Command-line interface
* Recursive Excel file discovery
* Sub-tabular data extraction (logical tables)
* SQLite and PostgreSQL database interfaces
* CLI query tool
* Summary data metrics


Installation
============
To install eparse, you can use pip and the latest version on PyPI:

.. code-block::

   $ pip install eparse

Or you can clone this repo and install from source, as the latest version
will not always by on PyPI:

.. code-block::

   $ git clone https://github.com/ChrisPappalardo/eparse.git
   $ cd eparse
   $ pip install .

Using eparse in another project?  You can also add either a PyPI version
or the latest source to your ``requirements.txt`` file as follows:

::

   eparse  # latest pypi version
   eparse==0.8.0  # sepcific pypi version
   eparse @ git+https://github.com/ChrisPappalardo/eparse.git  # latest source

If you plan to use the postgres interface, you also need to install
the postgres package ``psycopg2``. Instructions can be found
`here <https://www.psycopg.org/docs/install.html#quick-install>`_.
This package is optional, and you can use the other interfaces
such as the ``SQLite3`` interface without having to install
``psycopg2``.

The easiest way to install the ``psycopg2`` package for your
particular environment may be to install the pre-compiled
binary driver as follows:

.. code-block::

   $ pip install psycopg2-binary

If you see an error while trying to use a postgres endpoint such
as ``postgres://user:pass@host:port/my_db`` that mentions the
postgres driver is missing, then you know you haven't properly
installed (and compiled)  ``psycopg2``.


Usage
=====
eparse can be used as either a python library or from the command-line.
You can view supported CLI commands and usage with ``--help`` as follows:

.. code-block::

    $ eparse --help
    Usage: eparse [OPTIONS] COMMAND [ARGS]...

    excel parser

    Options:
    -i, --input TEXT   input source
    -o, --output TEXT  output destination
    -f, --file TEXT    file(s) or dir(s) to target
    -d, --debug        use debug mode
    -l, --loose        find tables loosely
    -r, --recursive    find files recursively
    -t, --truncate     truncate dataframe output
    -v, --verbose      increase output verbosity
    --help             Show this message and exit.

    Commands:
    migrate  migrate eparse table
    parse    parse table(s) found in sheet for target(s)
    query    query eparse output
    scan     scan for excel files in target

You can also use eparse from python like so:

.. code-block::

    from eparse.core import get_df_from_file

    print([table for table in get_df_from_file('myfile.xlsx')])
    102   Date  Principal Repayment   Date  Principal Repayment
    103  44834        700757.679004  44926        430013.148303
    104  44926         71957.776108  45016        100576.127808
    105  45016         147578.19262  45107        898008.340095
    106  45107         32801.363072  45199         841656.13896
    ...

For example, to find and print cells from any "Principal Repayment" columns in excel files in the "tests" directory, you would:

.. code-block::

    from pathlib import Path
    from eparse.core import get_df_from_file, df_serialize_table

    for f in Path("tests").iterdir():
        if f.is_file() and "xls" in f.name:
            for table in get_df_from_file(f):
                for row in df_serialize_table(table[0]):
                    if row["c_header"] == "Principal Repayment":
                        print(row)


Scan
----
To scan one or more directories for Excel files with descriptive
information, you can use the ``scan`` command like so:

.. code-block::

    $ eparse -v -f <path_to_files> scan

Increase the verbosity with additional flags, such as ``-vvv``, for
more descriptive information about the file(s), including sheet names.


Parse
-----
Excel files can be parsed as follows:

.. code-block::

    $ eparse -v -f <path_to_files> parse

This mode will list each table found in each Excel file to the command-line.
This mode is useful for initial discovery for parseable data.

eparse uses a simple algorithm for identifying tables.  Table "corners"
are identified as cells that contain empty cells above and to the left
(or sheet boundaries).  A densely or sparsely populated 2x2+ table must
follow in order for data to be extracted in relation to that cell.
eparse will automatically adjust for rowspan labels and empty table
corners and the dense vs. sparse criterion can be controlled with
the ``--loose`` flag.  eparse can also tolerate a user-specified number
of NA row and column cells and still consider the table to be unbroken
with the ``--nacount`` arg.

eparse was written to accomodate various types of output formats and
endpoints, including ``null:///``, ``stdout:///``, ``sqlite3:///db_name``,
and ``postgres://user:password@host:port/db_name``.

null
^^^^
This mode is useful for validating files and generating descriptive
info, and is the default.  The command above with `-v` is an example
of this mode, which lists out the tables found.

stdout
^^^^^^
This mode is good for viewing data extracted from Excel files in the
console.  For example, you could view all tables found in `Sheet1`
with the following command:

.. code-block::

    $ eparse -f <path_to_files> -o stdout:/// parse -s "Sheet1"

eparse uses `pandas <https://github.com/pandas-dev/pandas>`_
to handle table data.  You can view larger tables without truncation
using the ``-t`` flag as follows:

.. code-block::

    $ eparse -t -f <path_to_files> -o stdout:/// parse -s "Sheet1"

Data in table format is useful for human viewing, but a serialized
form is better for data interfacing.  Serialize your output with
the ``-z`` flag as follows:

.. code-block::

    $ eparse -t -f <path_to_files> -o stdout:/// parse -z

Each cell of extracted table data is serialized as follows:

* `row` - 0-indexed table row number
* `column` - 0-indexed table column number
* `value` - the value of the cell as a ``str``
* `type` - the implied python ``type`` of the data found
* `c_header` - the column header
* `r_header` - the row header
* `excel_RC` - the RC reference from the spreadsheet (e.g. B10)
* `sheet` - the name of the sheet
* `f_name` - the name of the file

sqlite3
^^^^^^^
eparse uses the `peewee <https://github.com/coleifer/peewee>`_
package for ORM and database integration.  The
`interfaces <eparse/interfaces.py>`_ module contains an
``ExcelParse`` model that provides data persistence and a common
interface.

To create a `SQLite3 <https://github.com/sqlite/sqlite>`_ database
with your parsed Excel data, use the following command:

.. code-block::

    $ mkdir .files
    $ eparse -f <path_to_files> -o sqlite3:/// parse -z

This command will automatically generate a unique database filename
using the ``uuid`` python package in the ``.files/`` sub-directory
of the working directory.  You may need to create this directory
before running this command, as shown.

You can also specify a path and filename of your choosing, like so:

.. code-block::

    $ mkdir .files
    $ eparse -f <path_to_files> -o sqlite3:///path/filename.db parse -z

postgres
^^^^^^^^
eparse also supports `postgresql` integrations. As mentioned above,
you will need ``psycopg2`` installed for `postgresql` integrations
to work. The eparse ``BaseDatabaseInterface`` abstracts the
implementation details, so you would use this interface the same
way you use the others, with the exception of the endpoint.

To use a ``postgresql`` database as the source and/or destination
of your data, you would supply an ``--input`` and/or ``--output``
endpoint to the tool as follows:

.. code-block::

    $ eparse -o postgres://user:password@host:port/db_name ...

Where details like ``user``, ``host``, ``port`` are provided to
you by your db administrator. eparse will create the necessary
table(s) and indexes for you when inserting data into the database.


Query
-----
Once you have stored parsed data, you can begin to query it using the
``peewee`` ORM.  This can be done with the tool or directly with
the database.

For example, query distinct column header names from a generated
``SQLite3`` database as follows:

.. code-block::

    $ eparse -i sqlite3:///.files/<db_file> -o stdout:/// query -m get_c_header
                   c_header  Total Rows  Data Types  Distinct Values
      0             ABC-col         150           2               76
      1             DEF-col        3981           3               15
      2             GHI-col          20           1                2
      ..                ...         ...         ...              ...

This command will give descriptive information of each distinct c_header
found, including total rows, unique data types, and distinct values.

You can also get raw un-truncated data as follows:

.. code-block::

    $ eparse -t -i sqlite3:///.files/<db_file> -o stdout:/// query

Filtering data on content is easy.  Use the ``--filter`` option as
follows:

.. code-block::

    $ eparse -i sqlite3:///.files/<db_file> -o stdout:/// query --filter f_name "somefile.xlsx"

The above command will filter all rows from an Excel file named
`somefile.xlsx`. You can use any of the following ``django``-style
filters:

* ``__eq`` equals X
* ``__lt`` less than X
* ``__lte`` less than or equal to X
* ``__gt`` greater than X
* ``__gte`` greater than or equal to X
* ``__ne`` not equal to X
* ``__in`` X is in
* ``__is`` is X
* ``__like`` like expression, such as ``%somestr%``, case sensitive
* ``__ilike`` like expression, such as ``%somestr%``, case insensitive
* ``__regexp`` regular expression matching such as ``^.*?foo.*?$``

Filters are applied to the ORM fields like so:

* ``--filter row__gte 4`` all extracted table rows `>= 5`
* ``--filter f_name__ilike "%foo%"`` all data from filenames with `foo`
* ``--filter value__ne 100`` all data with values other than `100`

Queried data can even be stored into a new database for creating
curated data subsets, as follows:

.. code-block::

    $ eparse -i sqlite3:///.files/<db_file> \
             -o sqlite3:///.files/<subq_db_file> \
             query --filter f_name "somefile.xlsx"

Since database files the tool generates when using `sqlite3:///` are
``SQLite`` native, you can also use `SQLite` database client tools
and execute raw SQL like so:

.. code-block::

    $ sudo apt-get install -y sqlite3-tools
    $ sqlite3 .files/<db_file>
    SQLite version 3.37.2 2022-01-06 13:25:41
    Enter ".help" for usage hints.
    sqlite> .schema
    CREATE TABLE IF NOT EXISTS "excelparse" ("id" INTEGER NOT NULL PRIMARY KEY, "row" INTEGER NOT NULL, "column" INTEGER NOT NULL, "value" VARCHAR(255) NOT NULL, "type" VARCHAR(255) NOT NULL, "c_header" VARCHAR(255) NOT NULL, "r_header" VARCHAR(255) NOT NULL, "excel_RC" VARCHAR(255) NOT NULL, "name" VARCHAR(255) NOT NULL, "sheet" VARCHAR(255) NOT NULL, "f_name" VARCHAR(255) NOT NULL);
    sqlite> .header on
    sqlite> SELECT * FROM excelparse LIMIT 1;
    id|row|column|value|type|c_header|r_header|excel_RC|name|sheet|f_name
    1|0|0|ABC|<class 'str'>|SomeCol|SomeRow|B2|MyTable|Sheet1|myfile.xlsm


Migrate
-------
eparse wouldn't be a solid tool without the ability to migrate your
eparse databases for future code changes.  You can apply migrations
that ship with future versions of eparse as follows:

.. code-block::

    $ eparse -i sqlite3:///.files/<db_file> migrate -m <migration>
    applied <migration>

It is up to you to determine the migrations you need based on the
eparse version you are upgrading from and to. Migrations can be
found in `eparse/migrations.py <eparse/migrations.py>`_


Unstructured
============
If you would like to use eparse to partition xls[x] files alongside unstructured, you can do so with our contributed `partition` and `partition_xlsx` modules. Simply import the `partition` function from `eparse.contrib.unstructured.partition` and use it instead of `partition` from `unstructured.partition.auto` like so:

.. code-block::

    from eparse.contrib.unstructured.partition import partition

    elements = partition(filename='some_file.xlsx', eparse_mode='...')

Valid `eparse_mode` settings are available in `eparse.contrib.unstructured.xlsx._eparse_modes`.


Development
===========
Clone the repo:

.. code-block::

    $ git clone https://github.com/ChrisPappalardo/eparse.git

Install devtest requirements and the package in editable mode:

.. code-block::

    $ pip install -r requirements.txt
    $ pip install -e .

Run unit tests:

.. code-block::

    $ make test

Run the linter:

.. code-block::

    $ make lint

Install pre-commit:

.. code-block::

    $ pre-commit install

Run pre-commit:

.. code-block::

    $ pre-commit run --all-files

Contributing
============
As an open-source project, contributions are always welcome. Please see `Contributing <CONTRIBUTING.rst>`_ for more information.


License
=======
eparse is licensed under the `MIT License <https://opensource.org/licenses/MIT>`_. See the `LICENSE <LICENSE>`_ file for more details.


Contact
=======
Thanks for your support of eparse. Feel free to contact me at `cpappala@gmail.com <mailto:cpappala@gmail.com>`_ or connect with me on `Github <https://www.linkedin.com/in/chris-a-pappalardo/>`_.
