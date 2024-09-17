from dataclasses import dataclass
from datetime import datetime
from typing import NamedTuple

from rich.console import Console, ConsoleOptions, RenderResult

from tringa.rich import render_run_result


@dataclass
class Repo:
    nameWithOwner: str


@dataclass
class PR:
    headRefName: str
    headRepository: dict
    headRepositoryOwner: dict
    url: str
    title: str
    number: int

    @property
    def repo(self) -> str:
        return f"{self.headRepositoryOwner['login']}/{self.headRepository['name']}"

    @property
    def branch(self) -> str:
        return self.headRefName


@dataclass
class Run:
    repo: str
    id: str
    time: datetime
    pr: PR

    def url(self) -> str:
        return f"https://github.com/{self.repo}/actions/runs/{self.id}"

    def to_dict(self) -> dict:
        return {
            "repo": self.repo,
            "id": self.id,
            "time": self.time.isoformat(),
            "pr": self.pr.__dict__ if self.pr is not None else None,
        }


class FailedTestRow(NamedTuple):
    file: str
    name: str
    passed: bool
    flaky: bool
    runs: int
    max_time: float
    text: str


@dataclass
class RunResult:
    run: Run
    failed_tests: list[FailedTestRow]

    def to_dict(self) -> dict:
        return {
            "run": self.run.to_dict(),
            "failed_tests": self.failed_tests,
        }

    def __rich_console__(
        self, console: Console, options: ConsoleOptions
    ) -> RenderResult:
        return render_run_result(self)
