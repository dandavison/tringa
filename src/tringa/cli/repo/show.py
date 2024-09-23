from dataclasses import dataclass

from rich.console import Console, ConsoleOptions, RenderResult
from rich.table import Table
from rich.text import Text

from tringa.cli import reports
from tringa.cli.reports import slowtests
from tringa.db import DB
from tringa.queries import EmptyParams, Query


@dataclass
class Report(reports.Report):
    repo: str
    prs: int
    flaky_tests: int
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
                    Text(str(self.flaky_tests), style="bold"),
                )
                yield (
                    "Slow tests",
                    self.slow_tests,
                )

            table = Table(show_header=False)
            table = Table(show_header=False)
            for row in rows():
                table.add_row(*row)
            return table

        yield make_summary()


def make_report(db: DB, repo: str) -> Report:
    flaky_tests = Query[tuple[int], EmptyParams](
        """
        select count(*) from (
            select distinct classname, name from test
            where flaky = true
        );
        """
    ).fetchone(db, {})[0]
    prs = Query[tuple[int], EmptyParams](
        """
        select count(*) from (
            select distinct pr_number from test
        );
        """
    ).fetchone(db, {})[0]

    slow_tests = slowtests.make_report(db, limit=10)
    return Report(
        repo=repo,
        prs=prs,
        flaky_tests=flaky_tests,
        slow_tests=slow_tests,
    )
