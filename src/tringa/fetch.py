import asyncio
import concurrent.futures
import tempfile
from collections import namedtuple
from datetime import datetime, timedelta
from itertools import chain
from pathlib import Path
from typing import AsyncIterator, Iterator, List, Optional, TypedDict

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


def fetch_data_for_repo(
    repo: str,
    since: timedelta,
    branch: Optional[str] = None,
    workflow_id: Optional[int] = None,
) -> None:
    if branch:
        rows = Fetcher()._fetch_and_parse_artifacts_for_branch(
            repo, since, branch, workflow_id
        )
    else:
        rows = Fetcher()._fetch_and_parse_artifacts_for_repo(repo, since)
    with cli.options.db_config.connect() as db:
        db.insert_rows(async_iterator_to_list(rows))


def fetch_data_for_pr(pr: PR) -> None:
    with cli.console.status("Fetching XML artifacts"):
        rows = asyncio.run(
            Fetcher()._fetch_and_parse_artifacts_for_pr(pr, since=cli.options.since)
        )
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
        self, repo: str, since: timedelta
    ) -> AsyncIterator[TestResult]:
        prs = await gh.prs(repo, since=since)
        for test_results_fut in asyncio.as_completed(
            self._fetch_and_parse_artifacts_for_pr(pr, since) for pr in prs
        ):
            for test_result in await test_results_fut:
                yield test_result

    async def _fetch_and_parse_artifacts_for_branch(
        self,
        repo: str,
        since: timedelta,
        branch: str,
        workflow_id: Optional[int] = None,
    ) -> AsyncIterator[TestResult]:
        runs = await gh.runs(repo, since, branch, workflow_id)

        for test_results_fut in asyncio.as_completed(
            self._fetch_and_parse_artifacts_for_run(run) for run in runs
        ):
            for test_result in await test_results_fut:
                yield test_result

    async def _fetch_and_parse_artifacts_for_pr(
        self, pr: gh.PR, since: timedelta
    ) -> list[TestResult]:
        runs = await gh.runs_via_workflows(pr.repo, since, pr.branch)
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
        self, run: Run, pr: Optional[PR] = None
    ) -> List[TestResult]:
        with tempfile.TemporaryDirectory() as dir:
            dir = Path(dir)
            if not await gh.run_download(run, dir, patterns=self.artifact_globs):
                return []
            return await asyncio.get_event_loop().run_in_executor(
                self.executor, _parse_artifacts_for_run, run, dir, pr
            )


def _parse_artifacts_for_run(
    run: Run, dir: Path, pr: Optional[PR] = None
) -> List[TestResult]:
    def test_results() -> Iterator[TestResult]:
        top_level_xmls = [p for p in dir.glob("*.xml") if p.is_file()]
        assert not any(
            top_level_xmls
        ), f"Expected top-level directory {dir} not to contain XML files, but contains: {top_level_xmls}"
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
    artifact_name: str, file: Path, run: Run, pr: Optional[PR]
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
                    pr=pr.number if pr else None,
                    pr_title=pr.title if pr else None,
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
