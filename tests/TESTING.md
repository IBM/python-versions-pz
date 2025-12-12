# Test Suite Documentation

## Overview

This comprehensive test suite ensures all Python scripts in the `python-versions-pz` project function correctly and remain compatible with package upgrades. The project uses **Poetry** for dependency management.

## Project Structure

```
tests/
├── __init__.py                          # Test package initialization
├── conftest.py                          # Pytest configuration and shared fixtures
├── test_dotnet_install.py              # Tests for PowerShell/dotnet-install.py
├── test_get_python_version.py          # Tests for .github/scripts/get_python_version.py
├── test_models_and_manifest_tools.py   # Tests for models.py and manifest_tools.py
├── test_package_compatibility.py       # Package upgrade compatibility tests
└── requirements-test.txt               # Test dependencies (legacy format)
```

## Dependencies (via Poetry)

### Production Dependencies

- **requests** >= 2.32.5 - HTTP library for API calls
- **typer** >= 0.19.2 - CLI framework
- **pydantic** >= 2.11.7 - Data validation

### Development Dependencies (Dev Group)

- **pytest** ^7.4.3 - Testing framework
- **pytest-cov** ^4.1.0 - Coverage reporting
- **pytest-mock** ^3.12.0 - Mocking utilities
- **requests-mock** ^1.11.0 - Mock requests library

## Running Tests

### Prerequisites

Install Poetry and dependencies:

```bash
poetry install
```

### Run All Tests

```bash
poetry run pytest
```

### Run with Coverage Report

```bash
poetry run pytest --cov
```

### Run Specific Test File

```bash
poetry run pytest tests/test_dotnet_install.py -v
```

### Run Specific Test Class

```bash
poetry run pytest tests/test_dotnet_install.py::TestVersionParsing -v
```

### Run Specific Test

```bash
poetry run pytest tests/test_dotnet_install.py::TestVersionParsing::test_parse_version_stable -v
```

### Generate HTML Coverage Report

```bash
poetry run pytest --cov --cov-report=html
# Open htmlcov/index.html in browser
```

## Test Files Overview

### 1. test_dotnet_install.py

**Module Under Test:** `PowerShell/dotnet-install.py`

Tests the .NET SDK installer for IBM architectures (s390x, ppc64le).

**Test Classes:**

- `TestVersionParsing` (7 tests) - Version string parsing functionality
- `TestVersionToString` (3 tests) - Converting Version objects back to strings
- `TestNormalizedVersionForNuget` (3 tests) - NuGet version normalization
- `TestIsVersionInNuget` (3 tests) - Checking version existence in NuGet
- `TestResolveTag` (4 tests) - Tag resolution and matching
- `TestFindClosestVersionTag` (3 tests) - Finding closest version match
- `TestFilterAndSortTags` (4 tests) - Filtering and sorting release tags
- `TestGetNugetVersions` (3 tests) - Fetching NuGet versions
- `TestDownloadFile` (3 tests) - File download functionality
- `TestExtractTarball` (2 tests) - Tarball extraction
- `TestFetchJson` (2 tests) - JSON API calls
- `TestGetAllTags` (2 tests) - Fetching GitHub releases
- `TestGetReleaseByTag` (2 tests) - Getting specific release
- `TestSetupEnvironment` (1 test) - Environment variable setup
- `TestVerifyInstallation` (2 tests) - Installation verification
- `TestIntegrationDownloadAndExtract` (1 test) - Integration workflow

**Total: 45 tests**

**Key Functionality Tested:**

- Version parsing with various pre-release formats (alpha, beta, rc, rtm, stable)
- Version comparison and sorting
- NuGet API compatibility
- GitHub API pagination
- File download with error handling
- Tarball extraction
- Environment setup for .NET SDK

### 2. test_get_python_version.py

**Module Under Test:** `.github/scripts/get_python_version.py`

Tests the Python version manifest parser and filter utilities.

**Test Classes:**

- `TestVersionDetection` (9 tests) - Version type detection (stable, alpha, beta, rc)
- `TestVersionParsing` (5 tests) - Parsing version strings
- `TestVersionComparison` (6 tests) - Version comparison logic
- `TestVersionMatchesFilter` (5 tests) - Version pattern filtering
- `TestManifestParsing` (4 tests) - Manifest initialization
- `TestFilterVersions` (7 tests) - Version filtering with various flags
- `TestListVersions` (3 tests) - Listing and sorting versions
- `TestGetLatestVersion` (5 tests) - Getting latest version
- `TestVersionSortingOrder` (3 tests) - Complex sorting scenarios
- `TestEdgeCases` (5 tests) - Edge cases and error conditions

**Total: 52 tests**

**Key Functionality Tested:**

- Alpha, beta, RC, and stable version detection
- Version parsing with various formats
- Version comparison (stable > prerelease)
- Glob pattern filtering (*.*, 3.1*, etc.)
- Stable-only vs. prerelease version listing
- Latest version selection with filters
- Sorting with multiple criteria

### 3. test_models_and_manifest_tools.py

**Modules Under Test:** `.github/scripts/models.py` and `.github/scripts/manifest_tools.py`

