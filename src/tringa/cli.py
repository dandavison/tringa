import sys
import tempfile
import zipfile
from io import BytesIO
from pathlib import Path
from typing import IO, Iterator

import duckdb
import IPython

from tringa.app import create_schema, load_xml
from tringa.github import download_junit_artifacts


def main():
    if len(sys.argv) <= 1:
        print("Usage: tringa owner/repo1 [owner/repo2 ...]", file=sys.stderr)
        sys.exit(1)
    repos = sys.argv[1:]

    with duckdb.connect(tempfile.mktemp()) as conn:
        try:
            create_schema(conn)
            for _, zip_file in download_junit_artifacts(repos):
                for xml in get_xml_files_from_zip_file(BytesIO(zip_file)):
                    load_xml(xml, conn)
        except Exception as err:
            print(f"Error: {err}", file=sys.stderr)
            sys.exit(1)
        else:
            IPython.start_ipython(argv=[], user_ns={"conn": conn, "sql": conn.sql})


def get_junit_xml_files_from_disk(file_path: Path) -> Iterator[IO[bytes]]:
    if file_path.suffix.lower() == ".xml":
        with open(file_path, "rb") as f:
            yield f
    elif file_path.suffix.lower() == ".zip":
        yield from get_xml_files_from_zip_file(file_path)
    else:
        print(
            "Error: Please provide an XML (*.xml) or ZIP (*.zip) file.",
            file=sys.stderr,
        )
        sys.exit(1)


def get_xml_files_from_zip_file(file: Path | IO[bytes]) -> Iterator[IO[bytes]]:
    with zipfile.ZipFile(file) as zip_file:
        for file_name in zip_file.namelist():
            if file_name.endswith(".xml"):
                with zip_file.open(file_name) as f:
                    yield f


if __name__ == "__main__":
    main()
