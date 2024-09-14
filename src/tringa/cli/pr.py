import asyncio
from typing import Annotated, Optional

import typer

import tringa.repl
from tringa import gh as gh
from tringa import queries as queries
from tringa.annotations import flaky as flaky
from tringa.artifact import fetch_and_load_new_artifacts
from tringa.cli import globals
from tringa.exceptions import TringaQueryException
from tringa.utils import tee as tee


def pr(
    pr_identifier: Annotated[Optional[str], typer.Argument()] = None,
    artifact_name_globs: Optional[list[str]] = None,
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
        fetch_and_load_new_artifacts(
            db, [pr.repo], artifact_name_globs=artifact_name_globs
        )
        flaky.annotate(db.cursor())
        if repl:
            tringa.repl.repl(db, repl)
        else:
            sql = queries.last_run_id(pr.repo, pr.branch)
            results = db.cursor().execute(tee(sql)).fetchall()
            if not results:
                raise TringaQueryException(f"Query returned no results:\n{sql}")
            [run_id] = results
            if rerun:
                asyncio.run(gh.rerun(pr.repo, run_id))
            else:
                print(db.exec_to_string(tee(queries.count_test_results())))
                print(db.exec_to_string(tee(queries.failed_tests_in_run(run_id))))
