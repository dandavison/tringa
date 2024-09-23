from collections import defaultdict
from dataclasses import dataclass
from typing import Optional

from rich.console import Console, ConsoleOptions, RenderResult
from rich.table import Table

from tringa.cli.reports import Report
from tringa.db import DB
from tringa.queries import EmptyParams, Query


@dataclass
class SlowTest(Report):
    name: str
    max_successful_duration: Optional[float]
    max_failed_duration: Optional[float]

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "max_successful_duration": self.max_successful_duration,
            "max_failed_duration": self.max_failed_duration,
        }

    def __rich_console__(
        self, console: Console, options: ConsoleOptions
    ) -> RenderResult:
        yield self.name


@dataclass
class SlowTests(Report):
    tests: list[SlowTest]

    def to_dict(self) -> dict:
        return {
            "tests": [t.to_dict() for t in self.tests],
        }

    def __rich_console__(
        self, console: Console, options: ConsoleOptions
    ) -> RenderResult:
        table = Table()
        table.add_column("Name", style="blue")
        table.add_column("Max Duration (success)", style="green")
        table.add_column("Max Duration (failure)", style="red")

        for test in self.tests:
            table.add_row(
                test.name,
                (
                    f"{test.max_successful_duration:.1f}s"
                    if test.max_successful_duration is not None
                    else ""
                ),
                (
                    f"{test.max_failed_duration:.1f}s"
                    if test.max_failed_duration is not None
                    else ""
                ),
            )

        yield table


def get_slow_tests(db: DB, threshold: float = 0.0, limit: int = 30) -> SlowTests:
    successful_tests = Query[tuple[str, float], EmptyParams](
        f"""
        select name, max(duration) from test
        where duration > {threshold} and passed = true
        group by name
        order by max(duration) desc
        limit {limit};
        """
    ).fetchall(db, {})

    failed_tests = Query[tuple[str, float], EmptyParams](
        f"""
        select name, max(duration) from test
        where duration > {threshold} and passed = false and skipped = false
        group by name
        order by max(duration) desc
        limit {limit};
        """
    ).fetchall(db, {})

    slow_tests = defaultdict(
        lambda: dict[str, Optional[float]](
            max_successful_duration=None, max_failed_duration=None
        )
    )

    for name, duration in successful_tests:
        slow_tests[name]["max_successful_duration"] = duration

    for name, duration in failed_tests:
        slow_tests[name]["max_failed_duration"] = duration

    return SlowTests(
        tests=[
            SlowTest(
                name=name,
                max_successful_duration=t["max_successful_duration"],
                max_failed_duration=t["max_failed_duration"],
            )
            for name, t in slow_tests.items()
        ]
    )
