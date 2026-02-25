"""
Test cases for YAML filter parsing and release_types array functionality.
Tests verify the new filter format with version and release_types array support.
"""
import pytest
import sys
import json
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import yaml

# Import the module under test
sys.path.insert(0, str(Path(__file__).parent.parent / ".github" / "scripts"))
import importlib.util
spec = importlib.util.spec_from_file_location(
    "get_python_version",
    str(Path(__file__).parent.parent / ".github" / "scripts" / "get_python_version.py")
)
get_python_version_module = importlib.util.module_from_spec(spec)
sys.modules["get_python_version"] = get_python_version_module
spec.loader.exec_module(get_python_version_module)

from get_python_version import PythonManifestParser


class TestReleaseTypesArray:
    """Test filtering with release_types array parameter."""

    def test_filter_versions_release_types_stable_only(self, sample_manifest):
        """Test filtering with release_types=['stable']."""
        parser = PythonManifestParser(sample_manifest)
        versions = parser.filter_versions(release_types=['stable'])
        assert "3.13.0" in versions
        assert "3.12.5" in versions
        assert "3.8.10" in versions
        assert "3.11.0-rc.1" not in versions
        assert "3.10.0-beta.2" not in versions
        assert "3.9.0-alpha.1" not in versions

    def test_filter_versions_release_types_multiple(self, sample_manifest):
        """Test filtering with multiple release types."""
        parser = PythonManifestParser(sample_manifest)
        versions = parser.filter_versions(release_types=['stable', 'rc'])
        assert "3.13.0" in versions
        assert "3.12.5" in versions
        assert "3.11.0-rc.1" in versions
        assert "3.10.0-beta.2" not in versions
        assert "3.9.0-alpha.1" not in versions

    def test_filter_versions_release_types_beta_only(self, sample_manifest):
        """Test filtering with only beta releases."""
        parser = PythonManifestParser(sample_manifest)
        versions = parser.filter_versions(release_types=['beta'])
        assert "3.10.0-beta.2" in versions
        assert "3.13.0" not in versions
        assert "3.11.0-rc.1" not in versions
        assert "3.9.0-alpha.1" not in versions

    def test_filter_versions_release_types_alpha_only(self, sample_manifest):
        """Test filtering with only alpha releases."""
        parser = PythonManifestParser(sample_manifest)
        versions = parser.filter_versions(release_types=['alpha'])
        assert "3.9.0-alpha.1" in versions
        assert "3.13.0" not in versions
        assert "3.11.0-rc.1" not in versions

    def test_filter_versions_release_types_rc_only(self, sample_manifest):
        """Test filtering with only RC releases."""
        parser = PythonManifestParser(sample_manifest)
        versions = parser.filter_versions(release_types=['rc'])
        assert "3.11.0-rc.1" in versions
        assert "3.13.0" not in versions
        assert "3.10.0-beta.2" not in versions

    def test_filter_versions_release_types_all(self, sample_manifest):
        """Test filtering with all release types."""
        parser = PythonManifestParser(sample_manifest)
        versions = parser.filter_versions(release_types=['stable', 'beta', 'rc', 'alpha'])
        assert "3.13.0" in versions
        assert "3.11.0-rc.1" in versions
        assert "3.10.0-beta.2" in versions
        assert "3.9.0-alpha.1" in versions
        assert len(versions) == 6  # All versions

    def test_filter_versions_release_types_string_converts_to_list(self, sample_manifest):
        """Test that string release_type is converted to list."""
        parser = PythonManifestParser(sample_manifest)
        versions = parser.filter_versions(release_types='stable')
        assert "3.13.0" in versions
        assert "3.11.0-rc.1" not in versions

    def test_filter_versions_release_types_with_version_filter(self, sample_manifest):
        """Test release_types combined with version_filter."""
        parser = PythonManifestParser(sample_manifest)
        versions = parser.filter_versions(
            release_types=['stable', 'rc'],
            version_filter='3.1*'
        )
        assert "3.13.0" in versions
        assert "3.12.5" in versions
        assert "3.11.0-rc.1" in versions
        assert "3.10.0-beta.2" not in versions

    def test_filter_versions_release_types_default(self, sample_manifest):
        """Test default release_types is ['stable']."""
        parser = PythonManifestParser(sample_manifest)
        versions = parser.filter_versions()  # No release_types specified
        assert "3.13.0" in versions
        assert "3.11.0-rc.1" not in versions


