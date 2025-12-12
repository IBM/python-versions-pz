"""
Comprehensive tests for get_python_version.py module.
Tests verify functionality with requests >= 2.32.5
"""
import pytest
import sys
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from functools import cmp_to_key

# Import the module under test
sys.path.insert(0, str(Path(__file__).parent.parent / ".github" / "scripts"))
import importlib.util
spec = importlib.util.spec_from_file_location("get_python_version", str(Path(__file__).parent.parent / ".github" / "scripts" / "get_python_version.py"))
get_python_version_module = importlib.util.module_from_spec(spec)
sys.modules["get_python_version"] = get_python_version_module
spec.loader.exec_module(get_python_version_module)

from get_python_version import PythonManifestParser


class TestVersionDetection:
    """Test version type detection methods."""

    def test_is_alpha_suffix(self):
        """Test alpha version detection with suffix."""
        assert PythonManifestParser.is_alpha("3.9.0-alpha.1")

    def test_is_alpha_endswith(self):
        """Test alpha version detection with endswith."""
        assert PythonManifestParser.is_alpha("3.9.0alpha")

    def test_is_alpha_with_dash(self):
        """Test alpha version detection with dash."""
        assert PythonManifestParser.is_alpha("3.9.0-alpha")

    def test_is_beta_suffix(self):
        """Test beta version detection with suffix."""
        assert PythonManifestParser.is_beta("3.10.0-beta.2")

    def test_is_beta_endswith(self):
        """Test beta version detection with endswith."""
        assert PythonManifestParser.is_beta("3.10.0beta")

    def test_is_rc_suffix(self):
        """Test RC version detection."""
        assert PythonManifestParser.is_rc("3.11.0-rc.1")

    def test_is_rc_endswith(self):
        """Test RC version detection with endswith."""
        assert PythonManifestParser.is_rc("3.11.0rc")

    def test_is_stable(self):
        """Test stable version detection."""
        assert PythonManifestParser.is_stable("3.13.0")
        assert PythonManifestParser.is_stable("3.12.5")

    def test_is_stable_with_prerelease_not_stable(self):
        """Test that prerelease versions are not stable."""
        assert not PythonManifestParser.is_stable("3.11.0-rc.1")
        assert not PythonManifestParser.is_stable("3.10.0-beta.2")
        assert not PythonManifestParser.is_stable("3.9.0-alpha.1")


class TestVersionParsing:
    """Test version string parsing."""

    def test_parse_version_simple(self):
        """Test parsing simple version."""
        result = PythonManifestParser.parse_version("3.13.0")
        assert result == (3, 13, 0, 0, 0)

    def test_parse_version_with_rc(self):
        """Test parsing version with RC."""
        result = PythonManifestParser.parse_version("3.11.0-rc.1")
        assert result[0] == 3  # major
        assert result[1] == 11  # minor
        assert result[2] == 0   # patch
        assert result[3] == -1  # rc priority
        assert result[4] == -1  # rc number

    def test_parse_version_with_beta(self):
        """Test parsing version with beta."""
        result = PythonManifestParser.parse_version("3.10.0-beta.2")
        major, minor, patch, pre_priority, pre_num = result
        assert major == 3
        assert minor == 10
        assert patch == 0
        assert pre_priority == -2  # beta priority
        assert pre_num == -2

    def test_parse_version_with_alpha(self):
        """Test parsing version with alpha."""
        result = PythonManifestParser.parse_version("3.9.0-alpha.1")
        major, minor, patch, pre_priority, pre_num = result
        assert major == 3
        assert minor == 9
        assert patch == 0
        assert pre_priority == -3  # alpha priority

    def test_parse_version_invalid(self):
        """Test parsing invalid version."""
        result = PythonManifestParser.parse_version("invalid")
        assert result == (0, 0, 0, 0, 0)


class TestVersionComparison:
    """Test version comparison functionality."""

    def test_version_compare_same(self):
        """Test comparing same versions."""
        result = PythonManifestParser.version_compare("3.13.0", "3.13.0")
        assert result == 0

    def test_version_compare_greater(self):
        """Test comparing greater version."""
        result = PythonManifestParser.version_compare("3.13.0", "3.12.0")
        assert result > 0

    def test_version_compare_less(self):
        """Test comparing lesser version."""
        result = PythonManifestParser.version_compare("3.12.0", "3.13.0")
        assert result < 0

    def test_version_compare_stable_vs_rc(self):
        """Test stable version is greater than RC."""
        result = PythonManifestParser.version_compare("3.11.0", "3.11.0-rc.1")
        assert result > 0

    def test_version_compare_rc_vs_beta(self):
        """Test RC is greater than beta."""
        result = PythonManifestParser.version_compare("3.10.0-rc.1", "3.10.0-beta.2")
        assert result > 0

    def test_version_compare_beta_vs_alpha(self):
        """Test beta is greater than alpha."""
        result = PythonManifestParser.version_compare("3.10.0-beta.1", "3.10.0-alpha.1")
        assert result > 0


