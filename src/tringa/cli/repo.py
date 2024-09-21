from typing import NoReturn, Optional

import typer

import tringa.cli.run
import tringa.repl
import tringa.tui.tui
from tringa import cli, scoped_db
from tringa.annotations import flaky as flaky
from tringa.db import DB
from tringa.models import RepoResult
from tringa.rich import print, print_json

app = typer.Typer(rich_markup_mode="rich")


@app.command()
def repl(repo: str, repl: Optional[tringa.repl.Repl]) -> NoReturn:
    with scoped_db.connect(cli.options.db_config, repo=repo) as db:
        tringa.repl.repl(db, repl)


@app.command()
def show(repo: str) -> None:
    with scoped_db.connect(cli.options.db_config, repo=repo) as db:
        result = _make_repo_result(db, repo)
        if cli.options.json:
            print_json(data=result.to_dict(), sort_keys=True)
        print(result)


@app.command()
def sql(repo: str, query: str):
    """
    Execute a SQL query against the database.
    """
    with scoped_db.connect(cli.options.db_config, repo=repo) as db:
        rel = db.connection.sql(query)
        if cli.options.json:
            print(rel.df().to_json(orient="records", indent=2))
        else:
            print(rel)


def _make_repo_result(db: DB, repo: str) -> RepoResult:
    return RepoResult(
        repo=repo,
        failed_tests=[],
    )
