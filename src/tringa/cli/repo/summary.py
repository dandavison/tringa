from dataclasses import dataclass

from rich.console import Console, ConsoleOptions, RenderResult
from rich.table import Table
from rich.text import Text

from tringa.db import DB
from tringa.models import Serializable
from tringa.queries import EmptyParams, Query


@dataclass
class RepoSummary(Serializable):
    repo: str
    prs: int
    flaky_tests: int

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
                    "PRs",
                    Text(str(self.prs), style="bold"),
                )
                yield (
                    "Flaky tests",
                    Text(str(self.flaky_tests), style="bold"),
                )

            table = Table(show_header=False)
            for row in rows():
                table.add_row(*row)
            return table

        yield make_summary()


def make_repo_summary(db: DB, repo: str) -> RepoSummary:
    flaky_tests = Query[tuple[int], EmptyParams](
        """
    select count(*) from test
    where flaky = true;
    """
    ).fetchone(db, {})[0]
    prs = len(
        Query[tuple[str], EmptyParams](
            """
    select distinct(pr_number) from test;
    """,
        ).fetchall(db, {})
    )

    return RepoSummary(
        repo=repo,
        prs=prs,
        flaky_tests=flaky_tests,
    )
