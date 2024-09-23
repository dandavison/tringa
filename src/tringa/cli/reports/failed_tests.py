from dataclasses import dataclass

from rich.console import Console, ConsoleOptions, RenderResult

from tringa.cli import reports
from tringa.db import DB
from tringa.models import TestResult
from tringa.queries import EmptyParams, Query


@dataclass
class Report(reports.Report):
    tests: list[TestResult]

    def summary(self) -> "Summary":
        return Summary(tests=self.tests)

    def to_dict(self) -> dict:
        return {
            "tests": [t.name for t in self.tests],
        }

    def __rich_console__(
        self, console: Console, options: ConsoleOptions
    ) -> RenderResult:
        for test in self.tests:
            yield test.name


@dataclass
class Summary(Report):
    def __rich_console__(
        self, console: Console, options: ConsoleOptions
    ) -> RenderResult:
        if self.tests:
            yield f"[bold red]{len(self.tests)}[/]"
        else:
            yield "[bold green]0[/]"


def make_report(db: DB) -> Report:
    failed_test_results = Query[TestResult, EmptyParams](
        """
    select * from test
    where passed = false and skipped = false
    order by file, flaky desc, duration desc;
    """
    ).fetchall(db, {})

    return Report(tests=failed_test_results)
