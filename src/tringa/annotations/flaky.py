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
from tringa.queries import EmptyParams, Query

_query = Query[tuple[str, str, bool, bool, str], EmptyParams](
    "select classname, name, passed, skipped, branch from test;"
).fetchall


def annotate(from_db: DB, to_db: DB):
    tests = _query(from_db, {})
    seen_branches, flaky = defaultdict(set), set()
    for classname, name, passed, skipped, branch in tests:
        if skipped:
            continue
        key = (classname, name)
        seen_branches[key].add(branch)
        if not passed and len(seen_branches[key]) > 1:
            flaky.add(key)

    if any(flaky):
        to_db.connection.executemany(
            "UPDATE test SET flaky = true WHERE classname = ? AND name = ?", list(flaky)
        )
