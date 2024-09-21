from dataclasses import dataclass
from datetime import datetime
from typing import NamedTuple, Optional, Protocol

from rich.console import Console, ConsoleOptions, RenderResult

from tringa import rich


class Serializable(Protocol):
    def to_dict(self) -> dict: ...


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
class Run(Serializable):
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


TreeSitterLanguageName = str  # TODO


@dataclass
class RepoResult(Serializable):
    repo: str
    failed_tests: list[FailedTestRow]

    def to_dict(self) -> dict:
        return {
            "repo": self.repo,
            "failed_tests": self.failed_tests,
        }

    def __rich_console__(
        self, console: Console, options: ConsoleOptions
    ) -> RenderResult:
        return rich.render_repo_result(self)


@dataclass
class RunResult(Serializable):
    run: Run
    failed_tests: list[FailedTestRow]

    def to_dict(self) -> dict:
        return {
            "run": self.run.to_dict(),
            "failed_tests": self.failed_tests,
        }

    def guess_language(self) -> Optional[TreeSitterLanguageName]:
        extensions = {
            "c": "c",
            "cpp": "cpp",
            "go": "go",
            "h": "c",
            "hpp": "cpp",
            "java": "java",
            "js": "javascript",
            "py": "python",
            "rs": "rust",
            "ts": "typescript",
        }
        candidates = {
            lang
            for ext, lang in extensions.items()
            # Look for apparent file-path-with-line-number in the test output
            if any(f".{ext}:" in t.text for t in self.failed_tests)
        }
        if len(candidates) == 1:
            return candidates.pop()
        else:
            return None

    def __rich_console__(
        self, console: Console, options: ConsoleOptions
    ) -> RenderResult:
        return rich.render_run_result(self)
