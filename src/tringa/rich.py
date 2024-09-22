from typing import TYPE_CHECKING

import humanize
from rich.console import Console, RenderResult
from rich.table import Table
from rich.text import Text

from tringa import cli

if TYPE_CHECKING:
    from tringa.models import RepoResult, RunResult, TestResult

console = Console()

print = console.print
print_json = console.print_json


def render_repo_result(repo_result: "RepoResult") -> RenderResult:
    rr = repo_result

    def make_summary():
        def rows():
            yield (
                "Repo",
                f"[link=https://github.com/{rr.repo}]{rr.repo}[/link]",
            )
            yield (
                "Flaky tests",
                Text(str(len(rr.flaky_tests)), style="bold"),
            )

        table = Table(show_header=False)
        for row in rows():
            table.add_row(*row)
        return table

    def make_flaky_tests():
        table = Table("Flaky tests", show_header=True)
        for (name,) in rr.flaky_tests:
            table.add_row(name)
        return table

    yield make_summary()
    yield make_flaky_tests()


def render_run_result(run_result: "RunResult") -> RenderResult:
    rr = run_result
    pr = rr.run.pr

    def make_header():
        def rows():
            yield (
                "Repo",
                f"[link=https://github.com/{rr.run.repo}]{rr.run.repo}[/link]",
            )
            yield (
                "PR",
                f"[link={pr.url}]#{pr.number} {pr.title}[/link]",
            )
            yield (
                "Last run",
                f"[link={rr.run.url()}]{humanize.naturaltime(rr.run.time)}[/link]",
            )
            yield (
                "Failed tests",
                Text(str(len(rr.failed_tests)), style="bold"),
            )

        table = Table(show_header=False)
        for row in rows():
            table.add_row(*row)
        return table

    yield make_header()
    if cli.options.verbose > 1:
        yield from make_failed_tests(rr.failed_tests)


def make_failed_tests(failed_tests: list["TestResult"]):
    def rows():
        for test in failed_tests:
            yield (test.name, test.text)

    for name, text in rows():
        table = Table(name)
        table.add_row(text)
        yield table
