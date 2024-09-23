from dataclasses import dataclass

import humanize
from rich.console import Console, ConsoleOptions, RenderResult
from rich.table import Table
from rich.text import Text

from tringa import cli, queries
from tringa.cli import reports
from tringa.cli.reports import flakes
from tringa.db import DB
from tringa.models import Run, TestResult


@dataclass
class Report(reports.Report):
    run: Run
    failed_tests: list[TestResult]
    flaky_tests: flakes.Report

    def to_dict(self) -> dict:
        return {
            "run": self.run.to_dict(),
            "failed_tests": self.failed_tests,
        }

    def __rich_console__(
        self, console: Console, options: ConsoleOptions
    ) -> RenderResult:
        pr = self.run.pr

        def make_header():
            def rows():
                yield (
                    "Repo",
                    f"[link=https://github.com/{self.run.repo}]{self.run.repo}[/link]",
                )
                yield ("PR", pr)
                yield (
                    "Last run",
                    f"[link={self.run.url}]{humanize.naturaltime(self.run.time)}[/link]",
                )
                yield (
                    "Failed tests",
                    Text(str(len(self.failed_tests)), style="bold"),
                )
                yield (
                    "Flaky tests",
                    self.flaky_tests.summary(),
                )

            table = Table(show_header=False)
            for row in rows():
                table.add_row(*row)
            return table

        yield make_header()
        if cli.options.verbose > 1:
            yield from _make_failed_tests(self.failed_tests)


def _make_failed_tests(failed_tests: list[TestResult]):
    def rows():
        for test in failed_tests:
            yield (test.name, test.text)

    for name, text in rows():
        table = Table(name)
        table.add_row(text)
        yield table


def make_report(db: DB, run: Run) -> Report:
    return Report(
        run=run,
        failed_tests=queries.failed_test_results(db, {}),
        flaky_tests=flakes.make_report(db),
    )
