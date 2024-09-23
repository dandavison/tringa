from typing import Annotated, NoReturn, Optional

import typer

import tringa.cli.run.cli
import tringa.repl
from tringa import cli
from tringa.annotations import flaky as flaky

app = typer.Typer(rich_markup_mode="rich")


@app.command()
def repl(
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
    with cli.options.db_config.connect() as db:
        tringa.repl.repl(db, repl)
