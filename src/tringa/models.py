from dataclasses import dataclass
from datetime import datetime
from typing import Literal, NamedTuple, Optional, Protocol, runtime_checkable


@runtime_checkable
class Serializable(Protocol):
    def to_dict(self) -> dict: ...


@dataclass
class StatusCheck:
    """
    E.g.
    {
      "__typename": "CheckRun",
      "completedAt": "0001-01-01T00:00:00Z",
      "conclusion": "",
      "detailsUrl": "https://github.com/temporalio/sdk-python/actions/runs/10890746589/job/30849903991",
      "name": "build-lint-test (3.8, ubuntu-latest)",
      "startedAt": "2024-09-30T11:10:14Z",
      "status": "IN_PROGRESS",
      "workflowName": "Continuous Integration"
    }
    """

    conclusion: str
    name: str
    status: Literal["IN_PROGRESS", "COMPLETED"]
    workflow_name: str

    def to_dict(self) -> dict:
        return {
            "conclusion": self.conclusion,
            "name": self.name,
            "status": self.status,
            "workflow_name": self.workflow_name,
        }

    def __rich__(self) -> str:
        match self.conclusion:
            case "SUCCESS":
                color = "green"
            case "FAILURE":
                color = "red"
            case "IN_PROGRESS":
                color = "yellow"
            case _:
                color = "gray"
        return f"[{color}]{self.name} {self.status} {self.conclusion}[/{color}]"


@dataclass
class PR:
    repo: str
    number: int
    title: str
    branch: str
    status_checks: list[StatusCheck]

    @property
    def url(self) -> str:
        return f"https://github.com/{self.repo}/pull/{self.number}"

    def __rich__(self) -> str:
        return f"[link={self.url}]#{self.number} {self.title}[/link]"


@dataclass
class Run(Serializable):
    repo: str
    id: int
    started_at: datetime
    branch: str
    sha: str
    pr: Optional[PR]

    @property
    def url(self) -> str:
        return f"https://github.com/{self.repo}/actions/runs/{self.id}"

    def to_dict(self) -> dict:
        return {
            "repo": self.repo,
            "id": self.id,
            "started_at": self.started_at.isoformat(),
            "pr": self.pr.__dict__ if self.pr is not None else None,
        }

    def title(self) -> str:
        t = f"{self.repo} #{self.id}"
        if self.pr is not None:
            t += f" {self.pr.title}"
        return t


class TestResult(NamedTuple):
    # run-level fields
    repo: str
    artifact: str
    branch: str
    run_id: int
    sha: str
    pr: Optional[int]
    pr_title: Optional[str]

    # suite-level fields
    file: str
    suite: str
    suite_time: datetime
    suite_duration: float

    # test-level fields
    classname: str  # Name of class or module containing the test function
    name: str  # Name of the test function
    duration: float
    passed: bool
    skipped: bool
    flaky: bool
    message: Optional[str]  # Failure message
    text: Optional[str]  # Stack trace or code context of failure

    def __str__(self) -> str:
        return f"{self.__class__.__name__}({self.repo}, {self.artifact}, {self.branch}, {self.run_id}, {self.file}, {self.name})"

    def __repr__(self) -> str:
        return self.__str__()

    def make_pr(self) -> Optional[PR]:
        if self.pr is None or self.pr_title is None:
            return None
        return PR(
            repo=self.repo,
            number=self.pr,
            title=self.pr_title,
            branch=self.branch,
            status_checks=[],
        )


TreeSitterLanguageName = str  # TODO
