"""
A Python wrapper for the GitHub CLI.
https://cli.github.com/manual/
"""

import asyncio
import json
import subprocess
import sys
from dataclasses import dataclass
from typing import Optional


async def api_bytes(endpoint: str) -> bytes:
    return await _gh("api", endpoint)


async def api(endpoint: str) -> dict:
    return json.loads((await api_bytes(endpoint)).decode())


@dataclass
class PR:
    headRefName: str
    headRepository: dict
    headRepositoryOwner: dict

    @property
    def repo(self) -> str:
        return f"{self.headRepositoryOwner['login']}/{self.headRepository['name']}"

    @property
    def branch(self) -> str:
        return self.headRefName


async def pr(pr_identifier: Optional[str] = None) -> PR:
    cmd = [
        "pr",
        "view",
        "--json",
        "headRefName,headRepository,headRepositoryOwner",
    ]
    if pr_identifier is not None:
        cmd.append(pr_identifier)

    return PR(**json.loads(await _gh(*cmd)))


@dataclass
class Run:
    run_id: str
    pr: PR
    timestamp: str
    sha: str


async def latest_run_in_pr(pr_identifier: Optional[str] = None) -> Run:
    pr_data = await pr(pr_identifier)
    branch = pr_data.branch
    repo = pr_data.repo

    cmd = ["api", f"/repos/{repo}/actions/runs?branch={branch}&per_page=1"]
    response = json.loads(await _gh(*cmd))
    if response["total_count"] == 0:
        raise ValueError(f"No runs found for branch {branch} in repo {repo}")

    run_data = response["workflow_runs"][0]
    return Run(
        run_id=str(run_data["id"]),
        pr=pr_data,
        timestamp=run_data["created_at"],
        sha=run_data["head_sha"],
    )


async def _gh(*args: str) -> bytes:
    try:
        process = await asyncio.create_subprocess_exec(
            "gh",
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
    except FileNotFoundError as err:
        if "'gh'" in str(err):
            print(
                "Please install gh and run `gh auth login`: https://cli.github.com/",
                file=sys.stderr,
            )
            exit(1)
        else:
            raise
    stdout, _ = await process.communicate()
    assert process.returncode is not None
    if process.returncode != 0:
        raise subprocess.CalledProcessError(process.returncode, ["gh", *args])
    return stdout
