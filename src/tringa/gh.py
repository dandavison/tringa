"""
A Python wrapper for the GitHub CLI.
https://cli.github.com/manual/
"""

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from subprocess import CalledProcessError
from typing import Optional

from tringa.exceptions import TringaException
from tringa.models import PR, Run
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
        "headRefName,headRepository,headRepositoryOwner,title,number",
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
        "headRefName,headRepository,headRepositoryOwner,title,number",
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


async def runs(repo: str, branch: str) -> list[Run]:
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


async def run_download(run: Run, dir: Path) -> None:
    await _gh("run", "download", str(run.id), "--repo", run.repo, "--dir", str(dir))


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
