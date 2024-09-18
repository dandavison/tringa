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
from typing import cast

from duckdb import DuckDBPyConnection


def annotate(conn: DuckDBPyConnection):
    tests = conn.execute("select classname, name, passed, branch from test").fetchall()
    tests = cast(list[tuple[str, str, bool, str]], tests)
    fail_branches, flaky = defaultdict(set), set()
    for classname, name, passed, branch in tests:
        key = (classname, name)
        if not passed:
            fail_branches[key].add(branch)
            if len(fail_branches[key]) > 1:
                flaky.add(key)

    if any(flaky):
        # TODO: are we really going to write computed values to the db? It might be
        # nice to add the annotations in some way that is not persisted.
        conn.executemany(
            "UPDATE test SET flaky = true WHERE classname = ? AND name = ?", list(flaky)
        )
