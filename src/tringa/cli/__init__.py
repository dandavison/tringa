from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from typing import Annotated, Optional

import typer

import tringa.repl
from tringa import cli as cli
from tringa.cli.output import console as console
from tringa.db import DBConfig


@dataclass
class GlobalOptions:
    artifact_globs: list[str]
    since: timedelta
    db_config: DBConfig
    json: bool
    nosync: bool
    tui: bool
    verbose: int
    table_row_limit: int = 20


options: GlobalOptions


def set_options(
    artifact_globs: list[str] = ["*junit*", "*xunit*", "*xml*"],
    since_days: int = 90,
    db_path: Optional[Path] = None,
    json: bool = False,
    nosync: Annotated[
        bool, typer.Option("--nosync", "-n", help="Do not fetch data.")
    ] = False,
    tui: bool = False,
    verbose: int = 1,
):
    if tui and json:
        raise typer.BadParameter("--tui and --json cannot be used together")

    if db_path is None:
        # No session-to-session persistence unless user supplies a path for the db.
        db_path = Path("/tmp/__tringa_non_persistent__.db")
        if db_path.exists():
            db_path.unlink()

    global options
    options = GlobalOptions(
        artifact_globs=artifact_globs,
        since=timedelta(days=since_days),
        db_config=DBConfig(path=db_path),
        json=json,
        nosync=nosync,
        tui=tui,
        verbose=verbose,
    )


set_options()


def validate_repl(repl: Optional[tringa.repl.Repl]):
    if repl == tringa.repl.Repl.SQL and not options.db_config.path:
        raise typer.BadParameter(
            "The --repl sql option requires --db-path."
            "\n\n"
            "SQL REPLs cannot be used with an in-memory db, since the Python app and the SQL REPL are different processes. "
            "However, the duckdb Python REPL can be used with an in-memory db.",
        )
