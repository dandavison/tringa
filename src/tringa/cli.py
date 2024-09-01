import asyncio
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import typer

import tringa.repl
from tringa import gh
from tringa.artifact import fetch_and_load_new_artifacts
from tringa.db import DBConfig, DBType

app = typer.Typer()


@dataclass
class GlobalOptions:
    db_config: DBConfig


_global_options: GlobalOptions


@app.callback()
def global_options(
    db_path: Optional[Path] = None,
    db_type: DBType = DBType.DUCKDB,
):
    """
    Common options for all commands
    """
    global _global_options
    _global_options = GlobalOptions(db_config=DBConfig(db_type=db_type, path=db_path))


@app.command()
def repl(
    repos: list[str],
    branch: Optional[str] = None,
    artifact_name_globs: Optional[list[str]] = None,
    repl: tringa.repl.Repl = tringa.repl.Repl.PYTHON,
):
    with _global_options.db_config.connect() as db:
        fetch_and_load_new_artifacts(db, repos, branch, artifact_name_globs)
        tringa.repl.repl(db, repl)


@app.command()
def pr(
    pr_identifier: Optional[str] = None,
    artifact_name_globs: Optional[list[str]] = None,
    repl: Optional[tringa.repl.Repl] = None,
):
    pr = asyncio.run(gh.pr(pr_identifier))
    with _global_options.db_config.connect() as db:
        fetch_and_load_new_artifacts(db, [pr.repo], pr.branch, artifact_name_globs)
        if repl:
            tringa.repl.repl(db, repl)
        else:
            nrows = db.connection.execute("select count(*) from test").fetchone()[0]
            print(f"{nrows} rows")


warnings.filterwarnings(
    "ignore",
    message="Attempting to work in a virtualenv. If you encounter problems, please install IPython inside the virtualenv.",
)


def main():
    app()
