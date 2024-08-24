import sys
import zipfile
from typing import IO

from junitparser.junitparser import JUnitXml


def parse_junit_xml(file: IO[bytes]) -> None:
    junit_xml = JUnitXml.fromstring(file.read().decode())

    for test_suite in junit_xml:
        print(f"Test Suite: {test_suite.name}")

        for test_case in test_suite:
            print(f"  Test Case: {test_case.name}")
            print(f"    Result: {'Passed' if test_case.result is None else 'Failed'}")

        print()


def parse_junit_xml_from_zip(zip_file: zipfile.ZipFile) -> None:
    for file_name in zip_file.namelist():
        if file_name.endswith(".xml"):
            with zip_file.open(file_name) as f:
                parse_junit_xml(f)


if __name__ == "__main__":
    parse_junit_xml_from_zip(zipfile.ZipFile(sys.argv[1]))
