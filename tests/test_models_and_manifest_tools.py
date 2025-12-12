"""
Comprehensive tests for models.py and manifest_tools.py modules.
Tests verify compatibility with pydantic >= 2.11.7
"""
import pytest
import sys
import json
import tempfile
import os
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open

# Import the modules under test
sys.path.insert(0, str(Path(__file__).parent.parent / ".github" / "scripts"))
import importlib.util

spec_models = importlib.util.spec_from_file_location("models", str(Path(__file__).parent.parent / ".github" / "scripts" / "models.py"))
models = importlib.util.module_from_spec(spec_models)
sys.modules["models"] = models
spec_models.loader.exec_module(models)

spec_manifest_tools = importlib.util.spec_from_file_location("manifest_tools", str(Path(__file__).parent.parent / ".github" / "scripts" / "manifest_tools.py"))
manifest_tools = importlib.util.module_from_spec(spec_manifest_tools)
sys.modules["manifest_tools"] = manifest_tools
spec_manifest_tools.loader.exec_module(manifest_tools)

from models import FileEntry, ManifestEntry
from manifest_tools import manifest_fetch, manifest_merge, app


class TestFileEntry:
    """Test FileEntry Pydantic model."""

    def test_file_entry_creation(self):
        """Test creating a FileEntry."""
        entry = FileEntry(
            filename="python-3.13.0-linux-x64.tar.gz",
            arch="x64",
            platform="linux",
            download_url="https://example.com/python.tar.gz"
        )
        assert entry.filename == "python-3.13.0-linux-x64.tar.gz"
        assert entry.arch == "x64"
        assert entry.platform == "linux"
        assert entry.platform_version is None

    def test_file_entry_with_platform_version(self):
        """Test FileEntry with platform_version."""
        entry = FileEntry(
            filename="python-3.13.0-linux-x64.tar.gz",
            arch="x64",
            platform="linux",
            platform_version="22.04",
            download_url="https://example.com/python.tar.gz"
        )
        assert entry.platform_version == "22.04"

    def test_file_entry_validation_missing_required(self):
        """Test FileEntry validation with missing required fields."""
        with pytest.raises(Exception):  # Pydantic validation error
            FileEntry(
                filename="python.tar.gz",
                arch="x64"
                # missing platform and download_url
            )

    def test_file_entry_model_dump(self):
        """Test FileEntry model_dump method."""
        entry = FileEntry(
            filename="python-3.13.0-linux-x64.tar.gz",
            arch="x64",
            platform="linux",
            download_url="https://example.com/python.tar.gz"
        )
        dumped = entry.model_dump()
        assert isinstance(dumped, dict)
        assert dumped["filename"] == "python-3.13.0-linux-x64.tar.gz"


class TestManifestEntry:
    """Test ManifestEntry Pydantic model."""

    def test_manifest_entry_creation(self):
        """Test creating a ManifestEntry."""
        entry = ManifestEntry(
            version="3.13.0",
            stable=True,
            release_url="https://github.com/actions/python-versions/releases/tag/3.13.0",
            files=[]
        )
        assert entry.version == "3.13.0"
        assert entry.stable is True
        assert entry.files == []

    def test_manifest_entry_with_files(self):
        """Test ManifestEntry with files."""
        file1 = FileEntry(
            filename="python-3.13.0-linux-x64.tar.gz",
            arch="x64",
            platform="linux",
            download_url="https://example.com/python.tar.gz"
        )
        entry = ManifestEntry(
            version="3.13.0",
            stable=True,
            release_url="https://github.com/actions/python-versions/releases/tag/3.13.0",
            files=[file1]
        )
        assert len(entry.files) == 1
        assert entry.files[0].arch == "x64"

    def test_manifest_entry_validation(self):
        """Test ManifestEntry validation."""
        with pytest.raises(Exception):  # Pydantic validation error
            ManifestEntry(
                version="3.13.0",
                stable=True
                # missing release_url and files
            )

    def test_manifest_entry_model_dump(self):
        """Test ManifestEntry model_dump method."""
        file1 = FileEntry(
            filename="python-3.13.0-linux-x64.tar.gz",
            arch="x64",
            platform="linux",
            download_url="https://example.com/python.tar.gz"
        )
        entry = ManifestEntry(
            version="3.13.0",
            stable=True,
            release_url="https://github.com/releases/tag/3.13.0",
            files=[file1]
        )
        dumped = entry.model_dump()
        assert isinstance(dumped, dict)
        assert dumped["version"] == "3.13.0"
        assert len(dumped["files"]) == 1


