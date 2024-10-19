"""
A Python wrapper for the GitHub CLI.
https://cli.github.com/manual/
"""

import asyncio
import json
import sys
from datetime import datetime, timedelta
from itertools import chain
from pathlib import Path
from subprocess import CalledProcessError
from typing import Optional, TypedDict

from tringa.exceptions import TringaException
from tringa.models import PR, Run, StatusCheck
from tringa.msg import debug
from tringa.utils import execute


async def api_bytes(endpoint: str, all_pages: bool = False) -> bytes:
    args = ["--paginate", "--slurp"] if all_pages else []
    return await _gh("api", *args, endpoint)


async def api(endpoint: str) -> list[dict]:
    return json.loads((await api_bytes(endpoint, all_pages=True)).decode())


## PR


async def prs(repo: str, since: timedelta) -> list[PR]:
    cmd = [
        "pr",
        "list",
        "--json",
        "headRefName,headRepository,headRepositoryOwner,title,number,statusCheckRollup",
    ]
    if since is not None:
        then = datetime.now() - since
        cmd.extend(["--search", f"created:>={then.date().isoformat()}"])
    if repo is not None:
        cmd.extend(["--repo", repo])

    return [_pr(d) for d in json.loads(await _gh(*cmd))]


async def pr(pr_identifier: Optional[str] = None, repo: Optional[str] = None) -> PR:
    cmd = [
        "pr",
        "view",
        "--json",
        "headRefName,headRepository,headRepositoryOwner,title,number,statusCheckRollup",
    ]
    if pr_identifier is not None:
        cmd.append(pr_identifier)
    if repo is not None:
        cmd.extend(["--repo", repo])
    return _pr(json.loads(await _gh(*cmd)))


def _pr(data: dict) -> PR:
    return PR(
        repo=f"{data['headRepositoryOwner']['login']}/{data['headRepository']['name']}",
        number=data["number"],
        title=data["title"],
        branch=data["headRefName"],
        status_checks=[
            StatusCheck(
                name=d["name"],
                status=d["status"],
                conclusion=d["conclusion"],
                workflow_name=d["workflowName"],
            )
            for d in data["statusCheckRollup"]
            if d["__typename"] == "CheckRun"
        ],
    )


## Repo


async def repo(repo_identifier: Optional[str] = None) -> str:
    cmd = [
        "repo",
        "view",
        "--json",
        "nameWithOwner",
    ]
    if repo_identifier is not None:
        cmd.append(repo_identifier)

    return json.loads(await _gh(*cmd))["nameWithOwner"]


# Run


class _WorkflowData(TypedDict):
    id: int
    name: str


async def runs_via_workflows(repo: str, branch: str) -> list[Run]:
    # workaround for https://github.com/cli/cli/issues/9228
    cmd = ["workflow", "list", "--repo", repo, "--json", "id,name"]
    workflows: list[_WorkflowData] = json.loads(await _gh(*cmd))
    return list(
        chain.from_iterable(
            await asyncio.gather(*[runs(repo, branch, w["id"]) for w in workflows])
        )
    )


async def runs(repo: str, branch: str, workflow_id: Optional[int] = None) -> list[Run]:
    cmd = [
        "run",
        "list",
        "--repo",
        repo,
        "--branch",
        branch,
        "--json",
        "databaseId,headBranch,headSha,startedAt",
    ]
    if workflow_id is not None:
        cmd.extend(["--workflow", str(workflow_id)])
    return [
        Run(
            id=data["databaseId"],
            repo=repo,
            branch=data["headBranch"],
            sha=data["headSha"],
            started_at=data["startedAt"],
            pr=None,
        )
        for data in json.loads(await _gh(*cmd))
    ]


async def run_download(run: Run, dir: Path, patterns: list[str]) -> bool:
    args = ["run", "download", str(run.id), "--repo", run.repo, "--dir", str(dir)]
    for p in patterns:
        args.extend(["--pattern", p])
    try:
        await _gh(*args)
    except CalledProcessError as exc:
        stderr = exc.stderr.decode() if exc.stderr else ""
        if "no artifact matches" in stderr:
            debug(
                f"Run {run.id} {run.pr or "[no PR]"} has no artifacts matching patterns: {patterns}"
            )
            return False
        elif "no valid artifacts" in stderr:
            debug(f"Run {run.id} {run.pr or "[no PR]"} has no valid artifacts")
            return False
        else:
            raise
    else:
        return True


async def rerun(repo: str, run_id: int) -> None:
    try:
        await _gh("run", "rerun", str(run_id), "--failed", "-R", repo)
    except CalledProcessError as exc:
        if exc.stderr and "cannot be rerun" in exc.stderr.decode():
            raise TringaException(
                f"Run {run_id} cannot be rerun (are you sure it's finished?)"
            ) from exc
        else:
            raise


async def _gh(*args: str) -> bytes:
    try:
        return await execute(["gh", *args])
    except FileNotFoundError as err:
        if "'gh'" in str(err):
            print(
                "Please install gh and run `gh auth login`: https://cli.github.com/",
                file=sys.stderr,
            )
            exit(1)
        else:
            raise
