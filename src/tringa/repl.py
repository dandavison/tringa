import os
import shutil
from enum import StrEnum
from typing import NoReturn

import IPython

from tringa.db import DB
from tringa.msg import fatal


class Repl(StrEnum):
    SQL = "sql"
    PYTHON = "python"


def repl(db: DB, repl: Repl) -> NoReturn:
    match repl:
        case Repl.SQL:
            sql(db)
        case Repl.PYTHON:
            python(db)


def sql(db: DB) -> NoReturn:
    db.connection.close()
    try:
        os.execvp("duckdb", ["duckdb", str(db.path)])
    except FileNotFoundError as err:
        if not shutil.which("duckdb"):
            fatal(
                "Install the duckdb CLI to use the duckdb SQL REPL: https://duckdb.org/docs/installation/.",
                "Alternatively, use --repl python.",
            )
        else:
            raise err


def python(db: DB) -> NoReturn:
    sql = db.connection.sql
    schema = sql(
        "select column_name, data_type from information_schema.columns where table_name = 'test'"
    )
    print(schema)
    n_rows = sql("select count(*) from test").fetchone()
    print("#rows: ", n_rows[0] if n_rows else "?")
    print("Example queries:\n")
    example_queries = [
        'sql("select name from test where passed = false and skipped = false")',
        'sql("select name, time from test order by time desc limit 10")',
    ]
    for q in example_queries:
        print(q)
    print("https://duckdb.org/docs/api/python/dbapi.html")
    IPython.start_ipython(argv=[], user_ns={"conn": db.connection, "sql": sql})
    assert False