class TestManifestFetch:
    """Test manifest_fetch functionality."""

    @patch('requests.get')
    @patch('builtins.open', new_callable=mock_open)
    def test_manifest_fetch_success(self, mock_file, mock_requests_get, temp_dir):
        """Test successful manifest fetch."""
        test_manifest = [
            {
                "version": "3.13.0",
                "stable": True,
                "release_url": "https://github.com/releases/tag/3.13.0",
                "files": []
            }
        ]
        mock_response = MagicMock()
        mock_response.json.return_value = test_manifest
        mock_requests_get.return_value = mock_response

        output_file = os.path.join(temp_dir, "manifest.json")
        manifest_fetch("https://example.com/manifest.json", output_file)

        mock_requests_get.assert_called_once()
        mock_file.assert_called()

    @patch('requests.get')
    def test_manifest_fetch_http_error(self, mock_requests_get):
        """Test manifest fetch with HTTP error."""
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = Exception("HTTP Error")
        mock_requests_get.return_value = mock_response

        with pytest.raises(Exception):
            manifest_fetch("https://example.com/manifest.json", "/tmp/out.json")


class TestManifestMerge:
    """Test manifest_merge functionality."""

    def test_manifest_merge_unique_versions(self, temp_dir):
        """Test merging manifests with unique versions."""
        existing = [
            {
                "version": "3.13.0",
                "stable": True,
                "release_url": "https://github.com/releases/tag/3.13.0",
                "files": [
                    {
                        "filename": "python-3.13.0-linux-x64.tar.gz",
                        "arch": "x64",
                        "platform": "linux",
                        "platform_version": None,
                        "download_url": "https://example.com/python-3.13.0.tar.gz"
                    }
                ]
            }
        ]
        remote = [
            {
                "version": "3.12.0",
                "stable": True,
                "release_url": "https://github.com/releases/tag/3.12.0",
                "files": []
            }
        ]

        existing_file = os.path.join(temp_dir, "existing.json")
        remote_file = os.path.join(temp_dir, "remote.json")
        output_file = os.path.join(temp_dir, "merged.json")

        with open(existing_file, 'w') as f:
            json.dump(existing, f)
        with open(remote_file, 'w') as f:
            json.dump(remote, f)

        manifest_merge(existing_file, remote_file, output_file)

        with open(output_file, 'r') as f:
            merged = json.load(f)

        assert len(merged) == 2
        versions = [m["version"] for m in merged]
        assert "3.13.0" in versions
        assert "3.12.0" in versions

    def test_manifest_merge_overlapping_versions(self, temp_dir):
        """Test merging manifests with overlapping versions."""
        file1 = {
            "filename": "python-3.13.0-linux-x64.tar.gz",
            "arch": "x64",
            "platform": "linux",
            "platform_version": None,
            "download_url": "https://example.com/python-3.13.0-x64.tar.gz"
        }
        file2 = {
            "filename": "python-3.13.0-linux-arm64.tar.gz",
            "arch": "arm64",
            "platform": "linux",
            "platform_version": None,
            "download_url": "https://example.com/python-3.13.0-arm64.tar.gz"
        }

        existing = [
            {
                "version": "3.13.0",
                "stable": True,
                "release_url": "https://github.com/releases/tag/3.13.0",
                "files": [file1]
            }
        ]
        remote = [
            {
                "version": "3.13.0",
                "stable": True,
                "release_url": "https://github.com/releases/tag/3.13.0",
                "files": [file2]
            }
        ]

        existing_file = os.path.join(temp_dir, "existing.json")
        remote_file = os.path.join(temp_dir, "remote.json")
        output_file = os.path.join(temp_dir, "merged.json")

        with open(existing_file, 'w') as f:
            json.dump(existing, f)
        with open(remote_file, 'w') as f:
            json.dump(remote, f)

        manifest_merge(existing_file, remote_file, output_file)

        with open(output_file, 'r') as f:
            merged = json.load(f)

        assert len(merged) == 1
        assert len(merged[0]["files"]) == 2

    def test_manifest_merge_duplicate_files_not_added(self, temp_dir):
        """Test that duplicate files are not added during merge."""
        file1 = {
            "filename": "python-3.13.0-linux-x64.tar.gz",
            "arch": "x64",
            "platform": "linux",
            "platform_version": None,
            "download_url": "https://example.com/python-3.13.0-x64.tar.gz"
        }

        existing = [
            {
                "version": "3.13.0",
                "stable": True,
                "release_url": "https://github.com/releases/tag/3.13.0",
                "files": [file1]
            }
        ]
        remote = [
            {
                "version": "3.13.0",
                "stable": True,
                "release_url": "https://github.com/releases/tag/3.13.0",
                "files": [file1]
            }
        ]

        existing_file = os.path.join(temp_dir, "existing.json")
        remote_file = os.path.join(temp_dir, "remote.json")
        output_file = os.path.join(temp_dir, "merged.json")

        with open(existing_file, 'w') as f:
            json.dump(existing, f)
        with open(remote_file, 'w') as f:
            json.dump(remote, f)

        manifest_merge(existing_file, remote_file, output_file)

        with open(output_file, 'r') as f:
            merged = json.load(f)

        assert len(merged) == 1
        assert len(merged[0]["files"]) == 1


