import zipfile
from collections import namedtuple
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import IO, Iterator, NamedTuple, Optional

import duckdb
import junitparser.xunit2 as jup
from rich.progress import track

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


def load_xml_from_zip_file_artifacts(
    conn: duckdb.DuckDBPyConnection,
    artifacts: Iterator[tuple[Artifact, bytes]],
):
    # Trade memory footprint for a progress bar
    for artifact, zip_file in track(list(artifacts), description="Writing XML to DB"):
        for file in get_xml_files_from_zip_file(BytesIO(zip_file)):
            load_xml(artifact, file.read().decode(), file.name, conn)


def get_xml_files_from_zip_file(file: Path | IO[bytes]) -> Iterator[IO[bytes]]:
    with zipfile.ZipFile(file) as zip_file:
        for file_name in zip_file.namelist():
            if file_name.endswith(".xml"):
                with zip_file.open(file_name) as f:
                    yield f


def load_xml(
    artifact: Artifact, xml: str, file_name: str, conn: duckdb.DuckDBPyConnection
):
    for row in get_rows(artifact, xml, file_name):
        insert_row(conn, row)


def get_rows(artifact: Artifact, xml: str, file_name: str) -> Iterator[TestResult]:
    empty_result = namedtuple("ResultElem", ["message", "text"])(None, None)
    for test_suite in jup.JUnitXml.fromstring(xml):
        for test_case in test_suite:
            # Passed test cases have no result. A failed/skipped test case will
            # typically have a single result, but the schema permits multiple.
            for result in test_case.result or [empty_result]:
                yield TestResult(
                    run_id=artifact["run_id"],
                    branch=artifact["branch"],
                    commit=artifact["commit"],
                    file=file_name,
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
