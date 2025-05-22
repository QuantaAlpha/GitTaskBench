# -*- coding: utf-8 -*-

"""
excel parser database migrations
"""

from playhouse.migrate import SchemaMigrator, migrate


def migration_000102_000200(model):
    """
    database migration from 0.1.2 to 0.2.0
    """

    database = model._meta.database.obj
    timestamp_field = model.timestamp

    migrator = SchemaMigrator.from_database(database)

    with database.atomic():
        migrate(
            # table column_name new_field
            migrator.add_column(
                "excelparse",
                "timestamp",
                timestamp_field,
            ),
            # table column_name(s) unique
            migrator.add_index(
                "excelparse",
                ("c_header",),
                False,
            ),
            migrator.add_index(
                "excelparse",
                ("r_header",),
                False,
            ),
            migrator.add_index(
                "excelparse",
                ("excel_RC",),
                False,
            ),
            migrator.add_index(
                "excelparse",
                ("name",),
                False,
            ),
            migrator.add_index(
                "excelparse",
                ("sheet",),
                False,
            ),
            migrator.add_index(
                "excelparse",
                ("f_name",),
                False,
            ),
            migrator.add_index(
                "excelparse",
                ("f_name", "sheet", "name"),
                False,
            ),
        )
