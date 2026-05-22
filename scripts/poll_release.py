#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import subprocess
import urllib.error
import urllib.request
from pathlib import Path

try:
    from .release_manifest import build_deploy_manifest
except ImportError:
    from release_manifest import build_deploy_manifest


GITHUB_REPOSITORY = os.environ.get("GITHUB_REPOSITORY", "magrathean-uk/teslatlas.eu")
RELEASE_TAG = os.environ.get("RELEASE_TAG", "deploy-main")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
STATE_FILE = Path(os.environ.get("DEPLOY_STATE_FILE", "/opt/sites/teslatlas/runtime/last_release"))
DEPLOY_SCRIPT = os.environ.get("DEPLOY_SCRIPT", "/opt/sites/teslatlas/deploy.sh")


def fetch_release() -> dict | None:
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"
    request = urllib.request.Request(
        f"https://api.github.com/repos/{GITHUB_REPOSITORY}/releases/tags/{RELEASE_TAG}",
        headers=headers,
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return None
        raise


def read_current_release() -> str:
    if not STATE_FILE.exists():
        return ""
    return STATE_FILE.read_text(encoding="utf-8").strip()


def write_current_release(release_id: str) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(f"{release_id}\n", encoding="utf-8")


def main() -> int:
    release = fetch_release()
    if release is None:
        print(f"release {RELEASE_TAG} not found for {GITHUB_REPOSITORY}")
        return 0
    manifest = build_deploy_manifest(release)
    release_id = manifest.release_id
    if read_current_release() == release_id:
        return 0
    subprocess.run([DEPLOY_SCRIPT, manifest.site_url, manifest.site_sha, release_id], check=True)
    write_current_release(release_id)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
