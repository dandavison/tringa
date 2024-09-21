import warnings
from typing import Optional

import duckdb
import typer

import tringa.repl
from tringa import cli
from tringa.artifact import fetch_and_load_new_artifacts
from tringa.cli import pr, repo
from tringa.exceptions import TringaException
from tringa.msg import error, info
from tringa.utils import tee as tee

app = typer.Typer(rich_markup_mode="rich")

app.callback()(cli.set_options)


@app.command()
def repl(
    repos: list[str] = [],
    branch: Optional[str] = None,
    repl: tringa.repl.Repl = tringa.repl.Repl.SQL,
):
    """
    Start a REPL to query the database.
    """
    if not repos:
        repos = [repo.get_current_repo().nameWithOwner]
    cli.validate_repl(repl)
    with cli.options.db_config.connect() as db:
        fetch_and_load_new_artifacts(db, repos, branch)
        tringa.repl.repl(db, repl)


app.add_typer(pr.app, name="pr")
app.add_typer(repo.app, name="repo")


@app.command()
def dropdb():
    """
    Delete the database.
    """
    path = cli.options.db_config.path
    if not path:
        error("No database path configured")
        exit(1)
    if not path.exists():
        error("Path does not exist:", path)
        exit(1)
    path.unlink()
    info("Deleted database at", path)


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
        error(e)
        exit(1)
