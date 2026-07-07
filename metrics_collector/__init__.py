"""
metrics_collector — A toolkit for collecting GitHub adoption and consumption metrics.

This package provides a set of modular scripts that collect metrics from
GitHub (code search, REST API, Releases API) to answer enterprise client
questions about usage of the ``setup-python-pz`` and ``python-versions-pz``
repositories.

Modules
-------
config      — Centralised configuration (tokens, owners, repos).
discovery   — Repository discovery via GitHub code search.
workflows   — Workflow-run collection and aggregation.
releases    — Release asset and download-count collection.
matrix      — Dependency/adoption matrix construction.
summary     — Executive summary aggregation.
cli         — Unified CLI (Typer) entry point.
"""
from metrics_collector import config
from metrics_collector import discovery
from metrics_collector import workflows
from metrics_collector import releases
from metrics_collector import matrix
from metrics_collector import summary

__all__ = [
    "config",
    "discovery",
    "workflows",
    "releases",
    "matrix",
    "summary",
]
