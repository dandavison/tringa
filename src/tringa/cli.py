import asyncio
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Optional

import duckdb
import typer
from xdg_base_dirs import xdg_data_home

import tringa.repl
from tringa import gh, queries
from tringa.annotations import flaky
from tringa.artifact import fetch_and_load_new_artifacts
from tringa.db import DBConfig, DBType
from tringa.msg import error, info
from tringa.utils import tee

app = typer.Typer(rich_markup_mode="rich")


@dataclass
class GlobalOptions:
    db_config: DBConfig


_global_options: GlobalOptions


@app.callback()
def global_options(
    db_path: Optional[Path] = None,
    db_type: DBType = DBType.DUCKDB,
):
    if db_path is None:
        dir = Path(xdg_data_home()) / "tringa"
        dir.mkdir(parents=True, exist_ok=True)
        db_path = dir / f"tringa.{db_type.value}"
    elif db_path == ":memory:":
        db_path = None

    global _global_options
    _global_options = GlobalOptions(db_config=DBConfig(db_type=db_type, path=db_path))


@app.command()
def dropdb():
    if _global_options.db_config.path:
        _global_options.db_config.path.unlink()
        info("Deleted database at", _global_options.db_config.path)


@app.command()
def repl(
    repos: list[str],
    branch: Optional[str] = None,
    artifact_name_globs: Optional[list[str]] = None,
    repl: tringa.repl.Repl = tringa.repl.Repl.PYTHON,
):
    _validate_options(_global_options, repl)
    with _global_options.db_config.connect() as db:
        fetch_and_load_new_artifacts(db, repos, branch, artifact_name_globs)
        tringa.repl.repl(db, repl)


@app.command()
def pr(
    pr_identifier: Annotated[Optional[str], typer.Argument()] = None,
    artifact_name_globs: Optional[list[str]] = None,
    repl: Optional[tringa.repl.Repl] = None,
):
    """
    Fetch and analyze test results from a PR.

    --pr-identifier may be any of the formats accepted by the GitHub `gh` CLI tool (https://cli.github.com/manual/):
      - PR number, e.g. "123";
      - PR URL, e.g. "https://github.com/OWNER/REPO/pull/123"; or
      - name of the PR's head branch, e.g. "patch-1" or "OWNER:patch-1".

    By default, a table of failed tests is printed, but --repl is available.
    Note that if you use --db-path, then the DB in the REPL may have tests from
    other PRs, repos, etc.
    """
    _validate_options(_global_options, repl)
    pr = asyncio.run(gh.pr(pr_identifier))
    with _global_options.db_config.connect() as db:
        # We do not restrict to the PR branch in order to collect information
        # across branches used to identify flakes.
        fetch_and_load_new_artifacts(
            db, [pr.repo], artifact_name_globs=artifact_name_globs
        )
        flaky.annotate(db.cursor())
        if repl:
            tringa.repl.repl(db, repl)
        else:
            run_id = (
                db.cursor()
                .execute(tee(queries.last_run_id(pr.repo, pr.branch)))
                .fetchone()[0]
            )
            print(db.sql(tee(queries.count_test_results())))
            print(db.sql(tee(queries.failed_tests_in_run(run_id))))


def _validate_options(global_options: GlobalOptions, repl: Optional[tringa.repl.Repl]):
    if repl == tringa.repl.Repl.SQL and not global_options.db_config.path:
        raise typer.BadParameter(
            "The --repl sql option requires --db-path."
            "\n\n"
            "SQL REPLs cannot be used with an in-memory db, since the Python app and the SQL REPL are different processes. "
            "However, the duckdb Python REPL can be used with an in-memory db, and this combination is the default.",
        )


warnings.filterwarnings(
    "ignore",
    message="Attempting to work in a virtualenv. If you encounter problems, please install IPython inside the virtualenv.",
)


def main():
    try:
        app()
    except duckdb.IOException as e:
        error(
            f"{e}\n\nIt looks like you left a tringa REPL open? Connecting to the DB from multiple processes is not supported currently."
        )
        exit(1)
    except Exception as e:
        error(e)
        exit(1)
