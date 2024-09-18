"""
A query is a function
(DB, Params) -> T
or
(DB, Params) -> list[T].
"""

from dataclasses import dataclass
from datetime import datetime
from textwrap import dedent
from typing import Any, Mapping, TypedDict

from tringa.db import DB
from tringa.models import PR, FailedTestRow, Run


@dataclass
class Query[P: Mapping[str, Any], R]:
    # TODO: types
    sql: str

    def fetchall(self, db: DB, params: P) -> list[R]:
        return db.connection.execute(self.sql.format(**params)).fetchall()

    def fetchone(self, db: DB, params: P) -> R:
        return db.fetchone(self.sql.format(**params))

    def fetchatom(self, db: DB, params: P) -> R:
        return db.fetchone(self.sql.format(**params))[0]

    def __post_init__(self):
        self.sql = dedent(self.sql).strip()


class EmptyParams(TypedDict):
    pass


count_test_results = Query[EmptyParams, int]("select count(*) from test;").fetchone


class FailedTestsInRunParams(TypedDict):
    repo: str
    run_id: str


_failed_tests_in_run = Query[FailedTestsInRunParams, FailedTestRow](
    """
    select file, name, passed, flaky, count(*) as runs, max(time) as max_time, max(text) as text from test
    where passed = false and skipped = false and run_id = '{run_id}' and repo = '{repo}'
    group by file, name, passed, flaky
    order by file, flaky desc, max_time desc;
    """
).fetchall


def failed_tests_in_run(db: DB, params: FailedTestsInRunParams) -> list[FailedTestRow]:
    return [FailedTestRow(*row) for row in _failed_tests_in_run(db, params)]


class LastRunIdParams(TypedDict):
    repo: str
    branch: str


_last_run = Query[LastRunIdParams, tuple[str, str, datetime]](
    """
    select repo, run_id, suite_timestamp from test
    where repo = '{repo}' and branch = '{branch}'
    order by suite_timestamp desc
    limit 1;
    """
).fetchone


def last_run(db: DB, pr: PR) -> Run:
    repo, run_id, time = _last_run(db, {"repo": pr.repo, "branch": pr.branch})
    return Run(repo=repo, id=run_id, time=time, pr=pr)
