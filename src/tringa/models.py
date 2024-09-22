from dataclasses import dataclass
from datetime import datetime
from typing import NamedTuple, Optional, Protocol


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

    def __rich__(self) -> str:
        return f"[link={self.url}]#{self.number} {self.title}[/link]"


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
            "pr": self.pr.__dict__,
        }


class TestResult(NamedTuple):
    artifact_name: str

    # run-level fields
    repo: str
    branch: str
    run_id: str
    sha: str

    # suite-level fields
    file: str
    suite: str
    suite_timestamp: datetime
    suite_time: float

    # test-level fields
    name: str  # Name of the test function
    classname: str  # Name of class or module containing the test function
    time: float
    passed: bool
    skipped: bool
    flaky: bool
    message: Optional[str]  # Failure message
    text: Optional[str]  # Stack trace or code context of failure


TreeSitterLanguageName = str  # TODO
