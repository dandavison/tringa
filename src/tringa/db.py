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
    artifact VARCHAR,
    repo VARCHAR,
    branch VARCHAR,
    run_id INT64,
    sha VARCHAR,
    pr INT64,
    pr_title VARCHAR,
    file VARCHAR,
    suite VARCHAR,
    suite_time TIMESTAMP,
    suite_duration FLOAT,
    name VARCHAR,
    classname VARCHAR,
    duration FLOAT,
    passed BOOLEAN,
    skipped BOOLEAN,
    flaky BOOLEAN,
    message VARCHAR,
    text VARCHAR
);
"""

CREATE_INDEX_SQL = """
CREATE INDEX idx_artifact ON test(artifact)
"""

INSERT_ROWS_SQL = """
INSERT INTO test (
    artifact,
    repo,
    branch,
    run_id,
    sha,
    pr,
    pr_title,
    file,
    suite,
    suite_time,
    suite_duration,
    name,
    classname,
    duration,
    passed,
    skipped,
    flaky,
    message,
    text
)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
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
        self.connection.execute(CREATE_INDEX_SQL)

    def insert_rows(self, rows: Iterable[TestResult]) -> None:
        # Inserting columns from a dataframe is more efficient than inserting
        # rows from a SQL INSERT statement.
        n_rows = str(len(rows)) if isinstance(rows, Sequence) else "<iterator>"
        df = pd.DataFrame(rows)
        if df.empty:
            return
        debug(f"Inserting {n_rows} rows into {self}")
        self.connection.execute("insert into test select * from df")

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