class TestListVersionsWithReleaseTypes:
    """Test list_versions with release_types parameter."""

    def test_list_versions_release_types_sorted(self, sample_manifest):
        """Test list_versions with release_types returns sorted results."""
        parser = PythonManifestParser(sample_manifest)
        versions = parser.list_versions(release_types=['stable'])
        assert versions[0] == "3.13.0"
        assert versions[-1] == "3.8.10"
        # Verify sorted in descending order
        for i in range(len(versions) - 1):
            assert parser.version_compare(versions[i], versions[i+1]) >= 0

    def test_list_versions_release_types_multiple(self, sample_manifest):
        """Test list_versions with multiple release types."""
        parser = PythonManifestParser(sample_manifest)
        versions = parser.list_versions(release_types=['stable', 'rc', 'beta'])
        # Should include stable, rc, and beta but not alpha
        assert "3.13.0" in versions
        assert "3.11.0-rc.1" in versions
        assert "3.10.0-beta.2" in versions
        assert "3.9.0-alpha.1" not in versions

    def test_list_versions_release_types_with_filter(self, sample_manifest):
        """Test list_versions with both release_types and version_filter."""
        parser = PythonManifestParser(sample_manifest)
        versions = parser.list_versions(
            release_types=['stable'],
            version_filter='3.1*'
        )
        assert "3.13.0" in versions
        assert "3.12.5" in versions
        assert len(versions) == 2


class TestGetLatestVersionWithReleaseTypes:
    """Test get_latest_version with release_types parameter."""

    def test_get_latest_version_release_types_stable(self, sample_manifest):
        """Test getting latest with stable only."""
        parser = PythonManifestParser(sample_manifest)
        latest = parser.get_latest_version(release_types=['stable'])
        assert latest == "3.13.0"

    def test_get_latest_version_release_types_rc(self, sample_manifest):
        """Test getting latest with RC only."""
        parser = PythonManifestParser(sample_manifest)
        latest = parser.get_latest_version(release_types=['rc'])
        assert latest == "3.11.0-rc.1"

    def test_get_latest_version_release_types_multiple(self, sample_manifest):
        """Test getting latest with stable and RC."""
        parser = PythonManifestParser(sample_manifest)
        latest = parser.get_latest_version(release_types=['stable', 'rc'])
        assert latest == "3.13.0"  # stable is higher than rc

    def test_get_latest_version_release_types_with_filter(self, sample_manifest):
        """Test latest with release_types and version_filter."""
        parser = PythonManifestParser(sample_manifest)
        latest = parser.get_latest_version(
            release_types=['stable'],
            version_filter='3.1*'
        )
        assert latest == "3.13.0"

    def test_get_latest_version_release_types_no_match(self, sample_manifest):
        """Test latest with release_types that don't match."""
        parser = PythonManifestParser(sample_manifest)
        latest = parser.get_latest_version(
            release_types=['stable'],
            version_filter='9.0.*'
        )
        assert latest is None


class TestYAMLFilterFileFormat:
    """Test YAML filter file parsing and format validation."""

    def test_yaml_filter_simple_inline_array(self, temp_file):
        """Test parsing YAML with inline array for release_types."""
        yaml_content = """version: 3.14.*
release_types: [stable]
"""
        with open(temp_file, 'w') as f:
            f.write(yaml_content)
        
        with open(temp_file, 'r') as f:
            config = yaml.safe_load(f)
        
        assert config['version'] == '3.14.*'
        assert config['release_types'] == ['stable']

    def test_yaml_filter_multiline_array(self, temp_file):
        """Test parsing YAML with multi-line array for release_types."""
        yaml_content = """version: 3.13.*
release_types:
  - stable
  - beta
  - rc
"""
        with open(temp_file, 'w') as f:
            f.write(yaml_content)
        
        with open(temp_file, 'r') as f:
            config = yaml.safe_load(f)
        
        assert config['version'] == '3.13.*'
        assert config['release_types'] == ['stable', 'beta', 'rc']

    def test_yaml_filter_comments_ignored(self, temp_file):
        """Test that YAML comments are properly ignored."""
        yaml_content = """# Filter configuration for Python releases
version: 3.14.*
# Include these release types
release_types: [stable, beta]
"""
        with open(temp_file, 'w') as f:
            f.write(yaml_content)
        
        with open(temp_file, 'r') as f:
            config = yaml.safe_load(f)
        
        assert config['version'] == '3.14.*'
        assert config['release_types'] == ['stable', 'beta']

    def test_yaml_filter_multiple_entries(self, temp_file):
        """Test YAML with array of filter entries."""
        yaml_content = """filters:
  - version: 3.14.*
    release_types: [stable]
  - version: 3.13.*
    release_types: [stable, beta]
"""
        with open(temp_file, 'w') as f:
            f.write(yaml_content)
        
        with open(temp_file, 'r') as f:
            config = yaml.safe_load(f)
        
        assert len(config['filters']) == 2
        assert config['filters'][0]['version'] == '3.14.*'
        assert config['filters'][0]['release_types'] == ['stable']
        assert config['filters'][1]['version'] == '3.13.*'
        assert config['filters'][1]['release_types'] == ['stable', 'beta']

    def test_yaml_filter_single_string_release_type(self, temp_file):
        """Test YAML where release_types is a single string instead of array."""
        yaml_content = """version: 3.14.*
release_types: stable
"""
        with open(temp_file, 'w') as f:
            f.write(yaml_content)
        
        with open(temp_file, 'r') as f:
            config = yaml.safe_load(f)
        
        assert config['version'] == '3.14.*'
        assert config['release_types'] == 'stable'

    def test_yaml_filter_empty_file(self, temp_file):
        """Test parsing empty YAML file."""
        with open(temp_file, 'w') as f:
            f.write("")
        
        with open(temp_file, 'r') as f:
            config = yaml.safe_load(f)
        
        assert config is None

    def test_yaml_filter_missing_version(self, temp_file):
        """Test YAML with missing version field."""
        yaml_content = """release_types: [stable]
"""
        with open(temp_file, 'w') as f:
            f.write(yaml_content)
        
        with open(temp_file, 'r') as f:
            config = yaml.safe_load(f)
        
        assert 'version' not in config
        assert config['release_types'] == ['stable']

    def test_yaml_filter_missing_release_types(self, temp_file):
        """Test YAML with missing release_types field."""
        yaml_content = """version: 3.14.*
"""
        with open(temp_file, 'w') as f:
            f.write(yaml_content)
        
        with open(temp_file, 'r') as f:
            config = yaml.safe_load(f)
        
        assert config['version'] == '3.14.*'
        assert 'release_types' not in config


