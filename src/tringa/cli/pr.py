import asyncio
from typing import Annotated, NoReturn, Optional

import typer

import tringa.cli.run
import tringa.repl
from tringa import cli, gh, queries
from tringa.annotations import flaky as flaky
from tringa.models import Run

app = typer.Typer(rich_markup_mode="rich")


@app.command()
def repl(
    pr_identifier: Annotated[Optional[str], typer.Argument()] = None,
    repl: Optional[tringa.repl.Repl] = None,
) -> NoReturn:
    tringa.cli.run.repl(_get_run(pr_identifier), repl)


@app.command()
def rerun(pr_identifier: Annotated[Optional[str], typer.Argument()] = None) -> None:
    tringa.cli.run.rerun(_get_run(pr_identifier))


@app.command()
def show(pr_identifier: Annotated[Optional[str], typer.Argument()] = None) -> None:
    tringa.cli.run.show(_get_run(pr_identifier))


@app.command()
def sql(
    query: str, pr_identifier: Annotated[Optional[str], typer.Argument()] = None
) -> None:
    tringa.cli.run.sql(_get_run(pr_identifier), query)


@app.command()
def tui(pr_identifier: Annotated[Optional[str], typer.Argument()] = None) -> NoReturn:
    tringa.cli.run.tui(_get_run(pr_identifier))


def _get_run(pr_identifier: Optional[str]) -> Run:
    pr = asyncio.run(gh.pr(pr_identifier))
    with cli.options.db_config.connect() as db:
        return queries.last_run(db, pr)
