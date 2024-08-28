import os
from collections import namedtuple
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from datetime import datetime
from io import BytesIO
from typing import Iterator, NamedTuple, Optional
from zipfile import ZipFile

import duckdb
import junitparser.xunit2 as jup
from rich import progress

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
    def parse_and_load(artifact: Artifact, zip_file: ZipFile, file_name: str):
        rows = get_rows(artifact, zip_file.read(file_name).decode(), file_name)
        insert_rows(conn.cursor(), list(rows))

    def submit_jobs() -> Iterator[Future]:
        with ThreadPoolExecutor(max_workers=os.cpu_count() or 1) as executor:
            for artifact, zip_bytes in artifacts:
                with ZipFile(BytesIO(zip_bytes)) as zip_file:
                    for file_name in zip_file.namelist():
                        if file_name.endswith(".xml"):
                            yield executor.submit(
                                parse_and_load, artifact, zip_file, file_name
                            )

    jobs = list(submit_jobs())
    progress.track(as_completed(jobs), total=len(jobs))


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


def insert_rows(conn: duckdb.DuckDBPyConnection, rows: list[TestResult]):
    conn.executemany(
        """
        INSERT INTO test (
            run_id, branch, commit, file, suite, suite_timestamp, suite_execution_time,
            name, classname, execution_time, passed, skipped, message, text
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
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
