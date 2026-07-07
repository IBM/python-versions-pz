"""
Discover repositories that use ``setup-python-pz`` via GitHub code search.

Produces one artifact:

``repositories_using_setup_python_pz.csv``
    Flat CSV with repo, workflow path, and file URL — the raw adoption list.
"""

from __future__ import annotations

import csv
import json
import time
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Set

import requests

from metrics_collector.config import Config


# ---------------------------------------------------------------------------
# Search helpers
# ---------------------------------------------------------------------------


def _paginated_search(
    cfg: Config,
    query: str,
    per_page: int = 100,
    max_pages: int = 30,
) -> List[Dict[str, Any]]:
    """Walk paginated GitHub code search results for *query*."""
    items: List[Dict[str, Any]] = []
    url = f"{cfg.github_search_base}/search/code"
    params: Dict[str, Any] = {
        "q": query,
        "per_page": min(per_page, 100),
        "page": 1,
    }

    for page in range(1, max_pages + 1):
        params["page"] = page
        resp = requests.get(url, headers=cfg.headers, params=params)

        if resp.status_code == 403 and "rate limit" in resp.text.lower():
            print("[WARN] Rate-limited on code search.  Stopping pagination.")
            break
        if resp.status_code == 422:
            break
        resp.raise_for_status()

        data = resp.json()
        batch = data.get("items", [])
        items.extend(batch)

        if len(batch) < per_page:
            break

        time.sleep(0.3)

    return items


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------


def discover(cfg: Config) -> Dict[str, Any]:
    """Search for workflow files referencing ``setup-python-pz``.

    Returns a dict with:
    - ``organizations``, ``repositories``, ``workflow_files`` — counts.
    - ``orgs_list``, ``repos_list`` — sorted lists.
    - ``repo_workflow_counts`` — per-repo workflow file count.
    """
    output_dir = cfg.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    query = f"uses: {cfg.setup_python_action}"
    print(f"[discovery] Searching for `{query}` …")
    raw = _paginated_search(cfg, query)

    results: List[Dict[str, Any]] = []
    for item in raw:
        repo_name = item.get("repository", {}).get("full_name", "unknown")
        results.append(
            {
                "repository": repo_name,
                "workflow_path": item.get("path", ""),
                "html_url": item.get("html_url", ""),
            }
        )

    orgs: Set[str] = set()
    repos: Set[str] = set()
    repo_workflow_counts: Dict[str, int] = Counter()
    for r in results:
        repos.add(r["repository"])
        repo_workflow_counts[r["repository"]] += 1
        parts = r["repository"].split("/", 1)
        if len(parts) == 2:
            orgs.add(parts[0])

    print(f"[discovery] Found {len(results)} workflow file(s) across "
          f"{len(repos)} repo(s) / {len(orgs)} org(s).")

    # Persist the raw repo CSV.
    _write_repositories_csv(results, output_dir)

    return {
        "organizations": len(orgs),
        "repositories": len(repos),
        "workflow_files": len(results),
        "orgs_list": sorted(orgs),
        "repos_list": sorted(repos),
        "repo_workflow_counts": dict(repo_workflow_counts),
    }


# ---------------------------------------------------------------------------
# Output writers
# ---------------------------------------------------------------------------


def _write_repositories_csv(
    results: List[Dict[str, Any]],
    output_dir: Path,
) -> Path:
    path = output_dir / "repositories_using_setup_python_pz.csv"
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["repository", "workflow_path", "html_url"])
        writer.writeheader()
        writer.writerows(results)
    print(f"              CSV  → {path}")
    return path
