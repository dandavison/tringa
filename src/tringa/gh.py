"""
A Python wrapper for the GitHub CLI.
https://cli.github.com/manual/
"""

import json
import sys
from typing import Optional

from tringa.models import PR, Repo
from tringa.utils import execute


async def api_bytes(endpoint: str) -> bytes:
    return await _gh("api", endpoint)


async def api(endpoint: str) -> dict:
    return json.loads((await api_bytes(endpoint)).decode())


async def pr(pr_identifier: Optional[str] = None) -> PR:
    cmd = [
        "pr",
        "view",
        "--json",
        "headRefName,headRepository,headRepositoryOwner,url,title,number",
    ]
    if pr_identifier is not None:
        cmd.append(pr_identifier)

    return PR(**json.loads(await _gh(*cmd)))


async def repo(repo_identifier: Optional[str] = None) -> Repo:
    cmd = [
        "repo",
        "view",
        "--json",
        "nameWithOwner",
    ]
    if repo_identifier is not None:
        cmd.append(repo_identifier)

    return Repo(**json.loads(await _gh(*cmd)))


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
