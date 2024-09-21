import asyncio
from typing import NoReturn, Optional

import tringa.cli.run
import tringa.repl
import tringa.tui.tui
from tringa import cli, gh, queries, scoped_db
from tringa.annotations import flaky as flaky
from tringa.db import DB
from tringa.models import Run, RunResult
from tringa.rich import print, print_json


def repl(run: Run, repl: Optional[tringa.repl.Repl]) -> NoReturn:
    with scoped_db.connect(cli.options.db_config, repo=run.repo, run_id=run.id) as db:
        tringa.repl.repl(db, repl)


def rerun(run: Run) -> None:
    asyncio.run(gh.rerun(run.pr.repo, run.id))


def show(run: Run) -> None:
    with scoped_db.connect(cli.options.db_config, repo=run.repo, run_id=run.id) as db:
        result = _make_run_result(db, run)
        if cli.options.json:
            print_json(data=result.to_dict(), sort_keys=True)
        print(result)


def sql(run: Run, query: str):
    """
    Execute a SQL query against the database.
    """
    with scoped_db.connect(cli.options.db_config, repo=run.repo, run_id=run.id) as db:
        rel = db.connection.sql(query)
        if cli.options.json:
            print(rel.df().to_json(orient="records", indent=2))
        else:
            print(rel)


def tui(run: Run) -> NoReturn:  # type: ignore
    with scoped_db.connect(cli.options.db_config, repo=run.repo, run_id=run.id) as db:
        tringa.tui.tui.tui(run_result=_make_run_result(db, run))


def _make_run_result(db: DB, run: Run) -> RunResult:
    return RunResult(
        run=run,
        failed_tests=queries.failed_tests_in_run(
            db, {"run_id": run.id, "repo": run.repo}
        ),
    )
