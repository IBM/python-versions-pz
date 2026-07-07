"""
Collect release and download-count metrics for ``python-versions-pz``.

Uses the GitHub Releases API to fetch all releases and their assets, then
aggregates download counts by Python version and architecture.

Artifact
--------
``releases_summary.json`` — total releases, total downloads, downloads
grouped by version (popularity) and by architecture (ppc64le / s390x).
"""

from __future__ import annotations

import json
import re
import time
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List

import requests

from metrics_collector.config import Config


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_VERSION_PATTERN = re.compile(
    r"python-(?P<version>\d+\.\d+\.\d+(?:rc\d+)?(?:alpha\d+)?(?:beta\d+)?)"
)


def _parse_version(asset_name: str) -> str | None:
    m = _VERSION_PATTERN.search(asset_name)
    return m.group("version") if m else None


def _parse_architecture(asset_name: str) -> str | None:
    for arch in ("ppc64le", "s390x"):
        if arch in asset_name:
            return arch
    return None


def _list_releases(cfg: Config) -> List[Dict[str, Any]]:
    owner, repo = cfg.python_versions_repo.split("/", 1)
    releases: List[Dict[str, Any]] = []
    url = f"{cfg.github_api_base}/repos/{owner}/{repo}/releases"
    page = 1

    while True:
        resp = requests.get(
            url, headers=cfg.headers, params={"per_page": 100, "page": page}
        )
        if resp.status_code == 404:
            print(f"[releases] Repository '{cfg.python_versions_repo}' not found.")
            return []
        resp.raise_for_status()
        batch = resp.json()
        if not batch:
            break
        releases.extend(batch)
        if len(batch) < 100:
            break
        page += 1
        time.sleep(0.3)

    return releases


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------


def collect(cfg: Config) -> Dict[str, Any]:
    """Fetch releases and produce aggregated release metrics.

    Returns a dict with:
    - ``total_releases``, ``total_assets``, ``total_downloads``.
    - ``downloads_by_version`` — ``{version: count}`` sorted by popularity.
    - ``downloads_by_arch`` — ``{arch: count}``.
    """
    output_dir = cfg.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"[releases] Fetching releases for {cfg.python_versions_repo} …")
    releases = _list_releases(cfg)

    total_assets = 0
    total_downloads = 0
    downloads_by_version: Dict[str, int] = defaultdict(int)
    downloads_by_arch: Dict[str, int] = defaultdict(int)

    for release in releases:
        for asset in release.get("assets", []):
            name = asset.get("name", "")
            downloads = asset.get("download_count", 0)
            version = _parse_version(name)
            arch = _parse_architecture(name)

            total_assets += 1
            total_downloads += downloads

            if version:
                downloads_by_version[version] += downloads
            if arch:
                downloads_by_arch[arch] += downloads

    version_popularity = dict(
        sorted(downloads_by_version.items(), key=lambda x: x[1], reverse=True)
    )

    aggregated = {
        "total_releases": len(releases),
        "total_assets": total_assets,
        "total_downloads": total_downloads,
        "downloads_by_version": version_popularity,
        "downloads_by_arch": dict(downloads_by_arch),
    }

    _write_summary_json(aggregated, output_dir)

    print(f"[releases] {aggregated['total_releases']} release(s), "
          f"{aggregated['total_assets']} asset(s), "
          f"{aggregated['total_downloads']} download(s)")

    return aggregated


# ---------------------------------------------------------------------------
# Output writers
# ---------------------------------------------------------------------------


def _write_summary_json(aggregated: Dict[str, Any], output_dir: Path) -> Path:
    path = output_dir / "releases_summary.json"
    path.write_text(json.dumps(aggregated, indent=2, default=str))
    print(f"           JSON → {path}")
    return path
