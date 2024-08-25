import sys
import zipfile
from pathlib import Path

import duckdb

from tyto import parse_junit_xml, parse_junit_xmls


def tyto(file_path, conn):
    if file_path.suffix.lower() == ".xml":
        with open(file_path, "rb") as f:
            parse_junit_xml(f, conn)
    elif file_path.suffix.lower() == ".zip":
        with zipfile.ZipFile(file_path) as zip_file:
            parse_junit_xmls(zip_file, conn)
    else:
        print("Error: Unsupported file type. Please provide an XML or ZIP file.")
        sys.exit(1)

    # Example query to show results
    result = conn.execute("SELECT * FROM test_results").fetchall()
    for row in result:
        print(row)


def main():
    if len(sys.argv) != 2:
        print("Usage: tyto <path_to_file>")
        print(
            "The file can be either a single XML file or a ZIP file containing XML files."
        )
        sys.exit(1)

    file_path = Path(sys.argv[1])

    if not file_path.exists():
        print(f"Error: File {file_path} not found.")
        sys.exit(1)

    conn = duckdb.connect(":memory:")
    conn.execute("""
        CREATE TABLE test_results (
            suite_name VARCHAR,
            case_name VARCHAR,
            result VARCHAR
        )
    """)

    try:
        tyto(file_path, conn)
    except zipfile.BadZipFile:
        print(f"Error: {file_path} is not a valid zip file.")
        sys.exit(1)
    except Exception as e:
        print(f"Error processing file: {e}")
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
