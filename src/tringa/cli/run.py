import asyncio
from typing import NoReturn, Optional

import tringa.cli.run
import tringa.repl
import tringa.tui.tui
from tringa import cli, gh, queries, scoped_db
from tringa.annotations import flaky as flaky
from tringa.cli import output
from tringa.db import DB
from tringa.models import Run, RunResult


def flakes(run: Run) -> None:
    with scoped_db.connect(
        cli.options.db_config, repo=run.repo, run_id=run.id
    ) as run_db:
        flakes = [
            s
            for (s,) in run_db.connection.sql(
                "select distinct name from test where flaky=true"
            ).fetchall()
        ]
        with cli.options.db_config.connect() as main_db:
            output.print_relation(
                main_db.connection.sql(
                    f"""
                    select name, branch, count(*) from test
                    where name in {tuple(flakes)} and
                        passed=false and
                        skipped=false and
                        repo = '{run.repo}' and run_id = '{run.id}'
                    group by name, branch
                    """
                )
            )


def repl(run: Run, repl: Optional[tringa.repl.Repl]) -> NoReturn:
    with scoped_db.connect(cli.options.db_config, repo=run.repo, run_id=run.id) as db:
        tringa.repl.repl(db, repl)


def rerun(run: Run) -> None:
    asyncio.run(gh.rerun(run.pr.repo, run.id))


def show(run: Run) -> None:
    with scoped_db.connect(cli.options.db_config, repo=run.repo, run_id=run.id) as db:
        output.print_serializable(_make_run_result(db, run))


def sql(run: Run, query: str) -> None:
    """
    Execute a SQL query against the database.
    """
    with scoped_db.connect(cli.options.db_config, repo=run.repo, run_id=run.id) as db:
        output.print_relation(db.connection.sql(query))


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
