import asyncio
from typing import Annotated, NoReturn, Optional

import typer

import tringa.cli.run.cli
import tringa.repl
from tringa import cli, gh, queries
from tringa.annotations import flaky as flaky
from tringa.fetch import fetch_data_for_pr
from tringa.models import PR, Run

app = typer.Typer(rich_markup_mode="rich")


PrOption = Annotated[
    Optional[str],
    typer.Argument(
        help="""PR number, PR URL, branch name, or any other PR identifier accepted by the `gh` GitHub CLI tool (https://cli.github.com/manual/)."""
    ),
]


def sync(pr_option: PrOption) -> PR:
    pr = asyncio.run(gh.pr(pr_option))
    if not cli.options.nosync:
        fetch_data_for_pr(pr)
    return pr


@app.command()
def failed(pr: PrOption = None) -> None:
    """Summarize failed tests in the latest run for this PR."""
    tringa.cli.run.cli.failed(_get_last_run(sync(pr)))


@app.command()
def flakes(pr: PrOption = None) -> None:
    """Summarize flaky tests in the latest run for this PR."""
    tringa.cli.run.cli.flakes(_get_last_run(sync(pr)))


@app.command()
def repl(
    pr: PrOption = None,
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
    Start an interactive REPL allowing execution of SQL queries against tests from the latest run for this PR.
    """
    tringa.cli.run.cli.repl(_get_last_run(sync(pr)), repl)


@app.command()
def rerun(pr: PrOption = None) -> None:
    """Rerun failed tests in the latest run for this PR."""
    tringa.cli.options.nosync = True
    tringa.cli.run.cli.rerun(_get_last_run(sync(pr)))


@app.command()
def show(pr: PrOption = None) -> None:
    """Summarize tests in the latest run for this PR."""
    tringa.cli.run.cli.show(_get_last_run(sync(pr)))


@app.command()
def sql(query: str, pr: PrOption = None) -> None:
    """Execute a SQL query against tests in the latest run for this PR."""
    tringa.cli.run.cli.sql(_get_last_run(sync(pr)), query)


@app.command()
def tui(pr: PrOption = None) -> NoReturn:
    """Browse tests in the latest run for this PR using an interactive interface."""
    tringa.cli.run.cli.tui(_get_last_run(sync(pr)))


def _get_last_run(pr: PR) -> Run:
    with cli.options.db_config.connect() as db:
        return queries.last_run(db, pr)
