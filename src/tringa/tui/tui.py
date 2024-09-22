from collections import defaultdict
from datetime import datetime
from typing import Iterator, Optional

import humanize
from rich.table import Table
from rich.text import Text
from textual.app import App, ComposeResult, RenderResult
from textual.binding import Binding
from textual.css.query import NoMatches
from textual.widgets import Collapsible, ListItem, ListView, RichLog, Static
from textual.widgets._collapsible import CollapsibleTitle

from tringa.cli.run.results import RunResults
from tringa.models import PR, Run, TestResult


class RunResultsWidget(Static):
    def __init__(self, run_results: RunResults):
        super().__init__()
        self.run_result = run_results

    def render(self) -> RenderResult:
        rr = self.run_result
        pr = rr.run.pr

        def rows():
            yield (
                "Repo",
                f"[@click=app.open_url('https://github.com/{rr.run.repo}')]{rr.run.repo}[/]",
            )
            yield (
                "PR",
                f"[@click=app.open_url('{pr.url}')]#{pr.number} {pr.title}[/]",
            )
            yield (
                "Last run",
                f"[@click=app.open_url('{rr.run.url()}')]{humanize.naturaltime(rr.run.time)}[/]",
            )
            yield (
                "Failed tests",
                Text(str(len(rr.failed_tests)), style="bold"),
            )

        table = Table(show_header=False)
        for row in rows():
            table.add_row(*row)
        return table


class FailedTestWidget(Collapsible):
    def __init__(self, test: TestResult, language: Optional[str]):
        title = test.name
        if test.flaky:
            title = f"{title} [bold yellow]FLAKY[/]"

        rich_log = RichLog()
        rich_log.write(test.text)

        super().__init__(rich_log, title=title)


class RunResultApp(App):
    CSS_PATH = "./tringa.tcss"

    BINDINGS = [
        Binding("right", "show_test_output", "Show test output"),
        Binding("left", "hide_test_output", "Hide test output"),
    ]

    def __init__(self, run_result: RunResults):
        super().__init__()
        self.run_result = run_result

    def compose(self) -> ComposeResult:
        yield RunResultsWidget(self.run_result)
        language = self.run_result.guess_language()

        def per_file_results() -> Iterator[tuple[str, ListView]]:
            tests_by_file = defaultdict(list[TestResult])
            for test in self.run_result.failed_tests:
                tests_by_file[test.file].append(test)
            for file, tests in sorted(tests_by_file.items()):
                name = file.removesuffix(".xml")
                n_flaky = sum(1 for test in tests if test.flaky)
                yield (
                    f"{name} [bold red]{len(tests)} failed[/] ([bold yellow]{n_flaky} flaky[/])",
                    ListView(
                        *[ListItem(FailedTestWidget(test, language)) for test in tests]
                    ),
                )

        yield ListView(
            *[
                ListItem(Collapsible(list_view, title=title))
                for title, list_view in per_file_results()
            ]
        )

    def action_open_url(self, url: str) -> None:
        self.open_url(url)

    def on_list_view_highlighted(self, event: ListView.Highlighted) -> None:
        """Apply a color to the focused test name"""
        # By default, the entire ListItem has a background color applied when
        # highlighted, and this color extends to the entire Collapsible content
        # when shown. To avoid that, the CSS removes that highlight color, and
        # we apply a color to the titles of the Collapsibles instead.
        if item := event.item:
            if title := item.query_one(CollapsibleTitle):
                for other_title in self.query(CollapsibleTitle):
                    other_title.remove_class("highlighted")
                title.add_class("highlighted")

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """
        Toggle test output visibility

        This is bound to <Enter> by ListView.
        """
        if item := event.item:
            if collapsible := item.query_one(Collapsible):
                collapsible.collapsed = not collapsible.collapsed

    def action_show_test_output(self) -> None:
        self._set_test_output_visibility(True)

    def action_hide_test_output(self) -> None:
        self._set_test_output_visibility(False)

    def _set_test_output_visibility(self, visible: bool) -> None:
        if focused := self.focused:
            if isinstance(focused, ListView):
                if list_item := focused.highlighted_child:
                    try:
                        collapsible = list_item.query_one(Collapsible)
                    except NoMatches:
                        pass
                    else:
                        collapsible.collapsed = not visible


def tui(run_result: RunResults) -> None:
    app = RunResultApp(run_result)
    app.run()


if __name__ == "__main__":
    tui(
        RunResults(
            run=Run(
                repo="repo",
                id="id",
                time=datetime.now(),
                pr=PR(
                    title="title",
                    url="url",
                    headRefName="headRefName",
                    headRepository={"name": "owner/repo"},
                    headRepositoryOwner={"login": "owner"},
                    number=77,
                ),
            ),
            failed_tests=(
                [
                    TestResult(
                        artifact_name="artifact_name",
                        repo="repo",
                        branch="branch",
                        file="example.py",
                        name="test_example",
                        run_id="run_id",
                        sha="sha",
                        suite="suite",
                        suite_timestamp=datetime.now(),
                        suite_time=1,
                        classname="classname",
                        time=1,
                        passed=False,
                        flaky=False,
                        skipped=False,
                        message="message",
                        text="""Traceback (most recent call last):
  File "example.py", line 10, in <module>
    result = divide(10, 0)
  File "example.py", line 6, in divide
    return a / b
ZeroDivisionError: division by zero""",
                    )
                ]
                * 7
            ),
        )
    )
