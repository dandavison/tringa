import asyncio
import tempfile
from collections import namedtuple
from datetime import datetime
from pathlib import Path
from typing import AsyncIterator, Iterator, List, TypedDict

import junitparser.xunit2 as jup

from tringa import cli, gh
from tringa.db import DB, TestResult
from tringa.models import Run
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


def fetch_test_data(repo: str) -> None:
    if cli.options.nofetch:
        return
    with cli.options.db_config.connect() as db:
        # We fetch for the entire repo, even when the requested scope is `run`, in
        # order to collect information across branches used to identify flakes.
        _fetch_and_load_new_artifacts(db, repo)


def _fetch_and_load_new_artifacts(
    db: DB,
    repo: str,
):
    artifact_globs = cli.options.artifact_globs or ["*"]
    with cli.console.status("Fetching XML artifacts"):
        rows = async_iterator_to_list(_fetch_and_parse_artifacts_for_repo(repo))
        db.insert_rows(rows)


async def _fetch_and_parse_artifacts_for_repo(repo: str) -> AsyncIterator[TestResult]:
    # Fetch all PRs since the specified date
    prs = await gh.prs(repo, since=cli.options.since)

    # Create tasks to fetch runs and process them for each PR
    tasks = [asyncio.create_task(_fetch_runs_and_process(pr)) for pr in prs]

    # Process results as they become available
    for coro in asyncio.as_completed(tasks):
        async for test_result in await coro:
            yield test_result


async def _fetch_runs_and_process(pr: gh.PR) -> AsyncIterator[TestResult]:
    # Fetch runs for the PR's branch
    runs = await gh.runs(pr.repo, branch=pr.branch)

    # Create tasks to download and parse artifacts for each run
    run_tasks = [
        asyncio.create_task(_download_and_parse_artifacts_for_run(run)) for run in runs
    ]

    # Process run tasks as they complete
    for run_coro in asyncio.as_completed(run_tasks):
        results = await run_coro  # List[TestResult]
        for test_result in results:
            yield test_result


async def _download_and_parse_artifacts_for_run(run: Run) -> List[TestResult]:
    with tempfile.TemporaryDirectory() as dir:
        dir = Path(dir)
        # Download artifacts for the run
        await gh.run_download(run, dir)

        # Parse artifacts in a separate thread to avoid blocking the event loop
        loop = asyncio.get_event_loop()
        results = await loop.run_in_executor(
            None, _parse_artifacts_for_run_sync, dir, run
        )
        return results


def _parse_artifacts_for_run_sync(dir: Path, run: Run) -> List[TestResult]:
    return list(_parse_artifacts_for_run(dir, run))


def _parse_artifacts_for_run(dir: Path, run: Run) -> Iterator[TestResult]:
    for file in dir.iterdir():
        if file.is_file() and file.suffix == ".xml":
            # TODO: is Artifact needed?
            artifact = Artifact(
                repo=run.repo,
                name=file.name,
                id=run.id,
                url=run.url,
                run_id=run.id,
                branch=run.branch,
                commit=run.sha,
            )
            for tr in _parse_xml_file(file, artifact):
                yield tr


def _parse_xml_file(file: Path, artifact: Artifact) -> Iterator[TestResult]:
    empty_result = namedtuple("ResultElem", ["message", "text"])(None, None)
    debug(f"Parsing {file}")
    for test_suite in jup.JUnitXml.fromfile(str(file)):
        for test_case in test_suite:
            # Passed test cases have no result. A failed/skipped test case will
            # typically have a single result, but the schema permits multiple.
            for result in test_case.result or [empty_result]:
                yield TestResult(
                    repo=artifact["repo"],
                    artifact=artifact["name"],
                    run_id=artifact["run_id"],
                    branch=artifact["branch"],
                    sha=artifact["commit"],
                    pr=0,
                    pr_title="",
                    file=file.name,
                    suite=test_suite.name,
                    suite_time=datetime.fromisoformat(test_suite.timestamp),
                    suite_duration=test_suite.time,
                    name=test_case.name,
                    classname=test_case.classname,
                    flaky=False,
                    duration=test_case.time,
                    passed=test_case.is_passed,
                    skipped=test_case.is_skipped,
                    message=result.message,
                    text=result.text,
                )
