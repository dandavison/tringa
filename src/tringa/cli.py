import sys
import tempfile
from textwrap import dedent
from typing import Optional

import duckdb
import IPython
import typer

from tringa.db import create_schema, load_xml_from_zip_file_artifacts
from tringa.github import download_junit_artifacts


def app(repos: list[str], branch: Optional[str] = None):
    with duckdb.connect(tempfile.mktemp()) as conn:
        try:
            artifacts = download_junit_artifacts(repos, branch)
            create_schema(conn)
            load_xml_from_zip_file_artifacts(conn, artifacts)
        except Exception as err:
            print(f"Error: {err}", file=sys.stderr)
            sys.exit(1)
        else:
            print(
                dedent("""
                See https://duckdb.org/docs/api/python/dbapi.html.

                Use the `sql` function to execute queries against the table named `test`.
                """)
            )
            sql = conn.sql
            schema = sql(
                "select column_name, data_type from information_schema.columns where table_name = 'test'"
            )
            example_queries = [
                'sql("select name from test where passed = false and skipped = false")',
                'sql("select name, time from test order by time desc limit 10")',
            ]
            print(schema)
            print("Examples:\n")
            for c in example_queries:
                print(c)
            IPython.start_ipython(argv=[], user_ns={"conn": conn, "sql": sql})


def main():
    typer.run(app)