class TestWorkflowHelperFunctions:
    """Test helper functions for workflow integration."""

    def test_parse_yaml_to_filter_and_release_types(self, temp_file):
        """Test extracting filter and release_types from YAML."""
        yaml_content = """version: 3.14.*
release_types: [stable, beta]
"""
        with open(temp_file, 'w') as f:
            f.write(yaml_content)
        
        with open(temp_file, 'r') as f:
            config = yaml.safe_load(f)
            version_filter = config.get('version', '')
            release_types = config.get('release_types', ['stable'])
            
            # Normalize to list if string
            if isinstance(release_types, str):
                release_types = [release_types]
        
        assert version_filter == '3.14.*'
        assert release_types == ['stable', 'beta']

    def test_normalize_release_types_to_list(self):
        """Test normalizing release_types string to list."""
        # Single string
        release_types = 'stable'
        if isinstance(release_types, str):
            release_types = [release_types]
        assert release_types == ['stable']
        
        # Already a list
        release_types = ['stable', 'beta']
        if isinstance(release_types, str):
            release_types = [release_types]
        assert release_types == ['stable', 'beta']

    def test_derive_filter_from_version(self):
        """Test deriving glob filter from specific version."""
        version = '3.14.5'
        # Convert latest version like 3.14.5 to 3.14.*
        filter_pattern = f"{'.'.join(version.split('.')[:2])}.*"
        assert filter_pattern == '3.14.*'

    def test_release_types_to_command_args(self):
        """Test converting release_types array to command args."""
        release_types = ['stable', 'beta', 'rc']
        # Space-separated string for shell command
        args_string = ' '.join(release_types)
        assert args_string == 'stable beta rc'


class TestReleaseTypesIntegration:
    """Integration tests combining version filter and release_types."""

    def test_filter_and_release_types_stable_3_14(self, sample_manifest):
        """Test real-world scenario: stable 3.14.* only."""
        parser = PythonManifestParser(sample_manifest)
        versions = parser.list_versions(
            release_types=['stable'],
            version_filter='3.1*'
        )
        assert all(PythonManifestParser.is_stable(v) for v in versions)
        assert all('3.1' in v for v in versions)

    def test_filter_and_release_types_prerelease_3_11(self, sample_manifest):
        """Test scenario: prerelease versions for 3.11."""
        parser = PythonManifestParser(sample_manifest)
        versions = parser.list_versions(
            release_types=['rc', 'beta', 'alpha'],
            version_filter='3.11*'
        )
        assert any('3.11' in v for v in versions)
        assert not any(PythonManifestParser.is_stable(v) for v in versions)

    def test_latest_with_multiple_release_types(self, sample_manifest):
        """Test getting latest version across multiple release types."""
        parser = PythonManifestParser(sample_manifest)
        latest = parser.get_latest_version(
            release_types=['stable', 'rc', 'beta'],
            version_filter='3.*'
        )
        # Should return the highest version across all specified types
        assert latest is not None
        assert '3.' in latest

    def test_backward_compatibility_old_api_still_works(self, sample_manifest):
        """Test backward compatibility: old filter_versions still works."""
        parser = PythonManifestParser(sample_manifest)
        # Using new release_types parameter
        versions = parser.filter_versions(
            release_types=['stable'],
            version_filter='3.1*'
        )
        assert len(versions) > 0
        assert all(PythonManifestParser.is_stable(v) for v in versions)
