import asyncio
import json
import os
import subprocess
import sys
from itertools import chain
from typing import AsyncIterator, Iterator

from tyto.utils import async_to_sync_iterator, info


async def fetch(endpoint: str) -> bytes:
    try:
        process = await asyncio.create_subprocess_exec(
            "gh",
            "api",
            endpoint,
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
        raise subprocess.CalledProcessError(process.returncode, ["gh", "api", endpoint])
    return stdout


async def fetch_json(endpoint: str) -> dict:
    return json.loads((await fetch(endpoint)).decode())


async def list_artifacts(repo: str) -> list[dict[str, str]]:
    info(f"Listing artifacts for {repo}")
    return [
        {
            "repo": repo,
            "name": artifact["name"],
            "id": artifact["id"],
            "url": artifact["url"],
            "download_url": artifact["archive_download_url"],
        }
        for artifact in (await fetch_json(f"/repos/{repo}/actions/artifacts"))[
            "artifacts"
        ]
    ]


def download_junit_artifacts(
    repos: list[str],
) -> Iterator[tuple[dict[str, str], bytes]]:
    info(f"Downloading artifacts for {repos}")

    async def fetch_zip(artifact: dict) -> tuple[dict[str, str], bytes]:
        info(f"Downloading {artifact['name']} from {artifact['repo']}")
        zip = await fetch(
            f"/repos/{artifact['repo']}/actions/artifacts/{artifact['id']}/zip"
        )
        return artifact, zip

    async def fetch_zips() -> AsyncIterator[tuple[dict[str, str], bytes]]:
        artifacts = filter(
            lambda a: a["name"].startswith("junit-xml--"),
            chain.from_iterable(await asyncio.gather(*map(list_artifacts, repos))),
        )
        for coro in asyncio.as_completed(map(fetch_zip, artifacts)):
            yield await coro

    return async_to_sync_iterator(fetch_zips())


if __name__ == "__main__":
    repo = "temporalio/sdk-python"
    output_dir = "/tmp/tringa-artifacts"
    os.makedirs(output_dir, exist_ok=True)
    for artifact, zip_data in download_junit_artifacts(
        ["temporalio/sdk-python", "temporalio/sdk-typescript"]
    ):
        file_path = os.path.join(output_dir, f"{artifact['name']}.zip")
        with open(file_path, "wb") as f:
            f.write(zip_data)
        info(f"Downloaded: {file_path}")
