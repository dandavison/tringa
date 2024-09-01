import os
import shutil
import sqlite3
from enum import StrEnum

import duckdb
import IPython

from tringa.db import DB
from tringa.log import fatal


class Repl(StrEnum):
    SQL = "sql"
    PYTHON = "python"


def repl(db: DB, repl: Repl):
    match repl:
        case Repl.SQL:
            sql(db)
        case Repl.PYTHON:
            python(db)


def sql(db: DB):
    db.connection.close()
    match db.connection:
        case duckdb.DuckDBPyConnection():
            try:
                os.execvp("duckdb", ["duckdb", str(db.path)])
            except FileNotFoundError as err:
                if not shutil.which("duckdb"):
                    fatal(
                        "Install the duckdb CLI to use the duckdb SQL REPL: https://duckdb.org/docs/installation/.",
                        "Alternatively, use --dbtype sqlite or --repl python.",
                    )
                else:
                    raise err
        case sqlite3.Connection():
            os.execvp("litecli", ["litecli", "--auto-vertical-output", str(db.path)])


def python(db: DB):
    assert isinstance(
        db.connection, duckdb.DuckDBPyConnection
    ), "The Python REPL is supported for duckdb only"
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
