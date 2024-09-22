"""
Our definition of a flaky test will probably become more sophisticated over
time. Our current working definition is:

> A test is flaky if it has failed at least once and it is present on more than
one branch.

TODO: This definition will give false positives if, for example, the test was
introduced in feature branch b, and then branch b' was created as a fork of b,
and it failed in both.
"""

from collections import defaultdict

from tringa.db import DB
from tringa.models import TestResult
from tringa.queries import EmptyParams, Query


def annotate(from_db: DB, to_db: DB):
    test_results = Query[TestResult, EmptyParams]("select * from test;").fetchall(
        from_db, {}
    )
    seen_branches, flaky = defaultdict(set), set()
    for tr in test_results:
        if tr.skipped:
            continue
        key = (tr.repo, tr.classname, tr.name)
        seen_branches[key].add(tr.branch)
        if not tr.passed and len(seen_branches[key]) > 1:
            flaky.add(key)

    if any(flaky):
        to_db.connection.executemany(
            "UPDATE test SET flaky = true WHERE repo = ? AND classname = ? AND name = ?",
            list(flaky),
        )
