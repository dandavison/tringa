"""
A Python wrapper for the GitHub CLI.
https://cli.github.com/manual/
"""

import json
import sys
from typing import Optional

from tringa.models import PR
from tringa.utils import execute


async def api_bytes(endpoint: str) -> bytes:
    return await _gh("api", endpoint)


async def api(endpoint: str) -> dict:
    return json.loads((await api_bytes(endpoint)).decode())


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

    data = json.loads(await _gh(*cmd))
    return PR(
        repo=f"{data['headRepositoryOwner']['login']}/{data['headRepository']['name']}",
        number=data["number"],
        title=data["title"],
        branch=data["headRefName"],
    )


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


async def rerun(repo: str, run_id: str) -> None:
    await _gh("run", "rerun", run_id, "--failed", "-R", repo)


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
