import asyncio
from typing import NoReturn, Optional

import tringa.cli.run.cli
import tringa.repl
import tringa.tui.tui
from tringa import cli, gh, queries, scoped_db
from tringa.annotations import flaky as flaky
from tringa.cli.output import tringa_print
from tringa.cli.reports.flakes import get_flakes
from tringa.cli.run.results import RunResults
from tringa.db import DB
from tringa.models import Run


def flakes(run: Run) -> None:
    with scoped_db.connect(cli.options.db_config, repo=run.repo, run_id=run.id) as db:
        tringa_print(get_flakes(db))


def repl(run: Run, repl: Optional[tringa.repl.Repl]) -> NoReturn:
    with scoped_db.connect(cli.options.db_config, repo=run.repo, run_id=run.id) as db:
        tringa.repl.repl(db, repl)


def rerun(run: Run) -> None:
    asyncio.run(gh.rerun(run.repo, run.id))


def show(run: Run) -> None:
    with scoped_db.connect(cli.options.db_config, repo=run.repo, run_id=run.id) as db:
        tringa_print(_make_run_result(db, run))


def sql(run: Run, query: str) -> None:
    """
    Execute a SQL query against the database.
    """
    with scoped_db.connect(cli.options.db_config, repo=run.repo, run_id=run.id) as db:
        tringa_print(db.connection.sql(query))


def tui(run: Run) -> NoReturn:  # type: ignore
    with scoped_db.connect(cli.options.db_config, repo=run.repo, run_id=run.id) as db:
        tringa.tui.tui.tui(run_result=_make_run_result(db, run))


def _make_run_result(db: DB, run: Run) -> RunResults:
    return RunResults(
        run=run,
        failed_tests=queries.failed_test_results(db, {}),
    )
