import asyncio
from dataclasses import dataclass
from typing import Annotated, Optional, Self

import humanize
import typer
from rich.console import Console, ConsoleOptions, RenderResult
from rich.table import Table
from rich.text import Text

import tringa.repl
from tringa import gh, queries
from tringa.annotations import flaky as flaky
from tringa.artifact import fetch_and_load_new_artifacts
from tringa.cli import globals
from tringa.db import DB
from tringa.models import Run
from tringa.rich import print, print_json


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

        run = queries.last_run(db, pr)

        if rerun:
            asyncio.run(gh.rerun(pr.repo, run.id))
            return

        result = RunResult.from_run(db, run)
        if globals.options.json:
            print_json(data=result.to_dict(), sort_keys=True)
        else:
            print(result)


@dataclass
class RunResult:
    run: Run
    failed_tests: list[queries.FailedTestRow]

    @classmethod
    def from_run(cls, db: DB, run: Run) -> Self:
        return cls(
            run=run,
            failed_tests=queries.failed_tests_in_run(
                db, {"run_id": run.id, "repo": run.repo}
            ),
        )

    def to_dict(self) -> dict:
        return {
            "run": self.run.to_dict(),
            "failed_tests": self.failed_tests,
        }

    def __rich_console__(
        self, console: Console, options: ConsoleOptions
    ) -> RenderResult:
        def make_header():
            def rows():
                if self.run.pr is not None:
                    yield (
                        "PR",
                        Text(
                            self.run.pr.title,
                            style=f"link {self.run.pr.url}",
                        ),
                    )
                yield (
                    "Last run",
                    Text(
                        humanize.naturaltime(self.run.time),
                        style=f"link {self.run.url()}",
                    ),
                )
                yield (
                    "Failed tests",
                    Text(str(len(self.failed_tests)), style="bold"),
                )

            table = Table(show_header=False)
            for row in rows():
                table.add_row(*row)
            return table

        def make_failed_tests():
            def rows():
                for test in self.failed_tests:
                    yield (test.name, test.text)

            for name, text in rows():
                table = Table(name)
                table.add_row(text)
                yield table

        yield make_header()
        if globals.options.verbose > 1:
            yield from make_failed_tests()
