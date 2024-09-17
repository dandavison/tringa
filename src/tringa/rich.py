from typing import TYPE_CHECKING

import humanize
from rich.console import Console, RenderResult
from rich.table import Table
from rich.text import Text

from tringa.cli import globals

if TYPE_CHECKING:
    from tringa.models import RunResult

console = Console()

print = console.print
print_json = console.print_json


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

    def make_failed_tests():
        def rows():
            for test in run_result.failed_tests:
                yield (test.name, test.text)

        for name, text in rows():
            table = Table(name)
            table.add_row(text)
            yield table

    yield make_header()
    if globals.options.verbose > 1:
        yield from make_failed_tests()
