from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import (
    Any,
    Iterable,
    Iterator,
    Optional,
    Sequence,
)

import duckdb
import pandas as pd

from tringa.exceptions import TringaQueryException
from tringa.models import TestResult
from tringa.msg import debug

CREATE_SCHEMA_SQL = """
CREATE TABLE test (
    repo VARCHAR,
    artifact VARCHAR,
    branch VARCHAR,
    run_id INT64,
    sha VARCHAR,
    pr INT64,
    pr_title VARCHAR,
    file VARCHAR,
    suite VARCHAR,
    suite_time TIMESTAMP,
    suite_duration FLOAT,
    classname VARCHAR,
    name VARCHAR,
    duration FLOAT,
    passed BOOLEAN,
    skipped BOOLEAN,
    flaky BOOLEAN,
    message VARCHAR,
    text VARCHAR,

    -- A run may have multiple run attempts. The artifact name typically includes
    -- the run attempt number, in order to avoid artifact name conflicts. However,
    -- GitHub does not expose the run attempt number in the metadata associated with
    -- an artifact, and we follow suite: i.e. we demand uniqueness on the following
    -- tuple, which means that multiple artifacts for the same run may not coexist
    -- in the table.
    PRIMARY KEY (repo, run_id, file, suite, classname, name),

    -- The following should be true also.
    -- UNIQUE (repo, artifact, file, suite, classname, name)
);
"""


@dataclass
class DB:
    connection: duckdb.DuckDBPyConnection
    path: Optional[Path]

    @staticmethod
    @contextmanager
    def _connect(path: Optional[Path]) -> Iterator[duckdb.DuckDBPyConnection]:
        yield duckdb.connect(str(path)) if path else duckdb.connect()

    def create_schema(self) -> None:
        self.connection.execute(CREATE_SCHEMA_SQL)

    def insert_rows(self, rows: Iterable[TestResult]) -> None:
        # Inserting columns from a dataframe is more efficient than inserting
        # rows from a SQL INSERT statement.
        n_rows = str(len(rows)) if isinstance(rows, Sequence) else "<iterator>"

        df = pd.DataFrame(rows)
        if df.empty:
            return
        debug(f"Inserting {n_rows} rows into {self}")
        # Sort by time so that rows from later run attempts (that match on the
        # uniqueness constraints) replace those from earlier run attempts.
        self.connection.execute(
            """
            INSERT OR REPLACE INTO test
            SELECT DISTINCT ON (repo, run_id, file, suite, classname, name) *
            FROM df
            ORDER BY repo, run_id, file, suite, classname, name, suite_time DESC
            """
        )

    def fetchone(self, sql: str) -> Any:
        rows = self.connection.execute(sql).fetchall()
        if not rows:
            raise TringaQueryException(f"Query returned no results:\n{sql}")
        if not len(rows) == 1:
            raise TringaQueryException(f"Query did not return a single row:\n{sql}")
        return rows[0]

    def __str__(self) -> str:
        return f"DuckDB({self.path})"


@dataclass
class DBConfig:
    path: Optional[Path]

    @contextmanager
    def connect(self) -> Iterator[DB]:
        new_db = not self.path or not self.path.exists()
        with DB._connect(self.path) as conn:
            db = DB(conn, self.path)
            if new_db:
                db.create_schema()
            yield db
