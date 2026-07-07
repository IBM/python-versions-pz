## Context

This is a maintenance-only PR. It keeps the repository workflows up to date and
includes the checked-in PowerShell tag override used by the tar-generation
flow.

## What changed

- Update the workflow action versions used by the repository workflows.
- Refresh the release and test workflows to newer action majors.
- Carry `.github/release/powershell-tag-override.txt` for the tar-generation flow.

## Why this shape

Keeping these changes in a dedicated chore PR avoids mixing workflow
maintenance with the functional build fixes.

## Validation

- Ran `actionlint` on the changed workflow files.
- `actionlint` reported shellcheck warnings in some workflow scripts, but no workflow syntax errors.
