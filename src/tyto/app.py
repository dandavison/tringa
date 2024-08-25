from collections import namedtuple
from datetime import datetime
from typing import IO, Iterator, NamedTuple, Optional

import duckdb
import junitparser.xunit2 as jup


class TestResult(NamedTuple):
    # suite-level fields
    file: str
    suite: str
    suite_timestamp: datetime
    suite_execution_time: float

    # test-level fields
    name: str  # Name of the test function
    classname: str  # Name of class or module containing the test function
    execution_time: float
    passed: bool
    skipped: bool
    message: Optional[str]  # Failure message
    text: Optional[str]  # Stack trace or code context of failure


def tyto(files: Iterator[IO[bytes]], conn: duckdb.DuckDBPyConnection):
    for file in files:
        for row in get_rows(file):
            insert_row(conn, row)


empty_result = namedtuple("ResultElem", ["message", "text"])(None, None)


def get_rows(file: IO[bytes]) -> Iterator[TestResult]:
    xml = jup.JUnitXml.fromstring(file.read().decode())
    for test_suite in xml:
        for test_case in test_suite:
            # Passed test cases have no result. A failed/skipped test case will
            # typically have a single result, but the schema permits multiple.
            for result in test_case.result or [empty_result]:
                yield TestResult(
                    file=file.name,
                    suite=test_suite.name,
                    suite_timestamp=datetime.fromisoformat(test_suite.timestamp),
                    suite_execution_time=test_suite.time,
                    name=test_case.name,
                    classname=test_case.classname,
                    execution_time=test_case.time,
                    passed=test_case.is_passed,
                    skipped=test_case.is_skipped,
                    message=result.message,
                    text=result.text,
                )


def insert_row(conn: duckdb.DuckDBPyConnection, row: TestResult):
    conn.execute(
        """
        INSERT INTO test (file, suite, suite_timestamp, suite_execution_time, name, classname, execution_time, passed, skipped, message, text)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        row,
    )


def create_schema(conn: duckdb.DuckDBPyConnection):
    conn.execute(
        """
        CREATE TABLE test (
            file VARCHAR,
            suite VARCHAR,
            suite_timestamp TIMESTAMP,
            suite_execution_time FLOAT,
            name VARCHAR,
            classname VARCHAR,
            execution_time FLOAT,
            passed BOOLEAN,
            skipped BOOLEAN,
            message VARCHAR,
            text VARCHAR
        )
        """
    )
