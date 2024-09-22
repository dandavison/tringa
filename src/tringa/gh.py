"""
A Python wrapper for the GitHub CLI.
https://cli.github.com/manual/
"""

import json
import sys
from subprocess import CalledProcessError
from typing import Optional

from tringa.exceptions import TringaException
from tringa.models import PR, Repo
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

    try:
        data = json.loads(await _gh(*cmd))
    except CalledProcessError as e:
        if "no pull requests found for branch" in e.stderr.decode():
            raise TringaException(
                f"{e}\n{e.stderr.decode()}\nIt looks like you ran `tringa pr` on a branch without a pull request."
            )
        else:
            raise
    else:
        return PR(
            repo=f"{data['headRepositoryOwner']['login']}/{data['headRepository']['name']}",
            number=data["number"],
            title=data["title"],
            branch=data["headRefName"],
        )


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
