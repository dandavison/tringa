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
    def make_header():
        def rows():
            if run_result.run.pr is not None:
                yield (
                    "PR",
                    f"[link={run_result.run.pr.url}]{run_result.run.pr.title}[/link]",
                )
            yield (
                "Last run",
                f"[link={run_result.run.url()}]{humanize.naturaltime(run_result.run.time)}[/link]",
            )
            yield (
                "Failed tests",
                Text(str(len(run_result.failed_tests)), style="bold"),
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
