from dataclasses import dataclass

from rich.console import Console, ConsoleOptions, RenderResult

from tringa.cli import reports
from tringa.models import StatusCheck


@dataclass
class Report(reports.Report):
    status_checks: list[StatusCheck]

    def to_dict(self) -> dict:
        return {
            "status_checks": [t.to_dict() for t in self.status_checks],
        }

    def __rich_console__(
        self, console: Console, options: ConsoleOptions
    ) -> RenderResult:
        for status_check in sorted(self.status_checks, key=lambda x: x.name):
            yield status_check


def make_report(status_checks: list[StatusCheck]) -> Report:
    return Report(status_checks=status_checks)
