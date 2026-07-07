"""
metrics-collector — Unified CLI entry point.

Usage
-----
Collect all metrics (adoption + consumption) in one pass:

    GITHUB_TOKEN=$(gh auth token) python -m metrics_collector.cli collect

Run individual steps:

    python -m metrics_collector.cli search
    python -m metrics_collector.cli runs
    python -m metrics_collector.cli releases
    python -m metrics_collector.cli matrix
    python -m metrics_collector.cli summary

Advanced options:

    GITHUB_ENTERPRISE_URL=https://github.mycompany.com python -m ... collect
    METRICS_OUTPUT_DIR=/tmp/my-metrics python -m ... collect
    python -m ... runs --lookback-days 30
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import typer

from metrics_collector.config import load_config, Config
from metrics_collector.discovery import discover
from metrics_collector.workflows import collect as collect_workflow_runs
from metrics_collector.releases import collect as collect_releases
from metrics_collector.matrix import build as build_matrix
from metrics_collector.summary import generate as generate_summary

# ---------------------------------------------------------------------------
# Typer app
# ---------------------------------------------------------------------------

app = typer.Typer(
    name="metrics-collector",
    help="Collect GitHub adoption and consumption metrics for "
         "setup-python-pz / python-versions-pz.",
    add_completion=False,
)


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _cfg(
    output_dir: Optional[str] = None,
    lookback_days: Optional[int] = None,
) -> Config:
    cfg = load_config()
    if output_dir:
        cfg.output_dir = Path(output_dir)
    if lookback_days is not None:
        cfg.workflow_lookback_days = lookback_days
    return cfg


def _require_token(cfg: Config) -> None:
    if not cfg.github_token:
        typer.secho(
            "ERROR: GITHUB_TOKEN environment variable is not set.\n"
            "Set it to a personal access token with repo, workflow, "
            "and read:org scopes.",
            fg=typer.colors.RED,
            err=True,
        )
        raise typer.Exit(code=1)


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


@app.command()
def search(
    output_dir: Optional[str] = typer.Option(
        None, "--output-dir", "-o", help="Override METRICS_OUTPUT_DIR."
    ),
) -> None:
    """Step 1: Discover repositories using setup-python-pz."""
    cfg = _cfg(output_dir)
    _require_token(cfg)
    result = discover(cfg)
    _save_intermediate(cfg, "adoption", result)
    typer.secho("✓ discovery complete", fg=typer.colors.GREEN)


@app.command()
def runs(
    output_dir: Optional[str] = typer.Option(
        None, "--output-dir", "-o", help="Override METRICS_OUTPUT_DIR."
    ),
    lookback_days: Optional[int] = typer.Option(
        None, "--lookback-days", "-l", help="Workflow run lookback window."
    ),
) -> None:
    """Step 2: Collect workflow-run metrics for discovered repos."""
    cfg = _cfg(output_dir, lookback_days)
    _require_token(cfg)
    adoption = _load_intermediate(cfg, "adoption")
    repos = adoption.get("repos_list", [])
    if not repos:
        typer.secho(
            "No repos found. Run 'search' first or check GITHUB_TOKEN scopes.",
            fg=typer.colors.YELLOW,
            err=True,
        )
        raise typer.Exit(code=1)
    result = collect_workflow_runs(cfg, repos)
    _save_intermediate(cfg, "workflows", result)
    typer.secho("✓ workflow-runs complete", fg=typer.colors.GREEN)


@app.command()
def releases(
    output_dir: Optional[str] = typer.Option(
        None, "--output-dir", "-o", help="Override METRICS_OUTPUT_DIR."
    ),
) -> None:
    """Step 3: Collect release assets and download counts."""
    cfg = _cfg(output_dir)
    _require_token(cfg)
    result = collect_releases(cfg)
    _save_intermediate(cfg, "releases", result)
    typer.secho("✓ releases complete", fg=typer.colors.GREEN)


@app.command()
def matrix(
    output_dir: Optional[str] = typer.Option(
        None, "--output-dir", "-o", help="Override METRICS_OUTPUT_DIR."
    ),
) -> None:
    """Step 4: Build the dependency / adoption matrix."""
    cfg = _cfg(output_dir)
    adoption = _load_intermediate(cfg, "adoption")
    wf = _load_intermediate(cfg, "workflows")
    build_matrix(adoption, wf, cfg.output_dir)
    typer.secho("✓ matrix complete", fg=typer.colors.GREEN)


@app.command()
def summary(
    output_dir: Optional[str] = typer.Option(
        None, "--output-dir", "-o", help="Override METRICS_OUTPUT_DIR."
    ),
) -> None:
    """Step 5: Produce the executive summary."""
    cfg = _cfg(output_dir)
    adoption = _load_intermediate(cfg, "adoption")
    wf = _load_intermediate(cfg, "workflows")
    rel = _load_intermediate(cfg, "releases")
    generate_summary(adoption, wf, rel, cfg.output_dir)
    typer.secho("✓ summary complete", fg=typer.colors.GREEN)


@app.command()
def collect(
    output_dir: Optional[str] = typer.Option(
        None, "--output-dir", "-o", help="Override METRICS_OUTPUT_DIR."
    ),
    lookback_days: Optional[int] = typer.Option(
        None, "--lookback-days", "-l", help="Workflow run lookback window."
    ),
) -> None:
    """Run the full pipeline: search → runs → releases → matrix → summary."""
    cfg = _cfg(output_dir, lookback_days)
    _require_token(cfg)

    # 1 — Discovery
    typer.secho("── Step 1/5: Repository discovery ──", bold=True)
    adoption = discover(cfg)
    _save_intermediate(cfg, "adoption", adoption)

    repos = adoption.get("repos_list", [])
    if not repos:
        typer.secho(
            "No repositories found. Check your GITHUB_TOKEN scopes.",
            fg=typer.colors.YELLOW,
        )
        raise typer.Exit(code=1)

    # 2 — Workflow runs
    typer.secho("── Step 2/5: Workflow runs ──", bold=True)
    wf_result = collect_workflow_runs(cfg, repos)
    _save_intermediate(cfg, "workflows", wf_result)

    # 3 — Releases
    typer.secho("── Step 3/5: Releases ──", bold=True)
    rel_result = collect_releases(cfg)
    _save_intermediate(cfg, "releases", rel_result)

    # 4 — Matrix
    typer.secho("── Step 4/5: Dependency matrix ──", bold=True)
    build_matrix(adoption, wf_result, cfg.output_dir)

    # 5 — Summary
    typer.secho("── Step 5/5: Executive summary ──", bold=True)
    generate_summary(adoption, wf_result, rel_result, cfg.output_dir)

    typer.secho("✓ Full pipeline complete!", fg=typer.colors.GREEN, bold=True)


# ---------------------------------------------------------------------------
# Intermediate state persistence
# ---------------------------------------------------------------------------

_INTERMEDIATE_DIR = Path(".metrics-intermediate")


def _save_intermediate(cfg: Config, name: str, data: dict) -> None:
    d = _INTERMEDIATE_DIR
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{name}.json").write_text(json.dumps(data, indent=2, default=str))


def _load_intermediate(cfg: Config, name: str) -> dict:
    path = _INTERMEDIATE_DIR / f"{name}.json"
    if not path.exists():
        typer.secho(
            f"Intermediate file '{path}' not found. "
            f"Run the relevant step first.",
            fg=typer.colors.RED,
            err=True,
        )
        raise typer.Exit(code=1)
    return json.loads(path.read_text())


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    app()
