import asyncio
import re
from typing import Annotated, NoReturn, Optional

import typer

import tringa.repl
import tringa.tui.tui
from tringa import cli, gh, scoped_db
from tringa.annotations import flaky as flaky
from tringa.cli.output import tringa_print
from tringa.cli.repo import show
from tringa.cli.reports import flaky_tests
from tringa.fetch import fetch_test_data
from tringa.utils import execute  # Import the execute function

app = typer.Typer(rich_markup_mode="rich")

RepoOption = Annotated[
    Optional[str],
    typer.Argument(
        help=(
            "GitHub repository to target, e.g. `dandavison/tringa`. "
            "Defaults to the current repository."
        ),
    ),
]


@app.command("flakes")
def _flakes(
    repo: RepoOption = None,
) -> None:
    """Show flaky tests in this repository."""
    repo = _get_repo(repo)
    with scoped_db.connect(cli.options.db_config, repo=repo) as db:
        tringa_print(flaky_tests.make_report(db))


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


@app.command("show")
def _show(
    repo: RepoOption = None,
) -> None:
    """View a summary of tests in this repository."""
    repo = _get_repo(repo)
    with scoped_db.connect(cli.options.db_config, repo=repo) as db:
        tringa_print(show.make_report(db, repo))


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


def _get_repo(repo: RepoOption) -> str:
    repo = _validate_repo_arg(repo) if repo else _infer_repo()
    # TODO: this isn't the right place for this
    fetch_test_data(repo)
    return repo


def _infer_repo() -> str:
    return _infer_repo_from_local_git_repo() or asyncio.run(gh.repo())


def _infer_repo_from_local_git_repo() -> Optional[str]:
    try:
        url = asyncio.run(execute(["git", "remote", "get-url", "origin"]))
        return _validate_repo_arg(url.decode().strip())
    except Exception:
        return None


def _validate_repo_arg(repo: str) -> str:
    _repo = r"([^/.]+/[^/.]+)"
    repo = repo.strip()
    # import pdb

    # pdb.set_trace()
    for regex in [
        rf"^{_repo}$",
        rf"^https://github\.com/{_repo}$",
        rf"^https://github\.com/{_repo}/",
        rf"^git@github\.com:{_repo}(\.git)?$",
    ]:
        if match := re.match(regex, repo):
            return match.group(1)
    raise typer.BadParameter(
        f"Supply repo in `owner/repo` format, or as a git or github URL.Invalid repo: {repo}."
    )
