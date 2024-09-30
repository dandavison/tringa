from dataclasses import dataclass

from rich.console import Console, ConsoleOptions, RenderResult
from rich.table import Table

from tringa import cli
from tringa.cli import reports
from tringa.db import DB
from tringa.models import TestResult
from tringa.queries import EmptyParams, Query


@dataclass
class Report(reports.Report):
    tests: list[TestResult]

    def summary(self) -> "Summary":
        return Summary(names=sorted({t.name for t in self.tests}))

    def to_dict(self) -> dict:
        return {
            "tests": [t.name for t in self.tests],
        }

    def __rich_console__(
        self, console: Console, options: ConsoleOptions
    ) -> RenderResult:
        for test in sorted(self.tests, key=lambda x: x.name):
            table = Table(f"[bold red]{test.name}[/]")
            table.add_row(test.text or "")
            yield table


@dataclass
class Summary(reports.Report):
    names: list[str]

    def to_dict(self) -> dict:
        return {
            "tests": self.names,
        }

    def __rich_console__(
        self, console: Console, options: ConsoleOptions
    ) -> RenderResult:
        for i, test in enumerate(self.names):
            if i + 1 == cli.options.table_row_limit:
                yield f"[red]...[{len(self.names) - i} more][/]"
                break
            yield f"[red]{test}[/]"


def make_report(db: DB) -> Report:
    failed_test_results = Query[TestResult, EmptyParams](
        """
    select * from test
    where passed = false and skipped = false
    order by file, flaky desc, duration desc;
    """
    ).fetchall(db, {})

    return Report(tests=failed_test_results)
