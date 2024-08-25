from io import BytesIO

import duckdb
import pytest

from tyto import parse_junit_xml


@pytest.fixture
def db_connection():
    conn = duckdb.connect(":memory:")
    conn.execute("""
        CREATE TABLE test_results (
            suite_name VARCHAR,
            case_name VARCHAR,
            result VARCHAR
        )
    """)
    yield conn
    conn.close()


def test_parse_junit_xml_passing(db_connection):
    xml_content = """
    <testsuite name="TestSuite1">
        <testcase name="test_passing" />
    </testsuite>
    """
    parse_junit_xml(BytesIO(xml_content.encode()), db_connection)
    result = db_connection.execute("SELECT * FROM test_results").fetchall()
    assert len(result) == 1
    assert result[0] == ("TestSuite1", "test_passing", "Passed")


def test_parse_junit_xml_failing(db_connection):
    xml_content = """
    <testsuite name="TestSuite1">
        <testcase name="test_failing">
            <failure message="Test failed" />
        </testcase>
    </testsuite>
    """
    parse_junit_xml(BytesIO(xml_content.encode()), db_connection)
    result = db_connection.execute("SELECT * FROM test_results").fetchall()
    assert len(result) == 1
    assert result[0] == ("TestSuite1", "test_failing", "Failed")
