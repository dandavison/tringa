import asyncio
from typing import Annotated, NoReturn, Optional

import typer

import tringa.cli.run.cli
import tringa.repl
import tringa.tui.tui
from tringa import cli, gh, scoped_db
from tringa.annotations import flaky as flaky
from tringa.cli.output import tringa_print
from tringa.cli.repo.flakes import get_flakes
from tringa.cli.repo.summary import RepoSummary
from tringa.db import DB
from tringa.fetch import fetch_test_data
from tringa.queries import EmptyParams, Query

app = typer.Typer(rich_markup_mode="rich")

RepoOption = Annotated[
    Optional[str],
    typer.Option(
        help=(
            "GitHub repository to target, e.g. `--repo dandavison/tringa`. "
            "Defaults to the current repository."
        ),
    ),
]


def _get_repo(repo: RepoOption) -> str:
    if repo is None:
        # TODO: do without a network call; e.g. use `git remote`.
        repo = asyncio.run(gh.repo())
    fetch_test_data(repo)
    return repo


@app.command()
def flakes(
    repo: RepoOption = None,
) -> None:
    """Show flaky tests in this repository."""
    repo = _get_repo(repo)
    with scoped_db.connect(cli.options.db_config, repo=repo) as db:
        tringa_print(get_flakes(db))


@app.command()
def repl(
    repo: RepoOption = None,
    repl: Annotated[
        Optional[tringa.repl.Repl],
        typer.Option(
            help=(
                "REPL type. "
                "Default is sql if duckdb CLI is installed, otherwise python. "
                "See https://duckdb.org/docs/api/python/overview.html for the duckdb Python API."
            ),
        ),
    ] = None,
) -> NoReturn:
    """
    Start an interactive REPL allowing execution of SQL queries against tests in this repository.
    """
    repo = _get_repo(repo)
    with scoped_db.connect(cli.options.db_config, repo=repo) as db:
        tringa.repl.repl(db, repl)


@app.command()
def show(
    repo: RepoOption = None,
) -> None:
    """View a summary of tests in this repository."""
    repo = _get_repo(repo)
    with scoped_db.connect(cli.options.db_config, repo=repo) as db:
        tringa_print(_make_repo_summary(db, repo))


@app.command()
def sql(
    query: Annotated[
        str,
        typer.Argument(help="SQL to execute."),
    ],
    repo: RepoOption = None,
) -> None:
    """Execute a SQL query against tests in this repository."""
    repo = _get_repo(repo)
    with scoped_db.connect(cli.options.db_config, repo=repo) as db:
        tringa_print(db.connection.sql(query))


def _make_repo_summary(db: DB, repo: str) -> RepoSummary:
    flaky_tests = Query[tuple[str], EmptyParams](
        """
    select distinct name from test
    where flaky = true
    order by file, time desc;
    """
    ).fetchall(db, {})

    return RepoSummary(
        repo=repo,
        flaky_tests=flaky_tests,
    )
