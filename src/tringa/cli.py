import asyncio
import warnings
from dataclasses import dataclass
from typing import Optional

import typer

import tringa.repl
from tringa import db, gh
from tringa.artifact import fetch_and_load_new_artifacts

app = typer.Typer()

warnings.filterwarnings(
    "ignore",
    message="Attempting to work in a virtualenv. If you encounter problems, please install IPython inside the virtualenv.",
)


@dataclass
class GlobalOptions:
    db_persistence: db.DBPersistence


global_options: GlobalOptions


@app.callback()
def common_options(
    ctx: typer.Context, db_persistence: db.DBPersistence = db.DBPersistence.EPHEMERAL
):
    """
    Common options for all commands
    """
    global global_options
    global_options = GlobalOptions(db_persistence=db_persistence)


@app.command()
def repl(
    repos: list[str],
    branch: Optional[str] = None,
    artifact_name_globs: Optional[list[str]] = None,
):
    with db.connection(global_options.db_persistence) as conn:
        fetch_and_load_new_artifacts(conn, repos, branch, artifact_name_globs)
        tringa.repl.repl(conn)


@app.command()
def pr(
    number: Optional[int] = None,
    artifact_name_globs: Optional[list[str]] = None,
    repl: bool = False,
):
    pr = asyncio.run(gh.pr(number))
    with db.connection(global_options.db_persistence) as conn:
        fetch_and_load_new_artifacts(conn, [pr.repo], pr.branch, artifact_name_globs)
        if repl:
            tringa.repl.repl(conn)


def main():
    app()
