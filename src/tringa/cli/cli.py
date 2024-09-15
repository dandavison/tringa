import asyncio
import warnings
from typing import Optional

import duckdb
import typer

import tringa.repl
from tringa import cli, gh
from tringa.artifact import fetch_and_load_new_artifacts
from tringa.cli import pr
from tringa.exceptions import TringaException
from tringa.msg import error, info
from tringa.utils import tee as tee

app = typer.Typer(rich_markup_mode="rich")

app.callback()(cli.set_options)


@app.command()
def repl(
    repos: list[str] = [],
    branch: Optional[str] = None,
    repl: tringa.repl.Repl = tringa.repl.Repl.PYTHON,
):
    """
    Start a REPL to query the database.
    """
    if not repos:
        repos = [asyncio.run(gh.repo()).nameWithOwner]
    cli.validate_repl(repl)
    with cli.options.db_config.connect() as db:
        fetch_and_load_new_artifacts(db, repos, branch)
        tringa.repl.repl(db, repl)


app.command()(pr.pr)


@app.command()
def dropdb():
    """
    Delete the database.
    """
    if cli.options.db_config.path:
        cli.options.db_config.path.unlink()
        info("Deleted database at", cli.options.db_config.path)


@app.command()
def sql(
    query: str,
    repos: list[str] = [],
    json: bool = False,
):
    """
    Execute a SQL query against the database.
    """
    if not repos:
        repo = asyncio.run(gh.repo()).nameWithOwner
        repos = [repo]
        query = query.format(repo=repo)
    with cli.options.db_config.connect() as db:
        fetch_and_load_new_artifacts(db, repos)
        if json:
            db.exec_to_json(query)
        else:
            db.exec_to_string(query)


warnings.filterwarnings(
    "ignore",
    message="Attempting to work in a virtualenv. If you encounter problems, please install IPython inside the virtualenv.",
)


def main():
    try:
        app()
    except TringaException as e:
        error(e)
        exit(1)
    except duckdb.IOException as e:
        error(
            f"{e}\n\nIt looks like you left a tringa REPL open? Connecting to the DB from multiple processes is not supported currently."
        )
        exit(1)
