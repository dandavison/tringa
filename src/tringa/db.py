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
    Self,
    Sequence,
    TypeVar,
)

import duckdb
from xdg_base_dirs import xdg_data_home

from tringa.log import debug


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


class DBPersistence(StrEnum):
    PERSISTENT = "persistent"
    EPHEMERAL = "ephemeral"


@dataclass
class DBConfig:
    db_persistence: DBPersistence
    db_type: DBType
    path: Optional[Path] = None

    def __post_init__(self) -> None:
        if self.db_persistence == DBPersistence.PERSISTENT:
            dir = Path(xdg_data_home()) / "tringa"
            dir.mkdir(parents=True, exist_ok=True)
            self.path = dir / f"tringa.{self.db_type.value}"


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

    @contextmanager
    @classmethod
    def connect(cls, db_config: DBConfig) -> Iterator[Self]:
        new_db = not db_config.path or not db_config.path.exists()
        with cls._connect(db_config.path) as conn:
            db = cls(conn, db_config.path)
            if new_db:
                db.create_schema()
            yield db

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
