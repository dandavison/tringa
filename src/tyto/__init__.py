from typing import IO, Iterator

import duckdb
import junitparser.junitparser as jup


def tyto(files: Iterator[IO[bytes]], conn: duckdb.DuckDBPyConnection):
    for file in files:
        for row in get_rows(file):
            insert_row(conn, row)


def get_rows(file: IO[bytes]) -> Iterator[tuple[str, str, str, str | None]]:
    for test_suite in jup.JUnitXml.fromstring(file.read().decode()):
        for test_case in test_suite:
            result = "Passed" if test_case.result is None else "Failed"
            stack_trace = None
            if isinstance(test_case.result, (jup.Error, jup.Failure)):
                stack_trace = test_case.result.text
            yield (test_suite.name, test_case.name, result, stack_trace)


def insert_row(conn: duckdb.DuckDBPyConnection, row: tuple):
    conn.execute(
        """
        INSERT INTO test_results (suite_name, case_name, result, stack_trace)
        VALUES (?, ?, ?, ?)
        """,
        row,
    )


def create_schema(conn: duckdb.DuckDBPyConnection):
    conn.execute(
        """
        CREATE TABLE test_results (
            suite_name VARCHAR,
            case_name VARCHAR,
            result VARCHAR,
            stack_trace VARCHAR
        )
        """
    )
