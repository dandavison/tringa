from dataclasses import dataclass

from rich.console import Console, ConsoleOptions, RenderResult
from rich.table import Table
from rich.text import Text

from tringa.cli import reports
from tringa.cli.reports import flakes, slowtests
from tringa.db import DB
from tringa.queries import EmptyParams, Query


@dataclass
class Report(reports.Report):
    repo: str
    prs: int
    flaky_tests: flakes.Report
    slow_tests: slowtests.Report

    def to_dict(self) -> dict:
        return {
            "repo": self.repo,
            "flaky_tests": self.flaky_tests,
        }

    def __rich_console__(
        self, console: Console, options: ConsoleOptions
    ) -> RenderResult:
        def make_summary():
            def rows():
                yield (
                    "Repo",
                    f"[link=https://github.com/{self.repo}]{self.repo}[/link]",
                )
                yield (
                    "PRs",
                    Text(str(self.prs), style="bold"),
                )
                yield (
                    "Flaky tests",
                    self.flaky_tests.summary(),
                )
                yield (
                    "Slow tests",
                    self.slow_tests.summary(),
                )

            table = Table(show_header=False)
            table = Table(show_header=False)
            for row in rows():
                table.add_row(*row)
            return table

        yield make_summary()


def make_report(db: DB, repo: str) -> Report:
    prs = Query[tuple[int], EmptyParams](
        """
        select count(*) from (
            select distinct pr_number from test
        );
        """
    ).fetchone(db, {})[0]

    return Report(
        repo=repo,
        prs=prs,
        flaky_tests=flakes.make_report(db),
        slow_tests=slowtests.make_report(db, limit=10),
    )
