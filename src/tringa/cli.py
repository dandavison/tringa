import asyncio
from fnmatch import fnmatch
from itertools import chain
from pathlib import Path
from typing import Optional

import duckdb
import IPython
import typer
from xdg_base_dirs import xdg_data_home

from tringa.db import create_schema, load_xml_from_zip_file_artifacts
from tringa.github import Artifact, download_junit_artifacts, fetch_artifacts
from tringa.log import info


def repl(
    repos: list[str],
    branch: Optional[str] = None,
    artifact_name_globs: list[str] = ["*"],
):
    db = get_db()
    info(f"Using database: {db}")
    with duckdb.connect(str(db)) as conn:
        artifacts = download_junit_artifacts(
            get_artifacts_to_download(
                conn, list_artifacts(repos, branch, artifact_name_globs)
            )
        )
        load_xml_from_zip_file_artifacts(conn, artifacts)
        sql = conn.sql
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
        IPython.start_ipython(argv=[], user_ns={"conn": conn, "sql": sql})


def get_db() -> Path:
    dir = Path(xdg_data_home()) / "tringa"
    dir.mkdir(parents=True, exist_ok=True)
    path = dir / "tringa.duckdb"
    if not path.exists():
        with duckdb.connect(str(path)) as conn:
            create_schema(conn)
    return path


def get_artifacts_to_download(
    conn: duckdb.DuckDBPyConnection,
    available_artifacts: list[Artifact],
) -> list[Artifact]:
    # TODO: Avoid repreatedly downloading artifacts that do not contribute tests
    existing_artifacts = set(
        s for (s,) in conn.execute("SELECT DISTINCT artifact_name FROM test").fetchall()
    )
    return [a for a in available_artifacts if a["name"] not in existing_artifacts]


def list_artifacts(
    repos: list[str],
    branch: Optional[str],
    artifact_name_globs: list[str],
) -> list[Artifact]:
    def include(artifact: Artifact) -> bool:
        if not any(fnmatch(artifact["name"], g) for g in artifact_name_globs):
            return False
        if branch is not None and artifact["branch"] != branch:
            return False
        return True

    async def _list_artifacts():
        return list(
            filter(
                include,
                chain.from_iterable(await asyncio.gather(*map(fetch_artifacts, repos))),
            )
        )

    return asyncio.run(_list_artifacts())


app = typer.Typer()


@app.command()
def tringa(
    repos: list[str],
    branch: Optional[str] = None,
    artifact_name_globs: list[str] = ["*"],
):
    repl(repos, branch, artifact_name_globs)


def main():
    app()
