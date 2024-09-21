import asyncio
from typing import Annotated, NoReturn, Optional

import typer

import tringa.cli.run
import tringa.repl
from tringa import cli, gh, queries
from tringa.annotations import flaky as flaky
from tringa.models import Run

app = typer.Typer(rich_markup_mode="rich")


PrIdentifier = Annotated[
    Optional[str],
    typer.Argument(
        help="""PR number, PR URL, branch name, or any other PR identifier accepted by the `gh` GitHub CLI tool (https://cli.github.com/manual/)."""
    ),
]


@app.command()
def repl(
    pr_identifier: PrIdentifier = None,
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
    tringa.cli.run.repl(_get_run(pr_identifier), repl)


@app.command()
def rerun(pr_identifier: PrIdentifier = None) -> None:
    """Rerun failed tests in the latest run for this PR."""
    tringa.cli.run.rerun(_get_run(pr_identifier))


@app.command()
def show(pr_identifier: PrIdentifier = None) -> None:
    """Summarize tests in the latest run for this PR."""
    tringa.cli.run.show(_get_run(pr_identifier))


@app.command()
def sql(query: str, pr_identifier: PrIdentifier = None) -> None:
    """Execute a SQL query against tests in the latest run for this PR."""
    tringa.cli.run.sql(_get_run(pr_identifier), query)


@app.command()
def tui(pr_identifier: PrIdentifier = None) -> NoReturn:
    """Browse tests in the latest run for this PR using an interactive interface."""
    tringa.cli.run.tui(_get_run(pr_identifier))


def _get_run(pr_identifier: Optional[str]) -> Run:
    pr = asyncio.run(gh.pr(pr_identifier))
    with cli.options.db_config.connect() as db:
        return queries.last_run(db, pr)
