from dataclasses import dataclass

from rich.console import Console, ConsoleOptions, RenderResult
from rich.table import Table
from rich.text import Text

from tringa.models import Serializable


@dataclass
class RepoSummary(Serializable):
    repo: str
    flaky_tests: list[tuple[str]]

    def to_dict(self) -> dict:
        return {
            "repo": self.repo,
            "flaky_tests": self.flaky_tests,
        }

    def __rich_console__(
        self, console: Console, options: ConsoleOptions
    ) -> RenderResult:
        def make_summary():
            def rows():
                yield (
                    "Repo",
                    f"[link=https://github.com/{self.repo}]{self.repo}[/link]",
                )
                yield (
                    "Flaky tests",
                    Text(str(len(self.flaky_tests)), style="bold"),
                )

            table = Table(show_header=False)
            for row in rows():
                table.add_row(*row)
            return table

        yield make_summary()