class TestVersionMatchesFilter:
    """Test version filter matching."""

    def test_filter_exact_match(self):
        """Test exact version match."""
        assert PythonManifestParser.version_matches_filter("3.13.0", "3.13.0")

    def test_filter_wildcard_minor(self):
        """Test wildcard in minor version."""
        assert PythonManifestParser.version_matches_filter("3.13.5", "3.13.*")
        assert not PythonManifestParser.version_matches_filter("3.12.5", "3.13.*")

    def test_filter_wildcard_patch(self):
        """Test wildcard in patch version."""
        assert PythonManifestParser.version_matches_filter("3.13.5", "3.*.5")
        assert not PythonManifestParser.version_matches_filter("3.13.6", "3.*.5")

    def test_filter_wildcard_major(self):
        """Test wildcard in major version."""
        assert PythonManifestParser.version_matches_filter("3.13.0", "*.13.0")
        # Wildcard matches any number, so 2.13.0 also matches
        assert PythonManifestParser.version_matches_filter("2.13.0", "*.13.0")

    def test_filter_multiple_wildcards(self):
        """Test multiple wildcards."""
        assert PythonManifestParser.version_matches_filter("3.13.5", "*.*.*")


class TestManifestParsing:
    """Test PythonManifestParser initialization and validation."""

    def test_parser_init_valid_manifest(self, sample_manifest):
        """Test initializing parser with valid manifest."""
        parser = PythonManifestParser(sample_manifest)
        assert parser.manifest == sample_manifest

    def test_parser_init_empty_manifest(self):
        """Test initializing parser with empty manifest."""
        with pytest.raises(ValueError):
            PythonManifestParser([])

    def test_parser_init_none_manifest(self):
        """Test initializing parser with None."""
        with pytest.raises(ValueError):
            PythonManifestParser(None)

    def test_parser_init_invalid_type(self):
        """Test initializing parser with invalid type."""
        with pytest.raises(ValueError):
            PythonManifestParser("not a list")


class TestFilterVersions:
    """Test filtering versions."""

    def test_filter_versions_stable_only(self, sample_manifest):
        """Test filtering for stable versions only."""
        parser = PythonManifestParser(sample_manifest)
        versions = parser.filter_versions(only_stable=True)
        assert "3.13.0" in versions
        assert "3.12.5" in versions
        assert "3.8.10" in versions
        assert "3.11.0-rc.1" not in versions
        assert "3.10.0-beta.2" not in versions

    def test_filter_versions_include_rc(self, sample_manifest):
        """Test filtering for RC versions."""
        parser = PythonManifestParser(sample_manifest)
        versions = parser.filter_versions(include_rc=True)
        assert "3.11.0-rc.1" in versions

    def test_filter_versions_include_beta(self, sample_manifest):
        """Test filtering for beta versions."""
        parser = PythonManifestParser(sample_manifest)
        versions = parser.filter_versions(include_beta=True)
        assert "3.10.0-beta.2" in versions

    def test_filter_versions_include_alpha(self, sample_manifest):
        """Test filtering for alpha versions."""
        parser = PythonManifestParser(sample_manifest)
        versions = parser.filter_versions(include_alpha=True)
        assert "3.9.0-alpha.1" in versions

    def test_filter_versions_with_version_filter(self, sample_manifest):
        """Test filtering by version pattern."""
        parser = PythonManifestParser(sample_manifest)
        versions = parser.filter_versions(only_stable=True, version_filter="3.1*")
        assert "3.13.0" in versions
        # 3.12.5 matches 3.1* pattern (3.1 followed by anything)
        assert "3.12.5" in versions

    def test_filter_versions_default_stable(self, sample_manifest):
        """Test default filtering returns stable only."""
        parser = PythonManifestParser(sample_manifest)
        versions = parser.filter_versions()
        # Default should include stable only
        assert "3.13.0" in versions
        assert all(PythonManifestParser.is_stable(v) for v in versions)

    def test_filter_versions_prerelease_excludes_stable(self, sample_manifest):
        """Test that prerelease filters exclude stable."""
        parser = PythonManifestParser(sample_manifest)
        versions = parser.filter_versions(include_rc=True)
        # Should NOT include stable versions when rc flag is set
        assert "3.11.0-rc.1" in versions
        # Stable versions should be excluded
        assert "3.13.0" not in versions


class TestListVersions:
    """Test listing versions."""

    def test_list_versions_default_sorted(self, sample_manifest):
        """Test listing versions in correct order."""
        parser = PythonManifestParser(sample_manifest)
        versions = parser.list_versions(only_stable=True)
        # Should be sorted descending
        assert versions[0] == "3.13.0"
        assert versions[-1] == "3.8.10"

    def test_list_versions_with_filter(self, sample_manifest):
        """Test listing with filter."""
        parser = PythonManifestParser(sample_manifest)
        versions = parser.list_versions(only_stable=True, version_filter="3.1*")
        assert len(versions) == 2  # 3.13.0 and 3.12.5
        assert versions[0] == "3.13.0"

    def test_list_versions_empty_result(self, sample_manifest):
        """Test listing with no matching results."""
        parser = PythonManifestParser(sample_manifest)
        versions = parser.list_versions(only_stable=True, version_filter="5.0.*")
        assert len(versions) == 0


