from contextlib import contextmanager
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import NamedTuple, Optional

import duckdb
from xdg_base_dirs import xdg_data_home

from tringa.log import info


class TestResult(NamedTuple):
    artifact_name: str

    # run-level fields
    run_id: str
    branch: str
    commit: str

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


class DBPersistence(StrEnum):
    PERSISTENT = "persistent"
    EPHEMERAL = "ephemeral"


@contextmanager
def connection(db_type: DBPersistence):
    db = ":memory:" if db_type == DBPersistence.EPHEMERAL else str(_get_db_path())
    info(f"Using database: {db}")
    with duckdb.connect(db) as conn:
        if db_type == DBPersistence.EPHEMERAL:
            _create_schema(conn)
        yield conn


def _get_db_path() -> Path:
    dir = Path(xdg_data_home()) / "tringa"
    dir.mkdir(parents=True, exist_ok=True)
    path = dir / "tringa.duckdb"
    if not path.exists():
        with duckdb.connect(str(path)) as conn:
            _create_schema(conn)
    return path


def insert_rows(conn: duckdb.DuckDBPyConnection, rows: list[TestResult]):
    conn.executemany(
        """
        INSERT INTO test (
            artifact_name,
            run_id,
            branch,
            commit,
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
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )


def _create_schema(conn: duckdb.DuckDBPyConnection):
    conn.execute(
        """
        CREATE TABLE test (
            artifact_name VARCHAR,
            run_id VARCHAR,
            branch VARCHAR,
            commit VARCHAR,
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
        )
        """
    )
    conn.execute(
        """
    CREATE INDEX idx_artifact_name ON test(artifact_name);
        """
    )
