from datetime import datetime

from textual.app import App, ComposeResult, RenderResult
from textual.widgets import Static

from tringa.cli.pr import RunResult
from tringa.models import PR, FailedTestRow, Run


class ResultWidget(Static):
    def __init__(self, run_result: RunResult):
        super().__init__()
        self.run_result = run_result

    def render(self) -> RenderResult:
        return self.run_result


class MyApp(App):
    CSS_PATH = "./layout.tcss"

    def __init__(self, run_result: RunResult):
        super().__init__()
        self.run_result = run_result

    def compose(self) -> ComposeResult:
        yield ResultWidget(self.run_result)


def tui(run_result: RunResult):
    app = MyApp(run_result)
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
