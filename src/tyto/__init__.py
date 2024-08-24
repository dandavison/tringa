import sys
import zipfile
from typing import IO

import duckdb
from junitparser.junitparser import JUnitXml


def parse_junit_xml(file: IO[bytes], conn: duckdb.DuckDBPyConnection) -> None:
    junit_xml = JUnitXml.fromstring(file.read().decode())

    for test_suite in junit_xml:
        for test_case in test_suite:
            conn.execute(
                """
                INSERT INTO test_results (suite_name, case_name, result)
                VALUES (?, ?, ?)
                """,
                (
                    test_suite.name,
                    test_case.name,
                    "Passed" if test_case.result is None else "Failed",
                ),
            )


def parse_junit_xmls(
    zip_file: zipfile.ZipFile, conn: duckdb.DuckDBPyConnection
) -> None:
    for file_name in zip_file.namelist():
        if file_name.endswith(".xml"):
            with zip_file.open(file_name) as f:
                parse_junit_xml(f, conn)


if __name__ == "__main__":
    conn = duckdb.connect(":memory:")
    conn.execute(
        """
        CREATE TABLE test_results (
            suite_name VARCHAR,
            case_name VARCHAR,
            result VARCHAR
        )
        """
    )

    parse_junit_xmls(zipfile.ZipFile(sys.argv[1]), conn)

    # Example query to show results
    result = conn.execute("SELECT * FROM test_results").fetchall()
    for row in result:
        print(row)

    conn.close()
