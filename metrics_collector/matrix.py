"""
Build a dependency / adoption matrix cross-referencing repositories,
their workflow counts, monthly runs, and total runs.

Artifacts
---------
- ``dependency_matrix.json``  — full matrix as JSON.
- ``dependency_matrix.csv``   — flat CSV for spreadsheet import.
"""

from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------


def build(
    adoption: Dict[str, Any],
    workflow_data: Dict[str, Any],
    output_dir: str | Path = "metrics-output",
) -> List[Dict[str, Any]]:
    """Join discovery results with workflow-run data into a dependency matrix.

    Parameters
    ----------
    adoption : dict
        Output from ``discovery.discover()``.
    workflow_data : dict
        Output from ``workflows.collect()``.
    output_dir : str or Path
        Directory to write artifacts into.

    Returns
    -------
    list[dict]
        Rows of the matrix sorted by monthly runs descending.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    top = workflow_data.get("top_consumers", [])
    lookup: Dict[str, Dict[str, int]] = {
        item["repository"]: {
            "monthly_runs": item["monthly_runs"],
            "total_runs": item["total_runs"],
        }
        for item in top
    }

    repo_workflow_counts = adoption.get("repo_workflow_counts", {})
    rows: List[Dict[str, Any]] = []
    for repo in adoption.get("repos_list", []):
        info = lookup.get(repo, {"monthly_runs": 0, "total_runs": 0})
        rows.append(
            {
                "repository": repo,
                "organization": repo.split("/", 1)[0],
                "workflow_files": repo_workflow_counts.get(repo, 0),
                "monthly_runs": info["monthly_runs"],
                "total_runs": info["total_runs"],
            }
        )

    rows.sort(key=lambda r: r["monthly_runs"], reverse=True)

    _write_json(rows, output_dir)
    _write_csv(rows, output_dir)

    print(f"[matrix] Built {len(rows)}-row dependency matrix.")

    return rows


# ---------------------------------------------------------------------------
# Output writers
# ---------------------------------------------------------------------------


def _write_json(matrix: List[Dict[str, Any]], output_dir: Path) -> Path:
    path = output_dir / "dependency_matrix.json"
    payload = {
        "generated_at": datetime.now().isoformat(),
        "total_repositories": len(matrix),
        "total_monthly_runs": sum(r["monthly_runs"] for r in matrix),
        "total_runs": sum(r["total_runs"] for r in matrix),
        "rows": matrix,
    }
    path.write_text(json.dumps(payload, indent=2))
    print(f"         JSON → {path}")
    return path


def _write_csv(matrix: List[Dict[str, Any]], output_dir: Path) -> Path:
    path = output_dir / "dependency_matrix.csv"
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "repository", "organization", "workflow_files",
                "monthly_runs", "total_runs",
            ],
        )
        writer.writeheader()
        writer.writerows(matrix)
    print(f"         CSV  → {path}")
    return path
