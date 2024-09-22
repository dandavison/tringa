"""
Our definition of a flaky test will probably become more sophisticated over
time. Our current working definition is:

> A test is flaky if it has failed on more than one branch.

This definition will give false positives if, for example, the test was
introduced in feature branch b, and then branch b' was created as a fork of b,
and it failed in both.

TODO: we would like the definition to capture "has failed on main".
"""

from collections import defaultdict

from tringa.db import DB
from tringa.queries import EmptyParams, Query

_query = Query[EmptyParams, tuple[str, str, bool, bool, str]](
    "select classname, name, passed, skipped, branch from test;"
).fetchall


def annotate(from_db: DB, to_db: DB):
    tests = _query(from_db, {})
    fail_branches, flaky = defaultdict(set), set()
    for classname, name, passed, skipped, branch in tests:
        key = (classname, name)
        if not passed and not skipped:
            fail_branches[key].add(branch)
            if len(fail_branches[key]) > 1:
                flaky.add(key)

    if any(flaky):
        to_db.connection.executemany(
            "UPDATE test SET flaky = true WHERE classname = ? AND name = ?", list(flaky)
        )
