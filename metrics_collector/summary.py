"""
Produce an executive summary aggregating all collected metrics into a
single, client-ready report.

Artifacts
---------
- ``executive_summary.json``  — structured summary for programmatic consumption.
- ``executive_summary.csv``   — single-row CSV with all KPIs.
"""

from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------


def generate(
    adoption: Dict[str, Any],
    workflow_data: Dict[str, Any],
    release_data: Dict[str, Any],
    output_dir: str | Path = "metrics-output",
) -> Dict[str, Any]:
    """Merge all collected data into a single executive summary.

    Parameters
    ----------
    adoption : dict
        Output from ``discovery.discover()``.
    workflow_data : dict
        Output from ``workflows.collect()``.
    release_data : dict
        Output from ``releases.collect()``.
    output_dir : str or Path
        Directory to write artifacts into.

    Returns
    -------
    dict
        All KPIs in one structure.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    version_popularity = release_data.get("downloads_by_version", {})
    supported_versions = sorted(version_popularity.keys())
    arch_data = release_data.get("downloads_by_arch", {})

    summary: Dict[str, Any] = {
        "organizations_using_setup_python_pz": adoption.get("organizations", 0),
        "repositories_using_setup_python_pz": adoption.get("repositories", 0),
        "workflow_files": adoption.get("workflow_files", 0),
        "monthly_workflow_runs": workflow_data.get("monthly_runs", 0),
        "weekly_workflow_runs": workflow_data.get("weekly_runs", 0),
        "daily_workflow_runs": workflow_data.get("daily_runs", 0),
        "total_workflow_runs": workflow_data.get("total_runs", 0),
        "total_releases": release_data.get("total_releases", 0),
        "total_release_downloads": release_data.get("total_downloads", 0),
        "total_release_assets": release_data.get("total_assets", 0),
        "supported_python_versions": len(supported_versions),
        "supported_python_versions_list": supported_versions,
        "python_version_popularity": version_popularity,
        "supported_architectures": len(arch_data),
        "supported_architectures_list": sorted(arch_data.keys()),
        "architecture_downloads": arch_data,
        "top_consumers": workflow_data.get("top_consumers", []),
        "generated_at": datetime.now().isoformat(),
    }

    _write_json(summary, output_dir)
    _write_csv(summary, output_dir)

    print("[summary] Executive summary generated.")
    for k in (
        "organizations_using_setup_python_pz",
        "repositories_using_setup_python_pz",
        "total_release_downloads",
        "monthly_workflow_runs",
    ):
        print(f"            {k}: {summary[k]}")

    return summary


# ---------------------------------------------------------------------------
# Output writers
# ---------------------------------------------------------------------------


def _write_json(summary: Dict[str, Any], output_dir: Path) -> Path:
    path = output_dir / "executive_summary.json"
    path.write_text(json.dumps(summary, indent=2, default=str))
    print(f"          JSON → {path}")
    return path


def _write_csv(summary: Dict[str, Any], output_dir: Path) -> Path:
    path = output_dir / "executive_summary.csv"

    flat_keys = [
        "organizations_using_setup_python_pz",
        "repositories_using_setup_python_pz",
        "workflow_files",
        "monthly_workflow_runs",
        "weekly_workflow_runs",
        "daily_workflow_runs",
        "total_workflow_runs",
        "total_releases",
        "total_release_downloads",
        "total_release_assets",
        "supported_python_versions",
        "supported_architectures",
    ]

    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=flat_keys)
        writer.writeheader()
        writer.writerow({k: summary.get(k, "") for k in flat_keys})

    print(f"          CSV  → {path}")
    return path
