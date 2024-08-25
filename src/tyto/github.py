import json
import subprocess
from typing import cast


def fetch(endpoint: str) -> dict | list:
    return json.loads(
        subprocess.run(
            ["gh", "api", endpoint], check=True, capture_output=True, text=True
        ).stdout
    )


def list_artifacts(repo: str) -> list[dict[str, str]]:
    return [
        {
            "name": artifact["name"],
            "url": artifact["url"],
            "download_url": artifact["archive_download_url"],
        }
        for artifact in cast(dict, fetch(f"/repos/{repo}/actions/artifacts"))
    ]


if __name__ == "__main__":
    print(json.dumps(list_artifacts("temporalio/sdk-python"), indent=2))
