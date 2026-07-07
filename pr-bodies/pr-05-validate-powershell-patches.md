## Context

The PowerShell v7.6.1 patch inputs (per-arch patch files, native patch, and
generated tarball) are now checked into the repository. Without a CI gate, stale
or missing patches could go unnoticed until the build step fails — and the
failure mode is not immediately obvious to someone looking at a release run.

Adding a scheduled validation workflow catches these failures early and keeps
them visible in the Actions tab, separate from the release pipeline.

## What changed

- Add `.github/workflows/validate-powershell-patches.yml` — a scheduled
  (weekly, Monday 06:00 UTC) and `workflow_dispatch`-triggered workflow that:
  1. Resolves the targeted PowerShell version from the override file or Makefile
     default.
  2. Checks that the per-arch patch, native patch, and generated tarball exist
     and are valid for both `ppc64le` and `s390x`.
  3. Builds the PowerShell image with `make powershell` on both architectures.
  4. Verifies the `pwsh` binary inside the resulting image.

## Why this shape

This follows the same pattern as the existing build workflows — run validation
on the actual build path (`make powershell`) so the check exercises the same
code that the release pipeline uses. Keeping validation in a separate workflow
keeps the release workflows focused on the release itself.

## Validation

- Ran the workflow on `ppc64le` and `s390x` self-hosted runners and verified
  both builds pass.
- Confirmed `pwsh --version` succeeds from each built image.
- Linted the workflow with `actionlint`.
