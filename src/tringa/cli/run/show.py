from dataclasses import dataclass

import humanize
from rich.console import Console, ConsoleOptions, RenderResult
from rich.table import Table

from tringa.cli import reports
from tringa.cli.reports import failedtests, flakes
from tringa.db import DB
from tringa.models import Run


@dataclass
class Report(reports.Report):
    run: Run
    failed_tests: failedtests.Report
    flaky_tests: flakes.Report

    def to_dict(self) -> dict:
        return {
            "run": self.run.to_dict(),
            "flaky_tests": self.flaky_tests.to_dict(),
        }

    def __rich_console__(
        self, console: Console, options: ConsoleOptions
    ) -> RenderResult:
        pr = self.run.pr

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
                self.failed_tests.summary(),
            )
            yield (
                "Flaky tests",
                self.flaky_tests.summary(),
            )

        table = Table(show_header=False)
        for row in rows():
            table.add_row(*row)
        yield table


def make_report(db: DB, run: Run) -> Report:
    return Report(
        run=run,
        failed_tests=failedtests.make_report(db),
        flaky_tests=flakes.make_report(db),
    )
