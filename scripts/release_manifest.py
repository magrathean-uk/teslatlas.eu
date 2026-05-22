from __future__ import annotations

import os
import sys
from dataclasses import dataclass


SITE_SLUG = os.environ.get("SITE_SLUG", "teslatlas")
SITE_ASSET_NAME = f"{SITE_SLUG}-site.tar.gz"
CHECKSUM_ASSET_NAME = "SHA256SUMS"


class ReleaseManifestError(ValueError):
    pass


@dataclass(frozen=True)
class DeployManifest:
    release_id: str
    site_url: str
    site_sha: str


def _assets_by_name(release: dict) -> dict:
    return {asset.get("name", ""): asset for asset in release.get("assets", [])}


def _sha256_digest(asset: dict, name: str) -> str:
    digest = str(asset.get("digest", ""))
    if digest.startswith("sha256:"):
        value = digest.split("sha256:", 1)[1]
        if len(value) >= 16:
            return value
    raise ReleaseManifestError(f"asset {name} missing sha256 digest")


def build_deploy_manifest(release: dict) -> DeployManifest:
    assets = _assets_by_name(release)
    site_asset = assets.get(SITE_ASSET_NAME)
    if not site_asset:
        raise ReleaseManifestError(f"missing asset: {SITE_ASSET_NAME}")
    if CHECKSUM_ASSET_NAME not in assets:
        raise ReleaseManifestError(f"missing asset: {CHECKSUM_ASSET_NAME}")

    site_sha = _sha256_digest(site_asset, SITE_ASSET_NAME)
    site_url = str(site_asset.get("url", "")).strip()
    if not site_url:
        raise ReleaseManifestError(f"asset {SITE_ASSET_NAME} missing url")

    return DeployManifest(release_id=site_sha[:16], site_url=site_url, site_sha=site_sha)


def write_github_env(output) -> None:
    output.write(f"SITE_RELEASE_ASSET={SITE_ASSET_NAME}\n")
    output.write(f"CHECKSUM_RELEASE_ASSET={CHECKSUM_ASSET_NAME}\n")


def main(argv: list[str]) -> int:
    if argv == ["github-env"]:
        write_github_env(sys.stdout)
        return 0
    if argv == ["site-asset"]:
        print(SITE_ASSET_NAME)
        return 0
    if argv == ["checksum-asset"]:
        print(CHECKSUM_ASSET_NAME)
        return 0
    raise SystemExit("usage: release_manifest.py github-env|site-asset|checksum-asset")


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
