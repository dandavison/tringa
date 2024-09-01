import asyncio
import warnings
from dataclasses import dataclass
from typing import Optional

import typer

import tringa.repl
from tringa import gh
from tringa.artifact import fetch_and_load_new_artifacts
from tringa.db import DBConfig, DBPersistence, DBType

app = typer.Typer()

warnings.filterwarnings(
    "ignore",
    message="Attempting to work in a virtualenv. If you encounter problems, please install IPython inside the virtualenv.",
)


@dataclass
class GlobalOptions:
    db_config: DBConfig


_global_options: GlobalOptions


@app.callback()
def global_options(
    db_persistence: DBPersistence = DBPersistence.EPHEMERAL,
    db_type: DBType = DBType.DUCKDB,
):
    """
    Common options for all commands
    """
    global _global_options
    _global_options = GlobalOptions(db_config=DBConfig(db_persistence, db_type))


@app.command()
def repl(
    repos: list[str],
    branch: Optional[str] = None,
    artifact_name_globs: Optional[list[str]] = None,
):
    with _global_options.db_config.connect() as db:
        fetch_and_load_new_artifacts(db, repos, branch, artifact_name_globs)
        tringa.repl.repl(db)


@app.command()
def pr(
    number: Optional[int] = None,
    artifact_name_globs: Optional[list[str]] = None,
    repl: bool = False,
):
    pr = asyncio.run(gh.pr(number))
    with _global_options.db_config.connect() as db:
        fetch_and_load_new_artifacts(db, [pr.repo], pr.branch, artifact_name_globs)
        if repl:
            tringa.repl.repl(db)
        else:
            nrows = db.connection.execute("select count(*) from test").fetchone()[0]
            print(f"{nrows} rows")


def main():
    app()