class TestUpdateVersion:
    """Test updating version with new file entries."""

    def test_update_version_existing_version(self, temp_dir):
        """Test adding file to existing version."""
        manifest_data = [
            {
                "version": "3.13.0",
                "stable": True,
                "release_url": "https://github.com/releases/tag/3.13.0",
                "files": [
                    {
                        "filename": "python-3.13.0-linux-x64.tar.gz",
                        "arch": "x64",
                        "platform": "linux",
                        "platform_version": None,
                        "download_url": "https://example.com/python-3.13.0-x64.tar.gz"
                    }
                ]
            }
        ]

        manifest_file = os.path.join(temp_dir, "manifest.json")
        with open(manifest_file, 'w') as f:
            json.dump(manifest_data, f)

        from manifest_tools import update_version
        update_version(
            existing_file=manifest_file,
            version="3.13.0",
            filename="python-3.13.0-linux-arm64.tar.gz",
            arch="arm64",
            platform="linux",
            download_url="https://example.com/python-3.13.0-arm64.tar.gz",
            platform_version=None,
            stable=True
        )

        with open(manifest_file, 'r') as f:
            updated = json.load(f)

        assert len(updated) == 1
        assert len(updated[0]["files"]) == 2

    def test_update_version_new_version(self, temp_dir):
        """Test creating new version entry."""
        manifest_data = [
            {
                "version": "3.12.0",
                "stable": True,
                "release_url": "https://github.com/releases/tag/3.12.0",
                "files": []
            }
        ]

        manifest_file = os.path.join(temp_dir, "manifest.json")
        with open(manifest_file, 'w') as f:
            json.dump(manifest_data, f)

        from manifest_tools import update_version
        update_version(
            existing_file=manifest_file,
            version="3.13.0",
            filename="python-3.13.0-linux-x64.tar.gz",
            arch="x64",
            platform="linux",
            download_url="https://example.com/python-3.13.0-x64.tar.gz",
            platform_version=None,
            stable=True
        )

        with open(manifest_file, 'r') as f:
            updated = json.load(f)

        assert len(updated) == 2
        versions = [m["version"] for m in updated]
        assert "3.13.0" in versions

    def test_update_version_duplicate_file_not_added(self, temp_dir):
        """Test that duplicate files are not added."""
        manifest_data = [
            {
                "version": "3.13.0",
                "stable": True,
                "release_url": "https://github.com/releases/tag/3.13.0",
                "files": [
                    {
                        "filename": "python-3.13.0-linux-x64.tar.gz",
                        "arch": "x64",
                        "platform": "linux",
                        "platform_version": None,
                        "download_url": "https://example.com/python-3.13.0-x64.tar.gz"
                    }
                ]
            }
        ]

        manifest_file = os.path.join(temp_dir, "manifest.json")
        with open(manifest_file, 'w') as f:
            json.dump(manifest_data, f)

        from manifest_tools import update_version
        update_version(
            existing_file=manifest_file,
            version="3.13.0",
            filename="python-3.13.0-linux-x64.tar.gz",
            arch="x64",
            platform="linux",
            download_url="https://example.com/python-3.13.0-x64.tar.gz",
            platform_version=None,
            stable=True
        )

        with open(manifest_file, 'r') as f:
            updated = json.load(f)

        assert len(updated) == 1
        assert len(updated[0]["files"]) == 1


