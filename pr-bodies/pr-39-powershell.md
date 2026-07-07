## Context

The PowerShell `v7.5.1` build was failing in CI. The immediate failure was in
the `.NET` restore/build step: some NuGet packages used by that PowerShell
release had become obsolete and were flagged with CVEs, so `dotnet` refused to
continue the build.

There was a second issue in the same path as well. The GitHub metadata lookup
in `PowerShell/dotnet-install.py` could hit rate limits when it ran without an
authenticated token.

## What changed

- Refresh the PowerShell patch and tar inputs to `v7.6.1` for `ppc64le` and
	`s390x`.
- Update `Makefile` and `PowerShell/Dockerfile` so the PowerShell build can receive the GitHub token as a Docker BuildKit secret.
- Update `PowerShell/dotnet-install.py` to read `GITHUB_TOKEN` or `GITHUB_TOKEN_FILE` and send authenticated GitHub API requests.
- Add test coverage for the authenticated download path in `tests/test_dotnet_install.py`.

## Why this shape

These changes stay together because they fix the same broken build path: move
off the `v7.5.1` inputs that no longer build cleanly, and make the replacement
path more reliable in CI by authenticating the metadata fetch.

## Validation

- Checked Python syntax for the updated Python files.
- Linted the changed reusable workflow with `actionlint`.
- Built the PowerShell image on a remote `ppc64le` VM and verified `pwsh --version` from the resulting image.
