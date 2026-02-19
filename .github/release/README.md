## Filter Configuration for release-matching-python-tags.yml

The release-matching workflow uses a YAML-based filter file to control which Python versions are released.

### Filter File Location
`.github/release/python-tag-filter.txt`

### Format
The file uses YAML format with the following fields:

- **version**: A glob pattern to match Python versions (e.g., `3.14.*`, `3.13.*`)
- **release_types**: An array of release types to include. Valid values:
  - `stable` - Production releases (e.g., 3.14.0, 3.13.5)
  - `beta` - Beta releases (e.g., 3.14.0b1)
  - `rc` - Release candidates (e.g., 3.14.0rc1)
  - `alpha` - Alpha releases (e.g., 3.14.0a1)

### Examples

**Example 1: Only stable 3.14.x releases**
```yaml
version: 3.14.*
release_types: [stable]
```

**Example 2: Both stable and beta (multi-line format)**
```yaml
version: 3.13.*
release_types:
  - stable
  - beta
```

**Example 3: All release types**
```yaml
version: 3.12.*
release_types: [stable, beta, rc, alpha]
```

### Behavior

- If the filter file is missing or empty, the workflow automatically derives a filter from the latest stable Python version
- The filter pattern is converted to a wildcard format (e.g., `3.14.5` → `3.14.*`)
- The workflow will release all versions matching both the version pattern AND the specified release types

### Triggering the Workflow

The workflow is triggered in two ways:
1. **Manual trigger**: `workflow_dispatch` (manual run in GitHub Actions UI)
2. **Automatic trigger**: Any push to `.github/release/python-tag-filter.txt`

Simply commit and push changes to this file to automatically trigger a release for matching versions.


## Legacy: Override for release-latest-python-tag.yml

To temporarily override the Python version released by the Release Latest Python Tag workflow, create a file at:

.github/release/python-tag-override.txt

Put a single line with the desired version, for example:

3.13.4

Commit and push that change to the repository. The next manual run of the workflow (workflow_dispatch) will use this tag. Delete the file (or leave it empty) to return to automatic latest-stable detection.
