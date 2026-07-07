"""
Centralised configuration for metrics collection.

All tunable values live here so that individual modules stay focused
on logic rather than hard-coded strings.

Environment variables
---------------------
GITHUB_TOKEN          — Personal access token (classic or fine-grained) with
                        ``repo``, ``workflow``, and ``read:org`` scopes.
GITHUB_ENTERPRISE_URL — Optional. If set, search and API calls target this
                        base URL instead of github.com.
METRICS_OUTPUT_DIR    — Directory where JSON/CSV artifacts are written.
                        Defaults to ``./metrics-output``.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_OUTPUT_DIR = Path("metrics-output")

# The action / reusable workflow we are searching for.
SETUP_PYTHON_ACTION = "ibm/setup-python-pz"
PYTHON_VERSIONS_REPO = "ibm/python-versions-pz"

# Architectures tracked in releases.
ARCHITECTURES = ["ppc64le", "s390x"]

# How far back to look for workflow runs (in days).
WORKFLOW_LOOKBACK_DAYS = 90


# ---------------------------------------------------------------------------
# Configuration dataclass
# ---------------------------------------------------------------------------


@dataclass
class Config:
    """Aggregated, validated configuration for the metrics collector."""

    # GitHub authentication
    github_token: str = ""

    # API base URL — overridden when targeting a GitHub Enterprise instance.
    github_api_base: str = "https://api.github.com"
    github_search_base: str = "https://api.github.com"

    # The action / reusable workflow we are searching for.
    setup_python_action: str = SETUP_PYTHON_ACTION
    python_versions_repo: str = PYTHON_VERSIONS_REPO

    # Architectures tracked in releases.
    architectures: List[str] = field(default_factory=lambda: list(ARCHITECTURES))

    # Lookback window for workflow runs (days).
    workflow_lookback_days: int = WORKFLOW_LOOKBACK_DAYS

    # Output directory for generated artifacts.
    output_dir: Path = DEFAULT_OUTPUT_DIR

    # Headers used for every GitHub API request.
    @property
    def headers(self) -> Dict[str, str]:
        h = {
            "Accept": "application/vnd.github+json",
            "User-Agent": "metrics-collector/1.0",
        }
        if self.github_token:
            h["Authorization"] = f"Bearer {self.github_token}"
        return h


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def load_config() -> Config:
    """Build a ``Config`` from environment variables and sensible defaults."""
    token = os.environ.get("GITHUB_TOKEN", "")
    enterprise_url = os.environ.get("GITHUB_ENTERPRISE_URL", "")

    cfg = Config(github_token=token)

    if enterprise_url:
        # Strip trailing slash, then derive API and search URLs.
        enterprise_url = enterprise_url.rstrip("/")
        cfg.github_api_base = f"{enterprise_url}/api/v3"
        cfg.github_search_base = f"{enterprise_url}/api/v3"

    output_env = os.environ.get("METRICS_OUTPUT_DIR")
    if output_env:
        cfg.output_dir = Path(output_env)

    return cfg
