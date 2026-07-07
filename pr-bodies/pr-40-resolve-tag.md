## Context

When `PYTHON_VERSION` moved forward, the build could still keep using an older,
manually pinned `ACTIONS_PYTHON_VERSIONS` value. In practice, that meant a
release such as `3.14.5` could still build from the wrong
`actions/python-versions` snapshot.

As a result, the release build was not guaranteed to use the upstream snapshot
that actually matched the Python version we were trying to publish.

## What changed

- Add `scripts/resolve-upstream-tag.sh` to query the upstream `actions/python-versions` release metadata and resolve the matching source tag for a requested Python version.
- Update `Makefile` so `ACTIONS_PYTHON_VERSIONS` is derived from `PYTHON_VERSION` on the host before the Docker build starts, while still allowing an explicit override when needed.
- Sync the default Python-related ARGs in `python-versions/Dockerfile` with the requested release line.

## Why this shape

This keeps upstream snapshot selection tied to the requested Python version
instead of depending on a separately maintained tag value.

## Validation

- Verified shell syntax for `scripts/resolve-upstream-tag.sh`.
- Ran the script locally for `3.14.5` and confirmed it resolved the expected upstream tag.
