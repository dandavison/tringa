"""
A query is a function
(DB, Params) -> T
or
(DB, Params) -> list[T].
"""

import typing
from dataclasses import dataclass
from textwrap import dedent
from typing import Any, Mapping, TypedDict

from tringa.db import DB
from tringa.models import PR, Run, TestResult


class EmptyParams(TypedDict):
    pass


@dataclass
class Query[R, P: Mapping[str, Any]]:
    # If the requested return type R is tuple, then we return the raw tuple(s).
    # Otherwise, the only permitted types for R are namedtuple or dataclass, and
    # the constructors takes tuple content as positional arguments.
    sql: str

    @property
    def _result_cls(self) -> type[R]:
        cls = getattr(self, "__orig_class__", None)
        assert cls is not None, (
            "__orig_class__ not present. "
            "It is an undocumented implementation detail, but present from Python 3.5.3 to 3.12.5 at least."
        )
        (result_cls, _) = typing.get_args(cls)
        return result_cls

    def fetchall(self, db: DB, params: P) -> list[R]:
        tuples = db.connection.execute(self.sql.format(**params)).fetchall()
        if typing.get_origin(self._result_cls) is tuple:
            return tuples
        return [self._result_cls(*row) for row in tuples]

    def fetchone(self, db: DB, params: P) -> R:
        _tuple = db.fetchone(self.sql.format(**params))
        if typing.get_origin(self._result_cls) is tuple:
            return _tuple
        return self._result_cls(*_tuple)

    def __post_init__(self):
        self.sql = dedent(self.sql).strip()


failed_test_results = Query[TestResult, EmptyParams](
    """
    select * from test
    where passed = false and skipped = false
    order by file, flaky desc, time desc;
    """
).fetchall


class LastRunParams(TypedDict):
    repo: str
    branch: str


_last_run = Query[TestResult, LastRunParams](
    """
    select * from test
    where repo = '{repo}' and branch = '{branch}'
    order by suite_timestamp desc
    limit 1;
    """
).fetchone


def last_run(db: DB, pr: PR) -> Run:
    # Hack: add pr to result
    tr = _last_run(db, {"repo": pr.repo, "branch": pr.branch})
    return Run(repo=tr.repo, id=tr.run_id, time=tr.suite_timestamp, pr=pr)
