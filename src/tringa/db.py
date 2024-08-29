import os
from collections import namedtuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from io import BytesIO
from typing import Iterator, NamedTuple, Optional
from zipfile import ZipFile

import duckdb
import junitparser.xunit2 as jup
from rich import progress

from tringa.github import Artifact
from tringa.log import debug


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


def load_xml_from_zip_file_artifacts(
    conn: duckdb.DuckDBPyConnection,
    artifacts: Iterator[tuple[Artifact, bytes]],
):
    def parse_and_load(artifact: Artifact, zip_file: ZipFile, file_name: str):
        debug("parse_and_load", artifact["name"], file_name)
        rows = get_rows(artifact, zip_file.read(file_name).decode(), file_name)
        insert_rows(conn.cursor(), list(rows))

    zip_files = []
    futures = []
    with ThreadPoolExecutor(max_workers=os.cpu_count() or 1) as executor:
        for artifact, zip_bytes in artifacts:
            zip_file = ZipFile(BytesIO(zip_bytes))
            for file_name in zip_file.namelist():
                if file_name.endswith(".xml"):
                    futures.append(
                        executor.submit(parse_and_load, artifact, zip_file, file_name)
                    )
            zip_files.append(zip_file)
        progress.track((f.result() for f in as_completed(futures)), total=len(futures))
    for zip_file in zip_files:
        zip_file.close()


def get_rows(artifact: Artifact, xml: str, file_name: str) -> Iterator[TestResult]:
    empty_result = namedtuple("ResultElem", ["message", "text"])(None, None)
    for test_suite in jup.JUnitXml.fromstring(xml):
        for test_case in test_suite:
            # Passed test cases have no result. A failed/skipped test case will
            # typically have a single result, but the schema permits multiple.
            for result in test_case.result or [empty_result]:
                yield TestResult(
                    artifact_name=artifact["name"],
                    run_id=artifact["run_id"],
                    branch=artifact["branch"],
                    commit=artifact["commit"],
                    file=file_name,
                    suite=test_suite.name,
                    suite_timestamp=datetime.fromisoformat(test_suite.timestamp),
                    suite_time=test_suite.time,
                    name=test_case.name,
                    classname=test_case.classname,
                    time=test_case.time,
                    passed=test_case.is_passed,
                    skipped=test_case.is_skipped,
                    message=result.message,
                    text=result.text,
                )


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


def create_schema(conn: duckdb.DuckDBPyConnection):
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
