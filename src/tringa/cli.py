import asyncio
import warnings
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


@app.command()
def repl(
    repos: list[str],
    branch: Optional[str] = None,
    artifact_name_globs: Optional[list[str]] = None,
):
    with db.connection() as conn:
        fetch_and_load_new_artifacts(conn, repos, branch, artifact_name_globs)
        tringa.repl.repl(conn)


@app.command()
def pr(
    number: Optional[int] = None,
    artifact_name_globs: Optional[list[str]] = None,
    repl: bool = False,
):
    pr = asyncio.run(gh.pr(number))
    with db.connection() as conn:
        fetch_and_load_new_artifacts(conn, [pr.repo], pr.branch, artifact_name_globs)
        if repl:
            tringa.repl.repl(conn)


def main():
    app()
