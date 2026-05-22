#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import sys
import tarfile
import tempfile
import urllib.request
from dataclasses import dataclass
from pathlib import Path

try:
    import fcntl
except ImportError:
    fcntl = None


class DeployApplyError(RuntimeError):
    pass


DIR_MODE = 0o755
FILE_MODE = 0o644
EXEC_MODE = 0o755


@dataclass(frozen=True)
class DeployConfig:
    site_slug: str = "teslatlas"
    project_dir: Path = Path("/opt/sites/teslatlas")
    lock_file: Path = Path("/tmp/teslatlas-deploy.lock")
    keep_releases: int = 3
    keep_downloads: int = 3

    @classmethod
    def from_env(cls) -> "DeployConfig":
        site_slug = os.environ.get("SITE_SLUG", "teslatlas")
        return cls(
            site_slug=site_slug,
            project_dir=Path(os.environ.get("PROJECT_DIR", f"/opt/sites/{site_slug}")),
            lock_file=Path(os.environ.get("LOCK_FILE", f"/tmp/{site_slug}-deploy.lock")),
            keep_releases=int(os.environ.get("KEEP_RELEASES", "3")),
            keep_downloads=int(os.environ.get("KEEP_DOWNLOADS", "3")),
        )


class DeployLock:
    def __init__(self, lock_file: Path) -> None:
        self.lock_file = lock_file
        self.handle = None

    def __enter__(self) -> "DeployLock":
        self.lock_file.parent.mkdir(parents=True, exist_ok=True)
        if fcntl is None:
            return self
        self.handle = self.lock_file.open("w")
        try:
            fcntl.flock(self.handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            self.handle.close()
            raise DeployApplyError("deploy already running") from exc
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if self.handle is not None:
            fcntl.flock(self.handle.fileno(), fcntl.LOCK_UN)
            self.handle.close()


def apply_deploy(config: DeployConfig, site_url: str, site_sha: str, release_id: str) -> None:
    _validate_release_id(release_id)
    project_dir = config.project_dir
    runtime_dir = project_dir / "runtime"
    releases_dir = runtime_dir / "releases"
    downloads_dir = runtime_dir / "downloads"
    current_link = runtime_dir / "current"
    release_dir = releases_dir / release_id
    archive_path = downloads_dir / f"{config.site_slug}-{release_id}.tar.gz"

    with DeployLock(config.lock_file):
        print(f"starting {config.site_slug} deploy for {release_id}")
        project_dir.mkdir(parents=True, exist_ok=True)
        runtime_dir.mkdir(parents=True, exist_ok=True)
        releases_dir.mkdir(parents=True, exist_ok=True)
        downloads_dir.mkdir(parents=True, exist_ok=True)
        _chmod(project_dir, DIR_MODE)
        _chmod(runtime_dir, DIR_MODE)
        _chmod(releases_dir, DIR_MODE)
        _chmod(downloads_dir, DIR_MODE)

        staging_parent = Path(tempfile.mkdtemp(prefix=".deploy-", dir=str(releases_dir)))
        staging_release = staging_parent / release_id
        try:
            _download(site_url, archive_path)
            _verify_sha256(archive_path, site_sha)
            staging_release.mkdir(parents=True)
            _extract_archive(archive_path, staging_release)
            _normalise_release_tree(staging_release)
            _require_dir(staging_release / "out")

            if release_dir.exists() or release_dir.is_symlink():
                _remove_path(release_dir)
            os.replace(staging_release, release_dir)

            _replace_symlink(Path("releases") / release_id, current_link)
            _install_runtime_files(project_dir, release_dir)
            _prune_releases(releases_dir, config.keep_releases)
            _prune_downloads(downloads_dir, config.keep_downloads)
        finally:
            _remove_path(staging_parent)

        print(f"{config.site_slug} deploy finished for {release_id}")


def _validate_release_id(release_id: str) -> None:
    if not release_id or Path(release_id).name != release_id or release_id in {".", ".."}:
        raise DeployApplyError("invalid release id")


def _download(url: str, output: Path) -> None:
    headers = {}
    token = os.environ.get("GITHUB_TOKEN", "")
    if token and url.startswith("https://api.github.com/"):
        headers = {"Authorization": f"Bearer {token}", "Accept": "application/octet-stream"}
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=90) as response, output.open("wb") as handle:
        shutil.copyfileobj(response, handle)