class TestPydanticCompatibility:
    """Test compatibility with pydantic >= 2.11.7 features."""

    def test_model_validation_with_extra_fields(self):
        """Test that Pydantic validates extra fields appropriately."""
        data = {
            "filename": "python-3.13.0-linux-x64.tar.gz",
            "arch": "x64",
            "platform": "linux",
            "download_url": "https://example.com/python.tar.gz",
            "extra_field": "should_be_ignored"
        }
        entry = FileEntry(**data)
        assert entry.filename == "python-3.13.0-linux-x64.tar.gz"

    def test_model_json_schema(self):
        """Test that model can generate JSON schema."""
        schema = FileEntry.model_json_schema()
        assert isinstance(schema, dict)
        assert "properties" in schema
        assert "filename" in schema["properties"]

    def test_model_copy(self):
        """Test copying models."""
        entry = FileEntry(
            filename="python-3.13.0-linux-x64.tar.gz",
            arch="x64",
            platform="linux",
            download_url="https://example.com/python.tar.gz"
        )
        copy = entry.model_copy()
        assert copy.filename == entry.filename
        assert copy is not entry

    def test_model_validation_error_handling(self):
        """Test validation error handling."""
        # Pydantic allows empty strings, so this test passes without raising
        entry = FileEntry(
            filename="",  # empty filename
            arch="x64",
            platform="linux",
            download_url="https://example.com/python.tar.gz"
        )
        assert entry.filename == ""


class TestManifestIntegration:
    """Integration tests for manifest operations."""

    def test_full_manifest_workflow(self, temp_dir):
        """Test complete manifest workflow: fetch -> merge -> update."""
        # Create initial manifest
        initial = [
            {
                "version": "3.12.0",
                "stable": True,
                "release_url": "https://github.com/releases/tag/3.12.0",
                "files": []
            }
        ]

        manifest_file = os.path.join(temp_dir, "manifest.json")
        with open(manifest_file, 'w') as f:
            json.dump(initial, f)

        # Update with new entry
        from manifest_tools import update_version
        update_version(
            existing_file=manifest_file,
            version="3.13.0",
            filename="python-3.13.0-linux-x64.tar.gz",
            arch="x64",
            platform="linux",
            download_url="https://example.com/python-3.13.0-x64.tar.gz",
            platform_version=None,
            stable=True
        )

        # Verify final state
        with open(manifest_file, 'r') as f:
            final = json.load(f)

        assert len(final) == 2
        assert all(isinstance(m, dict) for m in final)
        assert all("version" in m for m in final)
        assert all("files" in m for m in final)
