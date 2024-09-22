import asyncio
from typing import Annotated, NoReturn, Optional

import typer

import tringa.cli.run
import tringa.repl
import tringa.tui.tui
from tringa import cli, gh, queries, scoped_db
from tringa.annotations import flaky as flaky
from tringa.db import DB
from tringa.models import Repo, RepoResult
from tringa.rich import print, print_json

app = typer.Typer(rich_markup_mode="rich")


@app.command()
def repl(
    repo: Annotated[
        Optional[str],
        typer.Option(
            help=(
                "Repository for which tests will be loaded into the DB, e.g. `--repo dandavison/tringa`. "
                "Defaults to the current repository."
            ),
        ),
    ] = None,
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
    repo: Annotated[
        Optional[str],
        typer.Option(
            help=(
                "Repository to show, e.g. `--repo dandavison/tringa`. "
                "Defaults to the current repository."
            ),
        ),
    ] = None,
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
    repo: Annotated[
        Optional[str],
        typer.Option(
            help=(
                "Repository to execute the query against, e.g. `--repo dandavison/tringa`. "
                "Defaults to the current repository."
            ),
        ),
    ] = None,
):
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


def _make_repo_result(db: DB, repo: str) -> RepoResult:
    return RepoResult(
        repo=repo,
        failed_tests=queries.failed_tests(db),
    )