def _verify_sha256(path: Path, expected: str) -> None:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    actual = digest.hexdigest()
    if actual.lower() != expected.lower():
        raise DeployApplyError(f"checksum mismatch for {path}")


def _extract_archive(archive_path: Path, destination: Path) -> None:
    destination_root = destination.resolve()
    with tarfile.open(archive_path, "r:gz") as archive:
        for member in archive.getmembers():
            target = (destination / member.name).resolve()
            if not str(target).startswith(f"{destination_root}{os.sep}") and target != destination_root:
                raise DeployApplyError("archive contains unsafe path")
        try:
            archive.extractall(destination, filter="data")
        except TypeError:
            archive.extractall(destination)


def _require_dir(path: Path) -> None:
    if not path.is_dir():
        raise DeployApplyError(f"release archive missing directory: {path.name}")


def _replace_symlink(target: Path, link_path: Path) -> None:
    link_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_link = link_path.with_name(f".{link_path.name}.tmp-{os.getpid()}")
    _remove_path(tmp_link)
    os.symlink(str(target), tmp_link)
    os.replace(tmp_link, link_path)


def _install_runtime_files(project_dir: Path, release_dir: Path) -> None:
    deploy_script = release_dir / "deploy.sh"
    if deploy_script.is_file():
        shutil.copy2(deploy_script, project_dir / "deploy.sh")
        _chmod(project_dir / "deploy.sh", EXEC_MODE)
    for dirname in ("scripts", "ops"):
        source = release_dir / dirname
        if not source.is_dir():
            continue
        target = project_dir / dirname
        target.mkdir(parents=True, exist_ok=True)
        _chmod(target, DIR_MODE)
        for path in source.iterdir():
            if path.is_file():
                shutil.copy2(path, target / path.name)
                _chmod(target / path.name, EXEC_MODE if path.suffix == ".py" or path.name.endswith(".sh") else FILE_MODE)


def _normalise_release_tree(path: Path) -> None:
    _chmod(path, DIR_MODE)
    for child in path.rglob("*"):
        if child.is_dir():
            _chmod(child, DIR_MODE)
        elif child.is_file():
            _chmod(child, FILE_MODE)
    for candidate in (
        path / "deploy.sh",
        path / "scripts" / "build-release.sh",
        path / "scripts" / "deploy_apply.py",
        path / "scripts" / "poll_release.py",
        path / "scripts" / "release_manifest.py",
    ):
        if candidate.is_file():
            _chmod(candidate, EXEC_MODE)


def _chmod(path: Path, mode: int) -> None:
    path.chmod(mode)


def _prune_releases(releases_dir: Path, keep_releases: int) -> None:
    keep_releases = max(1, keep_releases)
    releases = [
        path
        for path in releases_dir.iterdir()
        if not path.name.startswith(".deploy-") and (path.is_dir() or path.is_symlink())
    ]
    releases.sort(key=lambda path: path.stat().st_mtime, reverse=True)
    for path in releases[keep_releases:]:
        _remove_path(path)


def _prune_downloads(downloads_dir: Path, keep_downloads: int) -> None:
    keep_downloads = max(1, keep_downloads)
    downloads = [path for path in downloads_dir.iterdir() if path.is_file()]
    downloads.sort(key=lambda path: path.stat().st_mtime, reverse=True)
    for path in downloads[keep_downloads:]:
        _remove_path(path)


def _remove_path(path: Path) -> None:
    if path.is_symlink() or path.is_file():
        path.unlink()
    elif path.is_dir():
        shutil.rmtree(path)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("site_url")
    parser.add_argument("site_sha")
    parser.add_argument("release_id")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    apply_deploy(DeployConfig.from_env(), args.site_url, args.site_sha, args.release_id)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv[1:]))
    except DeployApplyError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)
