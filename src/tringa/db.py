from collections import namedtuple
from datetime import datetime
from typing import IO, Iterator, NamedTuple, Optional

import duckdb
import junitparser.xunit2 as jup

from tringa.github import Artifact


class TestResult(NamedTuple):
    # run-level fields
    run_id: str
    branch: str
    commit: str

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


def load_xml(artifact: Artifact, xml: IO[bytes], conn: duckdb.DuckDBPyConnection):
    for row in get_rows(artifact, xml):
        insert_row(conn, row)


def get_rows(artifact: Artifact, file: IO[bytes]) -> Iterator[TestResult]:
    xml = jup.JUnitXml.fromstring(file.read().decode())
    empty_result = namedtuple("ResultElem", ["message", "text"])(None, None)
    for test_suite in xml:
        for test_case in test_suite:
            # Passed test cases have no result. A failed/skipped test case will
            # typically have a single result, but the schema permits multiple.
            for result in test_case.result or [empty_result]:
                yield TestResult(
                    run_id=artifact["run_id"],
                    branch=artifact["branch"],
                    commit=artifact["commit"],
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
        INSERT INTO test (
            run_id,
            branch,
            commit,
            file,
            suite,
            suite_timestamp,
            suite_execution_time,
            name,
            classname,
            execution_time,
            passed,
            skipped,
            message,
            text
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        row,
    )


def create_schema(conn: duckdb.DuckDBPyConnection):
    conn.execute(
        """
        CREATE TABLE test (
            run_id VARCHAR,
            branch VARCHAR,
            commit VARCHAR,
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
