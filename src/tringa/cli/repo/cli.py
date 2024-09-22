import asyncio
from typing import Annotated, NoReturn, Optional

import typer
from attr import dataclass

import tringa.cli.run.cli
import tringa.repl
import tringa.tui.tui
from tringa import cli, gh, scoped_db
from tringa.annotations import flaky as flaky
from tringa.cli import print, print_json
from tringa.cli.repo.summary import RepoSummary
from tringa.db import DB
from tringa.models import Repo
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
    if repo is None:
        repo = get_current_repo().nameWithOwner
    with scoped_db.connect(cli.options.db_config, repo=repo) as db:
        tringa.repl.repl(db, repl)


@app.command()
def show(
    repo: RepoOption = None,
) -> None:
    """View a summary of tests in this repository."""
    if repo is None:
        repo = get_current_repo().nameWithOwner
    with scoped_db.connect(cli.options.db_config, repo=repo) as db:
        result = _make_repo_result(db, repo)
        if cli.options.json:
            print_json(data=result.to_dict(), sort_keys=True)
        print(result)


@app.command()
def sql(
    query: Annotated[
        str,
        typer.Argument(help="SQL to execute."),
    ],
    repo: RepoOption = None,
) -> None:
    """Execute a SQL query against tests in this repository."""
    if repo is None:
        repo = get_current_repo().nameWithOwner
    with scoped_db.connect(cli.options.db_config, repo=repo) as db:
        rel = db.connection.sql(query)
        if cli.options.json:
            print(rel.df().to_json(orient="records", indent=2))
        else:
            print(rel)


def get_current_repo() -> Repo:
    # TODO: do without a network call; e.g. use `git remote`.
    return asyncio.run(gh.repo())


def _make_repo_result(db: DB, repo: str) -> RepoSummary:
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


@dataclass
class FlakyTest:
    name: str
    introduced_in: str