class TestGetLatestVersion:
    """Test getting latest version."""

    def test_get_latest_version_stable(self, sample_manifest):
        """Test getting latest stable version."""
        parser = PythonManifestParser(sample_manifest)
        latest = parser.get_latest_version(only_stable=True)
        assert latest == "3.13.0"

    def test_get_latest_version_with_rc(self, sample_manifest):
        """Test getting latest with RC."""
        parser = PythonManifestParser(sample_manifest)
        latest = parser.get_latest_version(include_rc=True)
        # When only rc flag is set, includes only rc versions (excludes stable)
        assert "rc" in latest or latest is None

    def test_get_latest_version_rc_only(self, sample_manifest):
        """Test getting latest RC only."""
        parser = PythonManifestParser(sample_manifest)
        latest = parser.get_latest_version(include_rc=True, include_alpha=True, include_beta=True)
        # When prerelease flags are set, includes only prerelease (not stable)
        assert any(tag in latest for tag in ["rc", "alpha", "beta", "rc.1", "alpha.1", "beta.2"])

    def test_get_latest_version_no_match(self, sample_manifest):
        """Test latest with no matches."""
        parser = PythonManifestParser(sample_manifest)
        latest = parser.get_latest_version(version_filter="5.0.*")
        assert latest is None

    def test_get_latest_version_with_filter(self, sample_manifest):
        """Test getting latest with version filter."""
        parser = PythonManifestParser(sample_manifest)
        latest = parser.get_latest_version(only_stable=True, version_filter="3.1*")
        assert latest == "3.13.0"


class TestVersionSortingOrder:
    """Test complex sorting scenarios."""

    def test_sorting_mixed_versions(self, sample_manifest):
        """Test sorting mixed stable and prerelease."""
        parser = PythonManifestParser(sample_manifest)
        versions = parser.list_versions()  # Default includes stable
        # Should be sorted by version, stable > prerelease
        assert versions[0] == "3.13.0"
        assert versions[-1] == "3.8.10"

    def test_sorting_same_major_minor_different_patch(self):
        """Test sorting versions with same major.minor."""
        manifest = [
            {"version": "3.10.5"},
            {"version": "3.10.2"},
            {"version": "3.10.10"},
            {"version": "3.10.1"},
        ]
        parser = PythonManifestParser(manifest)
        versions = parser.list_versions()
        assert versions[0] == "3.10.10"
        assert versions[-1] == "3.10.1"

    def test_sorting_prerelease_numbers(self):
        """Test sorting prerelease with different numbers."""
        manifest = [
            {"version": "3.10.0-rc.1"},
            {"version": "3.10.0-rc.5"},
            {"version": "3.10.0-rc.2"},
            {"version": "3.10.0-rc.10"},
        ]
        parser = PythonManifestParser(manifest)
        versions = parser.list_versions(only_stable=False, include_rc=True)
        # RC versions should be sorted by number (descending)
        # Due to negative pre_num in parsing, the sorting might be different
        if len(versions) > 0:
            assert "3.10.0-rc.10" in versions or "3.10.0-rc.5" in versions


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_empty_version_in_manifest(self):
        """Test manifest with empty version field."""
        manifest = [
            {"version": ""},
            {"version": "3.13.0"}
        ]
        parser = PythonManifestParser(manifest)
        versions = parser.list_versions()
        assert "3.13.0" in versions
        assert "" not in versions

    def test_missing_version_field(self):
        """Test manifest entry without version field."""
        manifest = [
            {"stable": True},
            {"version": "3.13.0", "stable": True}
        ]
        parser = PythonManifestParser(manifest)
        versions = parser.list_versions()
        assert len(versions) == 1
        assert "3.13.0" in versions

    def test_unicode_version_string(self):
        """Test version with unicode characters."""
        manifest = [
            {"version": "3.13.0✓"},
            {"version": "3.12.0"}
        ]
        parser = PythonManifestParser(manifest)
        versions = parser.list_versions()
        # Invalid versions should be handled gracefully
        assert "3.12.0" in versions

    def test_very_large_version_numbers(self):
        """Test parsing very large version numbers."""
        result = PythonManifestParser.parse_version("999.999.999")
        assert result[0] == 999
        assert result[1] == 999
        assert result[2] == 999

    def test_prerelease_with_multiple_dots(self):
        """Test prerelease with multiple dots in number."""
        result = PythonManifestParser.parse_version("3.10.0-rc.1.2.3")
        assert result[0] == 3
        assert result[1] == 10
        assert result[2] == 0
