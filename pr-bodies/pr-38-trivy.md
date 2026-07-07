## Context

The release build was failing in the Trivy verification path before the Python build could proceed. The Trivy version pin, checksum validation, and install logic were split across multiple places, which made failures harder to reason about and update.

## What changed

- Add `.trivyversion` as the repository source of truth for the pinned Trivy release.
- Add `scripts/verify-trivy.sh` to verify the requested release tag and the pinned checksums.
- Add `scripts/update-trivy-checksums.sh` to refresh the checksum file from the upstream Trivy release.
- Move the container-side install logic into `python-versions/install-trivy.sh`.
- Centralize Trivy asset naming in `python-versions/trivy-assets.sh`.
- Update `Makefile`, `python-versions/Dockerfile`, and the reusable build workflow to use the new verification/install flow.

## Why this shape

This keeps the Trivy pin, verification, and install path aligned so the same pinned metadata is used both on the host and inside the Docker build.

## Validation

- Verified shell syntax for the added and updated scripts.
- Ran the local checksum verification path against the pinned Trivy version.
- Linted the changed reusable workflow with `actionlint`.
