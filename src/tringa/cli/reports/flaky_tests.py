from collections import defaultdict
from dataclasses import dataclass
from typing import DefaultDict

from rich.console import Console, ConsoleOptions, RenderResult
from rich.table import Table

from tringa import cli
from tringa.cli import reports
from tringa.db import DB
from tringa.models import Run, SerializableDict, TestResult
from tringa.queries import EmptyParams, Query


@dataclass
class Build(reports.Report):
    file: str
    run: Run

    @property
    def name(self) -> str:
        return self.file.removesuffix(".xml")

    def __rich__(self) -> str:
        return f"[link={self.run.url}]{self.file}[/link]"

    def __rich_console__(
        self, console: Console, options: ConsoleOptions
    ) -> RenderResult:
        yield self.__rich__()

    def to_dict(self) -> SerializableDict:
        return {
            "name": self.file,
        }


@dataclass
class FlakyTestPR(reports.Report):
    run: Run
    failed_builds: list[Build]

    def __rich_console__(
        self, console: Console, options: ConsoleOptions
    ) -> RenderResult:
        table = Table(self.run.title())
        for build in self.failed_builds:
            table.add_row(build)
        yield table

    def to_dict(self) -> SerializableDict:
        return {
            "run": self.run.to_dict(),
            "failed_builds": [b.to_dict() for b in self.failed_builds],
        }


@dataclass
class FlakyTest(reports.Report):
    name: str
    prs_with_failures: list[FlakyTestPR]

    def __rich_console__(
        self, console: Console, options: ConsoleOptions
    ) -> RenderResult:
        table = Table(title=self.name, show_header=False)
        for pr in self.prs_with_failures:
            table.add_row(pr.run.pr, "\n".join(b.__rich__() for b in pr.failed_builds))
        yield table

    def to_dict(self) -> SerializableDict:
        return {
            "name": self.name,
            "failed_runs": [r.to_dict() for r in self.prs_with_failures],
        }


@dataclass
class Summary(reports.Report):
    tests: list[FlakyTest]

    def to_dict(self) -> dict:
        return {"test_names": sorted({t.name for t in self.tests})}

    def __rich_console__(
        self, console: Console, options: ConsoleOptions
    ) -> RenderResult:
        seen = set()
        for i, test in enumerate(sorted(self.tests, key=lambda x: x.name)):
            if i + 1 == cli.options.table_row_limit:
                yield f"...[{len(self.tests) - i} more]"
                break
            if test.name in seen:
                continue
            seen.add(test.name)
            if run := next((pr.run for pr in test.prs_with_failures), None):
                yield f"[link={run.url}]{test.name}[/link]"
            else:
                yield test.name


@dataclass
class Report(reports.Report):
    tests: list[FlakyTest]

    def summary(self) -> Summary:
        return Summary(tests=self.tests)

    def to_dict(self) -> SerializableDict:
        return {"tests": [t.to_dict() for t in self.tests]}

    def __rich_console__(
        self, console: Console, options: ConsoleOptions
    ) -> RenderResult:
        for test in self.tests:
            yield test


def make_report(db: DB) -> Report:
    test_results = Query[TestResult, EmptyParams](
        """
        select * from test
        where flaky = true and passed = false and skipped = false
        order by name, branch, file, suite_time desc;
        """
    ).fetchall(db, {})

    name_to_branch_to_file_to_latest_failure: DefaultDict[
        str, DefaultDict[str, dict[str, TestResult]]
    ] = defaultdict(lambda: defaultdict(lambda: defaultdict()))
    for tr in test_results:
        file_to_latest_failure = name_to_branch_to_file_to_latest_failure[tr.name][
            tr.branch
        ]
        # Data should be unique on (branch, run, run_attempt, file, name)
        # but run_attempt is not in the table because it is not returned by
        # the GitHub artifacts API. So, we take the first for each file.
        file_to_latest_failure.setdefault(tr.file, tr)

    def flaky_tests():
        for (
            name,
            branch_to_file_to_latest_failure,
        ) in name_to_branch_to_file_to_latest_failure.items():
            prs_with_failures = []
            for (
                branch,
                file_to_latest_failure,
            ) in branch_to_file_to_latest_failure.items():
                failed_builds = [
                    Build(
                        file,
                        Run(
                            repo=tr.repo,
                            id=tr.run_id,
                            branch=branch,
                            sha=tr.sha,
                            pr=tr.make_pr(),
                            started_at=tr.suite_time,
                        ),
                    )
                    for file, tr in file_to_latest_failure.items()
                ]
                # FIXME
                run = next(b.run for b in failed_builds)

                prs_with_failures.append(
                    FlakyTestPR(
                        run=run,
                        failed_builds=failed_builds,
                    )
                )
            yield FlakyTest(name, prs_with_failures)

    return Report(tests=list(flaky_tests()))
