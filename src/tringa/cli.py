import sys
import tempfile
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
            IPython.start_ipython(argv=[], user_ns={"conn": conn, "sql": conn.sql})


def main():
    typer.run(app)
