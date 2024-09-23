import asyncio
from collections import namedtuple
from datetime import datetime
from fnmatch import fnmatch
from io import BytesIO
from itertools import chain, starmap
from typing import AsyncIterator, Iterator, TypedDict
from zipfile import ZipFile

import junitparser.xunit2 as jup

from tringa import cli, gh
from tringa.db import DB, TestResult
from tringa.models import PR
from tringa.msg import debug, warn
from tringa.utils import async_to_sync_iterator


class Artifact(TypedDict):
    repo: str
    name: str
    id: int
    url: str
    run_id: int
    branch: str
    commit: str


def fetch_test_data(repo: str) -> None:
    with cli.options.db_config.connect() as db:
        # We fetch for the entire repo, even when the requested scope is `run`, in
        # order to collect information across branches used to identify flakes.
        _fetch_and_load_new_artifacts(db, [repo])


def _fetch_and_load_new_artifacts(
    db: DB,
    repos: list[str],
):
    artifact_globs = cli.options.artifact_globs or ["*"]
    remote_artifacts = _list_remote_artifacts(repos, artifact_globs)
    artifacts_to_download = _get_artifacts_not_in_db(db, remote_artifacts)
    downloaded_artifacts = _download_zip_artifacts(artifacts_to_download)
    rows = _parse_xml_from_zip_artifacts(downloaded_artifacts)
    rows = _fetch_pr_info(list(rows))
    db.insert_rows(rows)


def _list_remote_artifacts(
    repos: list[str],
    artifact_globs: list[str],
) -> list[Artifact]:
    async def _list_artifacts():
        return list(
            filter(
                lambda a: any(fnmatch(a["name"], g) for g in artifact_globs),
                chain.from_iterable(
                    await asyncio.gather(*map(_list_remote_artifacts_for_repo, repos))
                ),
            )
        )

    return asyncio.run(_list_artifacts())


async def _list_remote_artifacts_for_repo(repo: str) -> list[Artifact]:
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


def _get_artifacts_not_in_db(
    db: DB,
    available_artifacts: list[Artifact],
) -> list[Artifact]:
    # TODO: Avoid repeatedly downloading artifacts that do not contribute tests
    existing_artifacts = {
        s
        for (s,) in db.connection.execute(
            "SELECT DISTINCT artifact FROM test"
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


def _parse_xml_from_zip_artifacts(
    artifacts: Iterator[tuple[Artifact, bytes]],
) -> Iterator[TestResult]:
    for artifact, zip_bytes in artifacts:
        with ZipFile(BytesIO(zip_bytes)) as zip_file:
            for file_name in zip_file.namelist():
                if file_name.endswith(".xml"):
                    yield from _parse_xml_file(file_name, zip_file, artifact)


def _fetch_pr_info(rows: list[TestResult]) -> Iterator[TestResult]:
    async def get_prs() -> dict[tuple[str, str], PR]:
        prs: dict[tuple[str, str], PR] = {}
        branches = list({(r.branch, r.repo) for r in rows})
        for (branch, repo), pr in zip(
            branches,
            await asyncio.gather(*starmap(gh.pr, branches), return_exceptions=True),
        ):
            if isinstance(pr, BaseException):
                exc = pr
                del pr
                if "no pull requests found for branch" in str(exc).lower():
                    if branch not in ["main", "master"]:
                        warn(f"Failed to get PR info for {repo}:{branch}: {exc}")
                else:
                    raise exc
            else:
                prs[(repo, branch)] = pr
        return prs

    prs = asyncio.run(get_prs())

    for row in rows:
        if pr := prs.get((row.repo, row.branch)):
            yield row._replace(
                pr_title=pr.title,
                pr=pr.number,
            )
        else:
            yield row


def _parse_xml_file(
    file_name: str, zip_file: ZipFile, artifact: Artifact
) -> Iterator[TestResult]:
    empty_result = namedtuple("ResultElem", ["message", "text"])(None, None)
    xml = zip_file.read(file_name).decode()
    if not xml:
        warn(f"Skipping empty XML file {file_name}")
        return
    debug(f"Parsing {file_name}: xml length is {len(xml)}")
    for test_suite in jup.JUnitXml.fromstring(xml):
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
                    file=file_name,
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
