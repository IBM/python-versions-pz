"""
Collect workflow-run metrics for every repository using ``setup-python-pz``.

Uses the GitHub Actions REST API to iterate workflows, list runs, and aggregate
them by day, week, month, and total.

Artifact
--------
``workflow_runs.csv`` — per-repo run counts (workflows, daily/weekly/monthly/total).
"""

from __future__ import annotations

import csv
import json
import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List

import requests

from metrics_collector.config import Config


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _list_workflows(cfg: Config, owner: str, repo: str) -> List[Dict[str, Any]]:
    url = f"{cfg.github_api_base}/repos/{owner}/{repo}/actions/workflows"
    resp = requests.get(url, headers=cfg.headers)
    if resp.status_code == 404:
        return []
    resp.raise_for_status()
    return resp.json().get("workflows", [])


def _list_workflow_runs(
    cfg: Config,
    owner: str,
    repo: str,
    workflow_id: int,
    since: datetime,
) -> List[Dict[str, Any]]:
    runs: List[Dict[str, Any]] = []
    url = f"{cfg.github_api_base}/repos/{owner}/{repo}/actions/workflows/{workflow_id}/runs"
    params: Dict[str, Any] = {
        "per_page": 100,
        "page": 1,
        "created": f">={since.isoformat()}",
    }

    for page in range(1, 101):
        params["page"] = page
        resp = requests.get(url, headers=cfg.headers, params=params)
        if resp.status_code == 404:
            break
        resp.raise_for_status()
        data = resp.json()
        batch = data.get("workflow_runs", [])
        runs.extend(batch)
        if len(batch) < 100:
            break
        time.sleep(0.2)

    return runs


def _classify_runs(
    runs: List[Dict[str, Any]],
    lookback: int,
) -> Dict[str, int]:
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=lookback)
    one_week_ago = now - timedelta(days=7)
    one_day_ago = now - timedelta(days=1)

    counts: Dict[str, int] = {"daily": 0, "weekly": 0, "monthly": 0, "total": len(runs)}
    for run in runs:
        created_str = run.get("run_started_at") or run.get("created_at")
        if not created_str:
            continue
        created = datetime.fromisoformat(created_str)
        if created >= one_day_ago:
            counts["daily"] += 1
        if created >= one_week_ago:
            counts["weekly"] += 1
        if created >= cutoff:
            counts["monthly"] += 1
    return counts


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------


def collect(
    cfg: Config,
    repos: List[str],
) -> Dict[str, Any]:
    """Collect workflow-run metrics for every repository in *repos*.

    Returns a dict with:
    - ``daily_runs``, ``weekly_runs``, ``monthly_runs``, ``total_runs``.
    - ``top_consumers`` — sorted descending by monthly runs.
    """
    output_dir = cfg.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    since = datetime.now(timezone.utc) - timedelta(days=cfg.workflow_lookback_days)
    per_repo: Dict[str, Any] = {}
    totals: Dict[str, int] = {"daily": 0, "weekly": 0, "monthly": 0, "total": 0}

    print(f"[workflows] Collecting runs for {len(repos)} repo(s) …")

    for repo_full in repos:
        owner, repo_name = repo_full.split("/", 1)
        workflows = _list_workflows(cfg, owner, repo_name)
        repo_runs: List[Dict[str, Any]] = []

        for wf in workflows:
            wf_runs = _list_workflow_runs(cfg, owner, repo_name, wf["id"], since)
            for r in wf_runs:
                repo_runs.append(
                    {
                        "workflow_id": wf["id"],
                        "workflow_name": wf.get("name", ""),
                        "workflow_path": wf.get("path", ""),
                        "run_id": r["id"],
                        "run_number": r.get("run_number"),
                        "status": r.get("status"),
                        "conclusion": r.get("conclusion"),
                        "created_at": r.get("created_at"),
                        "run_started_at": r.get("run_started_at"),
                        "html_url": r.get("html_url"),
                        "actor": r.get("actor", {}).get("login") if r.get("actor") else None,
                    }
                )
            time.sleep(0.15)

        counts = _classify_runs(repo_runs, cfg.workflow_lookback_days)
        per_repo[repo_full] = {
            "repository": repo_full,
            "workflows_count": len(workflows),
            "runs_count": len(repo_runs),
            "daily_runs": counts["daily"],
            "weekly_runs": counts["weekly"],
            "monthly_runs": counts["monthly"],
            "total_runs": counts["total"],
        }

        for key in totals:
            totals[key] += counts[key]

        if repo_runs:
            print(f"  {repo_full}: {len(repo_runs)} run(s) "
                  f"(daily={counts['daily']}, weekly={counts['weekly']}, "
                  f"monthly={counts['monthly']})")

    top_consumers = sorted(
        (
            {"repository": k, "monthly_runs": v["monthly_runs"], "total_runs": v["total_runs"]}
            for k, v in per_repo.items()
        ),
        key=lambda x: x["monthly_runs"],
        reverse=True,
    )

    _write_csv(per_repo, output_dir)

    print(f"[workflows] Totals — daily={totals['daily']}, "
          f"weekly={totals['weekly']}, monthly={totals['monthly']}, "
          f"total={totals['total']}")

    return {
        "daily_runs": totals["daily"],
        "weekly_runs": totals["weekly"],
        "monthly_runs": totals["monthly"],
        "total_runs": totals["total"],
        "top_consumers": top_consumers,
    }


# ---------------------------------------------------------------------------
# Output writers
# ---------------------------------------------------------------------------


def _write_csv(per_repo: Dict[str, Any], output_dir: Path) -> Path:
    path = output_dir / "workflow_runs.csv"
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "repository", "workflows_count", "runs_count",
                "daily_runs", "weekly_runs", "monthly_runs", "total_runs",
            ],
        )
        writer.writeheader()
        for data in per_repo.values():
            writer.writerow({k: data[k] for k in writer.fieldnames})
    print(f"               CSV → {path}")
    return path
