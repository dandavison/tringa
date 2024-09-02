from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import typer
from xdg_base_dirs import xdg_data_home

import tringa.repl
from tringa.db import DBConfig, DBType


@dataclass
class GlobalOptions:
    db_config: DBConfig


options: GlobalOptions


def set_options(
    db_path: Optional[Path] = None,
    db_type: DBType = DBType.DUCKDB,
):
    if db_path is None:
        dir = Path(xdg_data_home()) / "tringa"
        dir.mkdir(parents=True, exist_ok=True)
        db_path = dir / f"tringa.{db_type.value}"
    elif db_path == ":memory:":
        db_path = None

    global options
    options = GlobalOptions(db_config=DBConfig(db_type=db_type, path=db_path))


def validate_repl(repl: Optional[tringa.repl.Repl]):
    if repl == tringa.repl.Repl.SQL and not options.db_config.path:
        raise typer.BadParameter(
            "The --repl sql option requires --db-path."
            "\n\n"
            "SQL REPLs cannot be used with an in-memory db, since the Python app and the SQL REPL are different processes. "
            "However, the duckdb Python REPL can be used with an in-memory db, and this combination is the default.",
        )
