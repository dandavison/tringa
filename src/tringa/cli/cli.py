import warnings

import duckdb
import typer

from tringa import cli
from tringa.cli import internals, pr, repo
from tringa.exceptions import TringaException
from tringa.msg import error, info
from tringa.utils import tee as tee

app = typer.Typer(rich_markup_mode="rich")

app.callback()(cli.set_options)

app.add_typer(pr.app, name="pr")
app.add_typer(repo.app, name="repo")
app.add_typer(internals.app, name="internals")


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


@app.command()
def sync(_repo: repo.RepoOption = None):
    """
    Fetch data for the current repository.
    """
    repo.sync(_repo)


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
