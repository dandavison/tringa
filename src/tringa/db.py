"""
We currently support both duckdb and sqlite. While there's no technical reason
to use duckdb for this application, it has a nice SQL REPL, and its Python REPL
has several useful features. However, a SQL REPL is available for sqlite
(litecli) via Python packaging, whereas the duckdb CLI must be installed
separately. These considerations have led to this module abstracting over the
two backends, which would otherwise be undesirable.
"""

import sqlite3
from abc import ABC, abstractmethod
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import (
    Generic,
    Iterable,
    Iterator,
    NamedTuple,
    Optional,
    Sequence,
    TypeVar,
)

import duckdb

from tringa.msg import debug


class TestResult(NamedTuple):
    artifact_name: str

    # run-level fields
    run_id: str
    branch: str
    sha: str

    # suite-level fields
    file: str
    suite: str
    suite_timestamp: datetime
    suite_time: float

    # test-level fields
    name: str  # Name of the test function
    classname: str  # Name of class or module containing the test function
    time: float
    passed: bool
    skipped: bool
    message: Optional[str]  # Failure message
    text: Optional[str]  # Stack trace or code context of failure


CREATE_SCHEMA_SQL = """
CREATE TABLE test (
    artifact_name VARCHAR,
    run_id VARCHAR,
    branch VARCHAR,
    sha VARCHAR,
    file VARCHAR,
    suite VARCHAR,
    suite_timestamp TIMESTAMP,
    suite_time FLOAT,
    name VARCHAR,
    classname VARCHAR,
    time FLOAT,
    passed BOOLEAN,
    skipped BOOLEAN,
    message VARCHAR,
    text VARCHAR
);
"""

CREATE_INDEX_SQL = """
CREATE INDEX idx_artifact_name ON test(artifact_name);
"""

INSERT_ROWS_SQL = """
INSERT INTO test (
    artifact_name,
    run_id,
    branch,
    sha,
    file,
    suite,
    suite_timestamp,
    suite_time,
    name,
    classname,
    time,
    passed,
    skipped,
    message,
    text
)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
"""


class DBType(StrEnum):
    DUCKDB = "duckdb"
    SQLITE = "sqlite"


@dataclass
class DBConfig:
    db_type: DBType
    path: Optional[Path]

    @contextmanager
    def connect(self) -> Iterator["DB"]:
        new_db = not self.path or not self.path.exists()
        cls = SqliteDB if self.db_type == DBType.SQLITE else DuckDB
        with cls._connect(self.path) as conn:
            db = cls(conn, self.path)  # type: ignore
            if new_db:
                db.create_schema()
            yield db


# In sqlite you always execute sql using a `connection.cursor()`, but you call
# commit() on the `connection`. In duckdb you can use the `connection` to
# execute sql (but should use a connection.cursor() in a thread).
Con = TypeVar("Con", bound=sqlite3.Connection | duckdb.DuckDBPyConnection)
Cur = TypeVar("Cur", bound=sqlite3.Cursor | duckdb.DuckDBPyConnection)


@dataclass
class DB(Generic[Con, Cur], ABC):
    connection: Con
    path: Optional[Path]

    @staticmethod
    @abstractmethod
    @contextmanager
    def _connect(path: Optional[Path]) -> Iterator[Con]: ...

    @abstractmethod
    def cursor(self) -> Cur: ...

    @abstractmethod
    def sql(self, sql: str) -> str: ...

    def create_schema(self) -> None:
        debug(f"{self}: creating schema")
        self.cursor().execute(CREATE_SCHEMA_SQL)
        self.cursor().execute(CREATE_INDEX_SQL)

    def insert_rows(self, rows: Iterable[TestResult]) -> None:
        n_rows = str(len(rows)) if isinstance(rows, Sequence) else "<iterator>"
        debug(f"Inserting {n_rows} rows into {self}")
        self.cursor().executemany(INSERT_ROWS_SQL, rows)

    def __str__(self) -> str:
        return f"DB(connection={self.connection}, path={self.path})"


@dataclass
class SqliteDB(DB[sqlite3.Connection, sqlite3.Cursor]):
    connection: sqlite3.Connection
    path: Optional[Path]

    @staticmethod
    @contextmanager
    def _connect(path: Optional[Path]) -> Iterator[sqlite3.Connection]:
        yield sqlite3.connect(str(path or ":memory:"))

    def cursor(self) -> sqlite3.Cursor:
        return self.connection.cursor()

    def sql(self, sql: str) -> str:
        return str(self.cursor().execute(sql).fetchall())

    def insert_rows(self, rows: Iterable[TestResult]) -> None:
        super().insert_rows(rows)
        self.connection.commit()


@dataclass
class DuckDB(DB[duckdb.DuckDBPyConnection, duckdb.DuckDBPyConnection]):
    connection: duckdb.DuckDBPyConnection
    path: Optional[Path]

    @staticmethod
    @contextmanager
    def _connect(path: Optional[Path]) -> Iterator[duckdb.DuckDBPyConnection]:
        yield duckdb.connect(str(path)) if path else duckdb.connect()

    def cursor(self) -> duckdb.DuckDBPyConnection:
        return self.connection

    def sql(self, sql: str) -> str:
        return str(self.connection.sql(sql))
