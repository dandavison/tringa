import asyncio
from typing import Annotated, Optional

import typer

import tringa.repl
from tringa import gh, queries
from tringa.annotations import flaky as flaky
from tringa.artifact import fetch_and_load_new_artifacts
from tringa.cli import globals
from tringa.db import DB
from tringa.models import Run, RunResult
from tringa.rich import print, print_json
from tringa.tui.tui import tui


def pr(
    pr_identifier: Annotated[Optional[str], typer.Argument()] = None,
    repl: Optional[tringa.repl.Repl] = None,
    rerun: bool = False,
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
    if repl and rerun:
        raise typer.BadParameter("--repl and --rerun cannot be used together")
    globals.validate_repl(repl)

    pr = asyncio.run(gh.pr(pr_identifier))
    with globals.options.db_config.connect() as db:
        # We do not restrict to the PR branch in order to collect information
        # across branches used to identify flakes.
        fetch_and_load_new_artifacts(db, [pr.repo])
        flaky.annotate(db.cursor())
        if repl:
            tringa.repl.repl(db, repl)

        run = queries.last_run(db, pr)

        if rerun:
            asyncio.run(gh.rerun(pr.repo, run.id))
            return

        result = make_run_result(db, run)
        if globals.options.json:
            print_json(data=result.to_dict(), sort_keys=True)
        elif globals.options.tui:
            tui(run_result=result)
        else:
            print(result)


def make_run_result(db: DB, run: Run) -> RunResult:
    return RunResult(
        run=run,
        failed_tests=queries.failed_tests_in_run(
            db, {"run_id": run.id, "repo": run.repo}
        ),
    )
