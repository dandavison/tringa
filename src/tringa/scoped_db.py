import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import (
    Iterator,
    Optional,
)

from tringa.annotations import flaky
from tringa.artifact import fetch_and_load_new_artifacts
from tringa.db import DB, DBConfig


@contextmanager
def connect(
    dbconfig: DBConfig, repo: str, run_id: Optional[str] = None
) -> Iterator[DB]:
    with dbconfig.connect() as db:
        # We fetch for the entire repo, even when the requested scope is run, in
        # order to collect information across branches used to identify flakes.
        fetch_and_load_new_artifacts(db, [repo])

        query = f"select * from test where repo = '{repo}'"
        if run_id:
            query += f" and run_id = '{run_id}'"

        df = db.connection.execute(query).df()

        with tempfile.NamedTemporaryFile() as f:
            path = Path(f.name)
            path.unlink()
            with DBConfig(path).connect() as db2:
                db2.connection.execute("insert into test select * from df")
                flaky.annotate(db.connection, db2.connection)
                yield db2
