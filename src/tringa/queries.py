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
from tringa.models import PR, Run, TestResult


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


_failed_tests = Query[EmptyParams, TestResult](
    """
    select * from test
    where passed = false and skipped = false
    order by file, flaky desc, time desc;
    """
).fetchall


def failed_tests(db: DB) -> list[TestResult]:
    return [TestResult(*row) for row in _failed_tests(db, {})]


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
