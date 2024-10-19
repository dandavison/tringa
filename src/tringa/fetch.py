import asyncio
import concurrent.futures
import tempfile
from collections import namedtuple
from datetime import datetime
from itertools import chain
from pathlib import Path
from typing import AsyncIterator, Iterator, List, TypedDict

import junitparser.xunit2 as jup

from tringa import cli, gh
from tringa.db import TestResult
from tringa.models import PR, Run
from tringa.msg import debug
from tringa.utils import async_iterator_to_list


class Artifact(TypedDict):
    repo: str
    name: str
    id: int
    url: str
    run_id: int
    branch: str
    commit: str


def fetch_data_for_repo(repo: str) -> None:
    with cli.console.status("Fetching XML artifacts"):
        rows = async_iterator_to_list(
            Fetcher()._fetch_and_parse_artifacts_for_repo(repo)
        )
    with cli.options.db_config.connect() as db:
        db.insert_rows(rows)


def fetch_data_for_pr(pr: PR) -> None:
    with cli.console.status("Fetching XML artifacts"):
        rows = asyncio.run(Fetcher()._fetch_and_parse_artifacts_for_pr(pr))
        with cli.options.db_config.connect() as db:
            db.insert_rows(rows)


class Fetcher:
    """
    Fetch, parse, and load test data from junit XML artifacts from GitHub CI.

    We use two threads: one for the asyncio event loop to perform concurrent
    fetches from the GitHub API, and one for parsing the XML.
    """

    def __init__(self):
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        self.artifact_globs = cli.options.artifact_globs

    async def _fetch_and_parse_artifacts_for_repo(
        self,
        repo: str,
    ) -> AsyncIterator[TestResult]:
        prs = await gh.prs(repo, since=cli.options.since)
        for test_results_fut in asyncio.as_completed(
            self._fetch_and_parse_artifacts_for_pr(pr) for pr in prs
        ):
            for test_result in await test_results_fut:
                yield test_result

    async def _fetch_and_parse_artifacts_for_pr(self, pr: gh.PR) -> list[TestResult]:
        runs = await gh.runs_via_workflows(pr.repo, pr.branch)
        return list(
            chain.from_iterable(
                [
                    (await rows)
                    for rows in asyncio.as_completed(
                        self._fetch_and_parse_artifacts_for_run(run, pr) for run in runs
                    )
                ]
            )
        )

    async def _fetch_and_parse_artifacts_for_run(
        self, run: Run, pr: PR
    ) -> List[TestResult]:
        with tempfile.TemporaryDirectory() as dir:
            dir = Path(dir)
            try:
                await gh.run_download(run, dir, patterns=self.artifact_globs)
            except gh.CalledProcessError as exc:
                if exc.stderr and "no valid artifacts" in exc.stderr.decode():
                    debug(f"Run {run.id} {run.pr or "[no PR]"} has no valid artifacts")
                    return []
                else:
                    raise exc
            return await asyncio.get_event_loop().run_in_executor(
                self.executor, _parse_artifacts_for_run, run, dir, pr
            )


def _parse_artifacts_for_run(run: Run, dir: Path, pr: PR) -> List[TestResult]:
    def test_results() -> Iterator[TestResult]:
        assert not any(
            dir.glob("*.xml")
        ), "Expected top-level directory to contain extracted artifact directories"
        for extracted_artifact_dir in dir.iterdir():
            assert (
                extracted_artifact_dir.is_dir()
            ), f"Expected {extracted_artifact_dir} to be a directory"
            artifact_name = extracted_artifact_dir.name
            for file in extracted_artifact_dir.glob("*.xml"):
                assert file.is_file()
                yield from _parse_xml_file(artifact_name, file, run, pr)

    return list(test_results())


def _parse_xml_file(
    artifact_name: str, file: Path, run: Run, pr: PR
) -> Iterator[TestResult]:
    empty_result = namedtuple("ResultElem", ["message", "text"])(None, None)
    debug(f"Parsing {file}")
    MAX_TEST_OUTPUT_LENGTH = 100_000
    for test_suite in jup.JUnitXml.fromfile(str(file)):
        for test_case in test_suite:
            if not test_case.name:
                continue
            # Passed test cases have no result. A failed/skipped test case will
            # typically have a single result, but the schema permits multiple.
            for result in test_case.result or [empty_result]:
                text = result.text
                if text and len(text) > MAX_TEST_OUTPUT_LENGTH:
                    debug(
                        f"Truncating {file} output from {len(text)} to {MAX_TEST_OUTPUT_LENGTH}"
                    )
                    text = text[:MAX_TEST_OUTPUT_LENGTH] + "...<truncated by tringa>"
                yield TestResult(
                    repo=run.repo,
                    artifact=artifact_name,
                    run_id=run.id,
                    branch=run.branch,
                    sha=run.sha,
                    pr=pr.number,
                    pr_title=pr.title,
                    file=file.name,
                    suite=test_suite.name,
                    suite_time=datetime.fromisoformat(test_suite.timestamp),
                    suite_duration=test_suite.time,
                    name=test_case.name,
                    classname=test_case.classname or "",
                    flaky=False,
                    duration=test_case.time,
                    passed=test_case.is_passed,
                    skipped=test_case.is_skipped,
                    message=result.message,
                    text=text,
                )
