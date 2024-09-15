from datetime import datetime
from typing import Optional

import humanize
from rich.table import Table
from rich.text import Text
from textual.app import App, ComposeResult, RenderResult
from textual.binding import Binding
from textual.css.query import NoMatches
from textual.widgets import Collapsible, ListItem, ListView, Static, TextArea
from textual.widgets._collapsible import CollapsibleTitle

from tringa.cli.pr import RunResult
from tringa.models import PR, FailedTestRow, Run


class RunResultSummary(Static):
    def __init__(self, run_result: RunResult):
        super().__init__()
        self.run_result = run_result

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


class FailedTest(Collapsible):
    def __init__(self, test: FailedTestRow, language: Optional[str]):
        title = test.name
        if test.flaky:
            title = f"{title} [bold red]FLAKY[/]"
        super().__init__(
            TextArea(test.text, language=language, read_only=True), title=title
        )


class RunResultApp(App):
    CSS_PATH = "./tringa.tcss"

    BINDINGS = [
        Binding("right", "show_test_output", "Show test output"),
        Binding("left", "hide_test_output", "Hide test output"),
    ]

    def __init__(self, run_result: RunResult):
        super().__init__()
        self.run_result = run_result

    def compose(self) -> ComposeResult:
        yield RunResultSummary(self.run_result)
        language = self.run_result.guess_language()
        yield ListView(
            *[
                ListItem(FailedTest(test, language))
                for test in self.run_result.failed_tests
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
        self._set_test_output_visible(True)

    def action_hide_test_output(self) -> None:
        self._set_test_output_visible(False)

    def _set_test_output_visible(self, visible: bool) -> None:
        if focused := self.focused:
            if isinstance(focused, ListView):
                if list_item := focused.highlighted_child:
                    try:
                        collapsible = list_item.query_one(Collapsible)
                    except NoMatches:
                        pass
                    else:
                        collapsible.collapsed = not visible


def tui(run_result: RunResult):
    app = RunResultApp(run_result)
    app.run()


if __name__ == "__main__":
    tui(
        RunResult(
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
                    FailedTestRow(
                        file="file",
                        name="name",
                        passed=False,
                        flaky=False,
                        runs=1,
                        max_time=1,
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
