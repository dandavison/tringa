import asyncio
import os
from collections import namedtuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from fnmatch import fnmatch
from io import BytesIO
from itertools import chain
from typing import AsyncIterator, Iterator, Optional, TypedDict
from zipfile import ZipFile

import junitparser.xunit2 as jup
from rich import progress

from tringa import gh
from tringa.db import DB, TestResult
from tringa.msg import debug, info
from tringa.utils import async_to_sync_iterator


class Artifact(TypedDict):
    repo: str
    name: str
    id: int
    url: str
    run_id: str
    branch: str
    commit: str


def fetch_and_load_new_artifacts(
    db: DB,
    repos: list[str],
    branch: Optional[str] = None,
    artifact_name_globs: Optional[list[str]] = None,
):
    remote_artifacts = _list_remote_artifacts(
        repos, branch, artifact_name_globs or ["*"]
    )
    artifacts_to_download = _query_for_artifacts_not_in_db(db, remote_artifacts)
    downloaded_artifacts = _download_zip_artifacts(artifacts_to_download)
    msg = f"Downloaded {len(artifacts_to_download)} new artifacts for repos: {repos}"
    if branch is not None:
        msg += f" branch: {branch}"
    if artifact_name_globs is not None:
        msg += f" artifact_name_globs: {artifact_name_globs}"
    info(msg)
    _load_xml_from_zip_artifacts(db, downloaded_artifacts)


def _list_remote_artifacts(
    repos: list[str],
    branch: Optional[str],
    artifact_name_globs: list[str],
) -> list[Artifact]:
    def include(artifact: Artifact) -> bool:
        if not any(fnmatch(artifact["name"], g) for g in artifact_name_globs):
            return False
        if branch is not None and artifact["branch"] != branch:
            return False
        return True

    async def _list_artifacts():
        return list(
            filter(
                include,
                chain.from_iterable(
                    await asyncio.gather(*map(_list_remote_artifacts_for_repo, repos))
                ),
            )
        )

    return asyncio.run(_list_artifacts())


async def _list_remote_artifacts_for_repo(repo: str) -> list[Artifact]:
    debug(f"Listing artifacts for {repo}")
    return [
        {
            "repo": repo,
            "name": artifact["name"],
            "id": artifact["id"],
            "url": artifact["url"],
            "run_id": artifact["workflow_run"]["id"],
            "branch": artifact["workflow_run"]["head_branch"],
            "commit": artifact["workflow_run"]["head_sha"],
        }
        for artifact in (await gh.api(f"/repos/{repo}/actions/artifacts"))["artifacts"]
    ]


def _query_for_artifacts_not_in_db(
    db: DB,
    available_artifacts: list[Artifact],
) -> list[Artifact]:
    # TODO: Avoid repreatedly downloading artifacts that do not contribute tests
    existing_artifacts = {
        s
        for (s,) in db.connection.execute(
            "SELECT DISTINCT artifact_name FROM test"
        ).fetchall()
    }
    return [a for a in available_artifacts if a["name"] not in existing_artifacts]


def _download_zip_artifacts(
    artifacts: list[Artifact],
) -> Iterator[tuple[Artifact, bytes]]:
    debug(
        f"Downloading {len(artifacts)} artifacts:",
        ", ".join(a["name"] for a in artifacts),
    )

    async def fetch_zip(artifact: Artifact) -> tuple[Artifact, bytes]:
        debug(f"Downloading zip artifact: {artifact['name']} from: {artifact['repo']}")
        zip_data = await gh.api_bytes(
            f"/repos/{artifact['repo']}/actions/artifacts/{artifact['id']}/zip"
        )
        return artifact, zip_data

    async def fetch_zips() -> AsyncIterator[tuple[Artifact, bytes]]:
        for coro in asyncio.as_completed(map(fetch_zip, artifacts)):
            yield await coro

    return async_to_sync_iterator(fetch_zips())


def _load_xml_from_zip_artifacts(
    db: DB,
    artifacts: Iterator[tuple[Artifact, bytes]],
):
    info(f"Loading artifacts into {db}")
    # Parsing the XML is slow, and doing it in parallel is a significant
    # optimization. OTOH we write to the DB from the main thread only.
    zip_files = []
    futures = []
    with ThreadPoolExecutor(max_workers=os.cpu_count() or 1) as executor:
        for artifact, zip_bytes in artifacts:
            zip_file = ZipFile(BytesIO(zip_bytes))
            for file_name in zip_file.namelist():
                if file_name.endswith(".xml"):
                    futures.append(
                        executor.submit(_get_db_rows, artifact, zip_file, file_name)
                    )
            zip_files.append(zip_file)
        rows = []
        progress.track(
            [rows.extend(f.result()) for f in as_completed(futures)],
            total=len(futures),
        )
        if rows:
            db.insert_rows(rows)
    for zip_file in zip_files:
        zip_file.close()


def _get_db_rows(
    artifact: Artifact, zip_file: ZipFile, file_name: str
) -> Iterator[TestResult]:
    empty_result = namedtuple("ResultElem", ["message", "text"])(None, None)
    xml = zip_file.read(file_name).decode()
    debug(f"Parsing {file_name}: xml is\n{xml}")
    for test_suite in jup.JUnitXml.fromstring(xml):
        for test_case in test_suite:
            # Passed test cases have no result. A failed/skipped test case will
            # typically have a single result, but the schema permits multiple.
            for result in test_case.result or [empty_result]:
                yield TestResult(
                    artifact_name=artifact["name"],
                    run_id=artifact["run_id"],
                    branch=artifact["branch"],
                    sha=artifact["commit"],
                    file=file_name,
                    suite=test_suite.name,
                    suite_timestamp=datetime.fromisoformat(test_suite.timestamp),
                    suite_time=test_suite.time,
                    name=test_case.name,
                    classname=test_case.classname,
                    flaky=False,
                    time=test_case.time,
                    passed=test_case.is_passed,
                    skipped=test_case.is_skipped,
                    message=result.message,
                    text=result.text,
                )
