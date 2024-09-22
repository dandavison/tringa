from dataclasses import dataclass
from datetime import datetime
from typing import NamedTuple, Optional, Protocol, runtime_checkable


@runtime_checkable
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

    @property
    def pr(self) -> PR:
        login, repo = self.repo.split("/")
        number = 99999
        return PR(
            headRefName=self.branch,
            headRepository={
                "name": repo,
                "login": login,
            },
            headRepositoryOwner={
                "name": repo,
                "login": login,
            },
            url=f"https://github.com/{self.repo}/pull/{number}",
            title=f"PR: {self.branch}",
            number=number,
        )

    def __str__(self) -> str:
        return f"{self.__class__.__name__}({self.artifact_name}, {self.repo}, {self.branch}, {self.run_id}, {self.file}, {self.name})"

    def __repr__(self) -> str:
        return self.__str__()


TreeSitterLanguageName = str  # TODO
