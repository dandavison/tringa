import sys
import zipfile
from pathlib import Path
from typing import IO, Iterator

import duckdb

from tyto.app import create_schema, tyto


def main():
    if len(sys.argv) != 2:
        print("Usage: tyto <path_to_file>", file=sys.stderr)
        print(
            "The file can be either a single XML file or a ZIP file containing XML files.",
            file=sys.stderr,
        )
        sys.exit(1)
    [file_path] = map(Path, sys.argv[1:])
    if not file_path.exists():
        print(f"Error: File {file_path} not found.", file=sys.stderr)
        sys.exit(1)

    conn = duckdb.connect(":memory:")
    try:
        create_schema(conn)
        tyto(get_junit_xml_files(file_path), conn)
    except zipfile.BadZipFile:
        print(f"Error: {file_path} is not a valid zip file.", file=sys.stderr)
        sys.exit(1)
    else:
        # Example query to show results
        result = conn.execute("SELECT * FROM test").fetchall()
        for row in result:
            print(row)
    finally:
        conn.close()


def get_junit_xml_files(file_path: Path) -> Iterator[IO[bytes]]:
    if file_path.suffix.lower() == ".xml":
        with open(file_path, "rb") as f:
            yield f
    elif file_path.suffix.lower() == ".zip":
        with zipfile.ZipFile(file_path) as zip_file:
            for file_name in zip_file.namelist():
                if file_name.endswith(".xml"):
                    with zip_file.open(file_name) as f:
                        yield f
    else:
        print(
            "Error: Unsupported file type. Please provide an XML or ZIP file.",
            file=sys.stderr,
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
