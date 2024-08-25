from io import BytesIO

import duckdb
import pytest

from tyto.app import create_schema, load_xml


def test_1():
    assert 1 == 1


def test_2():
    assert 1 == 2


@pytest.mark.skip("skip")
def test_3():
    assert 1 == 3


@pytest.fixture
def db_connection():
    conn = duckdb.connect(":memory:")
    create_schema(conn)
    yield conn
    conn.close()


def test_parse_junit_xml_passing(db_connection: duckdb.DuckDBPyConnection):
    xml_content = """
    <testsuite name="TestSuite1">
        <testcase name="test_passing" />
    </testsuite>
    """
    load_xml(BytesIO(xml_content.encode()), db_connection)
    result = db_connection.execute("SELECT * FROM test_results").fetchall()
    assert len(result) == 1
    assert result[0] == ("TestSuite1", "test_passing", "Passed")


def test_parse_junit_xml_failing(db_connection: duckdb.DuckDBPyConnection):
    xml_content = """
    <testsuite name="TestSuite1">
        <testcase name="test_failing">
            <failure message="Test failed" />
        </testcase>
    </testsuite>
    """
    load_xml(BytesIO(xml_content.encode()), db_connection)
    result = db_connection.execute("SELECT * FROM test_results").fetchall()
    assert len(result) == 1
    assert result[0] == ("TestSuite1", "test_failing", "Failed")
