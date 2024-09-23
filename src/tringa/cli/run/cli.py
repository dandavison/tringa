import asyncio
from typing import NoReturn, Optional

import tringa.cli.reports.flaky_tests
import tringa.cli.run.cli
import tringa.cli.run.show
import tringa.repl
import tringa.tui.tui
from tringa import cli, gh, scoped_db
from tringa.annotations import flaky as flaky
from tringa.cli.output import tringa_print
from tringa.models import Run

reports = tringa.cli.reports


def flakes(run: Run) -> None:
    with scoped_db.connect(cli.options.db_config, repo=run.repo, run_id=run.id) as db:
        tringa_print(reports.flaky_tests.make_report(db))


def repl(run: Run, repl: Optional[tringa.repl.Repl]) -> NoReturn:
    with scoped_db.connect(cli.options.db_config, repo=run.repo, run_id=run.id) as db:
        tringa.repl.repl(db, repl)


def rerun(run: Run) -> None:
    asyncio.run(gh.rerun(run.repo, run.id))


def show(run: Run) -> None:
    with scoped_db.connect(cli.options.db_config, repo=run.repo, run_id=run.id) as db:
        tringa_print(tringa.cli.run.show.make_report(db, run))


def sql(run: Run, query: str) -> None:
    """
    Execute a SQL query against the database.
    """
    with scoped_db.connect(cli.options.db_config, repo=run.repo, run_id=run.id) as db:
        tringa_print(db.connection.sql(query))


def tui(run: Run) -> NoReturn:  # type: ignore
    with scoped_db.connect(cli.options.db_config, repo=run.repo, run_id=run.id) as db:
        tringa.tui.tui.tui(run_result=tringa.cli.run.show.make_report(db, run))