Tests Pydantic models and manifest management operations.

**Test Classes:**

- `TestFileEntry` (4 tests) - FileEntry Pydantic model
- `TestManifestEntry` (4 tests) - ManifestEntry Pydantic model
- `TestManifestFetch` (2 tests) - Fetching remote manifests
- `TestManifestMerge` (3 tests) - Merging manifests
- `TestUpdateVersion` (3 tests) - Adding/updating version entries
- `TestPydanticCompatibility` (4 tests) - Pydantic 2.11.7+ compatibility
- `TestManifestIntegration` (1 test) - Full workflow integration

**Total: 21 tests**

**Key Functionality Tested:**

- Pydantic model validation
- Required vs. optional fields
- Model serialization (model_dump, model_json_schema)
- Manifest fetch from remote URLs
- Manifest merging with duplicate detection
- Adding file entries to versions
- Nested Pydantic models
- JSON schema generation

### 4. test_package_compatibility.py

**Purpose:** Verify package upgrade resilience

Tests that the project remains compatible with minimum required package versions.

**Test Classes:**

- `TestRequestsCompatibility` (4 tests) - requests >= 2.32.5
- `TestTyperCompatibility` (6 tests) - typer >= 0.19.2
- `TestPydanticCompatibility` (10 tests) - pydantic >= 2.11.7
- `TestCrossModuleCompatibility` (6 tests) - Inter-module compatibility
- `TestPackageUpgradeScenarios` (4 tests) - Upgrade resilience

**Total: 30 tests**

**Key Functionality Tested:**

- Minimum version requirements met
- API compatibility with minimum versions
- Error handling mechanisms
- JSON serialization round-trips
- Nested model handling
- Field validation
- Optional field behavior
- Type conversion

## Test Fixtures (conftest.py)

### Global Fixtures

- `temp_dir` - Temporary directory for file operations
- `temp_file` - Temporary file for testing
- `sample_manifest` - Sample Python manifest data
- `sample_dotnet_releases` - Sample GitHub releases data
- `sample_nuget_versions` - Sample NuGet versions

## Coverage Report

The test suite aims for comprehensive coverage of:

- All public functions and methods
- Version parsing and comparison logic
- API interactions (GitHub, NuGet)
- File operations (download, extract, merge)
- Error handling paths
- Edge cases and boundary conditions

Run coverage report:

```bash
poetry run pytest --cov=.github/scripts --cov=PowerShell --cov-report=html
```

## Continuous Integration

The test suite is designed to be run in CI/CD pipelines:

```yaml
# Example GitHub Actions
- name: Install dependencies
  run: poetry install

- name: Run tests with coverage
  run: poetry run pytest --cov --cov-report=xml

- name: Upload coverage
  uses: codecov/codecov-action@v3
  with:
    files: ./coverage.xml
```

## Adding New Tests

When adding new functionality:

1. Add corresponding test class to appropriate test file
2. Use existing fixtures from `conftest.py`
3. Mock external API calls (GitHub, NuGet)
4. Test both success and error paths
5. Include edge cases
6. Run tests locally before committing:

```bash
poetry run pytest -v
```

## Common Test Patterns

### Mocking API Calls

```python
@patch('urllib.request.urlopen')
def test_api_call(self, mock_urlopen):
    mock_response = MagicMock()
    mock_response.status = 200
    mock_response.read.return_value = json.dumps(data).encode()
    mock_urlopen.return_value.__enter__.return_value = mock_response
    
    result = fetch_json("https://api.example.com")
    assert result == data
```

### Testing Pydantic Models

```python
def test_model_creation(self):
    entry = FileEntry(
        filename="test.tar.gz",
        arch="x64",
        platform="linux",
        download_url="https://example.com/test.tar.gz"
    )
    assert entry.filename == "test.tar.gz"
    
    dumped = entry.model_dump()
    assert isinstance(dumped, dict)
```

### Testing Version Parsing

```python
def test_parse_version(self):
    v = parse_version("v9.0.0-preview.7")
    assert v.major == 9
    assert v.minor == 0
    assert v.stage_priority == 1  # preview
```

## Troubleshooting

### ImportError when running tests

Ensure Poetry environment is active and dependencies are installed:

```bash
poetry install
poetry run pytest
```

### Tests fail with version mismatch

Check installed package versions:

```bash
poetry show
```

Update Poetry lockfile:

```bash
poetry update
```

### Mocking not working in tests

Ensure you're mocking at the correct import location:

```python
# Wrong - mocks in the wrong location
@patch('requests.get')
def test_func(self, mock_get): pass

# Correct - mock where it's used
@patch('dotnet_install.urllib.request.urlopen')
def test_func(self, mock_urlopen): pass
```

## Summary

This test suite provides:

- **147 total tests** across 4 test modules
- **Complete coverage** of all Python scripts
- **Package compatibility verification** for critical dependencies
- **Integration tests** for workflows
- **Edge case handling** and error paths
- **Mocking of external APIs** for reliability
- **Pytest configuration** in pyproject.toml

The tests ensure that package upgrades won't break existing functionality and that all features work as expected.
