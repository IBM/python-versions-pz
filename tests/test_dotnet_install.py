"""
Comprehensive tests for dotnet-install.py module.
Tests verify functionality with typer >= 0.19.2 and requests >= 2.32.5
"""
import pytest
import os
import sys
import json
import tempfile
import tarfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, mock_open
from typing import List

# Import the module under test
sys.path.insert(0, str(Path(__file__).parent.parent / "PowerShell"))
import importlib.util
spec = importlib.util.spec_from_file_location("dotnet_install", str(Path(__file__).parent.parent / "PowerShell" / "dotnet-install.py"))
dotnet_install = importlib.util.module_from_spec(spec)
sys.modules["dotnet_install"] = dotnet_install
spec.loader.exec_module(dotnet_install)

from dotnet_install import (
    Version,
    parse_version,
    version_to_string,
    is_version_in_nuget,
    normalized_version_for_nuget,
    resolve_tag,
    find_closest_version_tag,
    filter_and_sort_tags,
    get_nuget_versions,
    download_file,
    extract_tarball,
    setup_environment,
    verify_installation,
    fetch_json,
    get_all_tags,
    get_release_by_tag,
    select_tag_interactive,
)


class TestVersionParsing:
    """Test Version parsing functionality."""

    def test_parse_version_stable(self):
        """Test parsing a stable version."""
        v = parse_version("v9.0.100")
        assert v.major == 9
        assert v.minor == 0
        assert v.patch == 100
        assert v.stage_priority == 4  # stable

    def test_parse_version_preview(self):
        """Test parsing a preview version."""
        v = parse_version("v9.0.0-preview.7.25351.106")
        assert v.major == 9
        assert v.minor == 0
        assert v.patch == 0
        assert v.stage_priority == 1  # preview
        assert v.stage_number == 7
        assert v.build == (25351, 106)

    def test_parse_version_rc(self):
        """Test parsing a release candidate version."""
        v = parse_version("v8.0.0-rc.2.23480.5")
        assert v.major == 8
        assert v.minor == 0
        assert v.stage_priority == 2  # rc
        assert v.stage_number == 2

    def test_parse_version_alpha(self):
        """Test parsing an alpha version."""
        v = parse_version("v7.0.0-alpha.1.23456")
        assert v.major == 7
        assert v.stage_priority == 0  # alpha

    def test_parse_version_rtm(self):
        """Test parsing an RTM version."""
        v = parse_version("v6.0.0-rtm.24503.15")
        assert v.major == 6
        assert v.stage_priority == 3  # rtm

    def test_parse_version_without_v_prefix(self):
        """Test parsing version without 'v' prefix."""
        v = parse_version("9.0.100")
        assert v.major == 9
        assert v.minor == 0
        assert v.patch == 100

    def test_version_comparison_stable_vs_preview(self):
        """Test that stable > preview in sorting."""
        stable = parse_version("v9.0.0")
        preview = parse_version("v9.0.0-preview.1")
        assert stable > preview

    def test_version_comparison_same_stage_different_number(self):
        """Test version comparison with same stage but different numbers."""
        preview1 = parse_version("v9.0.0-preview.1")
        preview2 = parse_version("v9.0.0-preview.2")
        # Both have stage_priority=1, so compare by stage_number
        assert preview2 > preview1


class TestVersionToString:
    """Test converting Version back to string."""

    def test_version_to_string_stable(self):
        """Test converting stable version to string."""
        v = Version(9, 0, 100, 4, 0, ())
        result = version_to_string(v)
        assert result == "9.0.100"

    def test_version_to_string_preview(self):
        """Test converting preview version to string."""
        v = Version(9, 0, 0, 1, 7, (25351, 106))
        result = version_to_string(v)
        assert result == "9.0.0-preview.7.25351.106"

    def test_version_to_string_rc(self):
        """Test converting RC version to string."""
        v = Version(8, 0, 0, 2, 2, (23480, 5))
        result = version_to_string(v)
        assert result == "8.0.0-rc.2.23480.5"


class TestNormalizedVersionForNuget:
    """Test normalizing versions for NuGet compatibility."""

    def test_normalize_stable_version(self):
        """Test normalizing stable version."""
        v = Version(9, 0, 100, 4, 0, ())
        result = normalized_version_for_nuget(v)
        assert result == "9.0.0"

    def test_normalize_preview_version(self):
        """Test normalizing preview version."""
        v = Version(9, 0, 0, 1, 7, (25351, 106))
        result = normalized_version_for_nuget(v)
        assert result == "9.0.0-preview.7.25351.106"

    def test_normalize_rc_version(self):
        """Test normalizing RC version."""
        v = Version(8, 0, 0, 2, 2, (23480, 5))
        result = normalized_version_for_nuget(v)
        assert result == "8.0.0-rc.2.23480.5"


class TestIsVersionInNuget:
    """Test checking if version exists in NuGet."""

    def test_version_in_nuget(self):
        """Test finding version in NuGet set."""
        nuget_set = {"9.0.0", "8.0.400", "8.0.0"}
        v = Version(9, 0, 100, 4, 0, ())
        assert is_version_in_nuget(nuget_set, v)

    def test_version_not_in_nuget(self):
        """Test version not found in NuGet set."""
        nuget_set = {"9.0.0", "8.0.400"}
        v = Version(7, 0, 0, 4, 0, ())
        assert not is_version_in_nuget(nuget_set, v)

    def test_preview_version_in_nuget(self):
        """Test finding preview version in NuGet set."""
        nuget_set = {"9.0.0-preview.7.25351.106"}
        v = Version(9, 0, 0, 1, 7, (25351, 106))
        assert is_version_in_nuget(nuget_set, v)


class TestResolveTag:
    """Test tag resolution functionality."""

    def test_resolve_tag_exact_match(self, sample_dotnet_releases):
        """Test exact tag match."""
        tag_input = "v9.0.100"
        result = resolve_tag(tag_input, sample_dotnet_releases)
        assert result == "v9.0.100"

    def test_resolve_tag_prefix_match(self, sample_dotnet_releases):
        """Test prefix-based tag matching."""
        tag_input = "v9.0"
        with patch('typer.echo'):
            result = resolve_tag(tag_input, sample_dotnet_releases)
        # Should find and return v9.0.100
        assert result == "v9.0.100"

    def test_resolve_tag_no_match(self, sample_dotnet_releases):
        """Test no matching tag found."""
        tag_input = "v10.0.0"
        # Should raise an Exit exception
        from typer import Exit
        with pytest.raises(Exit):
            resolve_tag(tag_input, sample_dotnet_releases)

    def test_resolve_tag_none_input(self, sample_dotnet_releases):
        """Test None input returns None."""
        result = resolve_tag(None, sample_dotnet_releases)
        assert result is None


class TestFindClosestVersionTag:
    """Test finding closest version tag."""

    def test_find_exact_version(self, sample_dotnet_releases):
        """Test finding exact version match."""
        result = find_closest_version_tag(sample_dotnet_releases, "v9.0.100")
        assert result == "v9.0.100"

    def test_find_closest_lower_version(self, sample_dotnet_releases):
        """Test finding closest lower version."""
        result = find_closest_version_tag(sample_dotnet_releases, "v8.0.350")
        # Should find v8.0.300 as it's the closest lower version
        assert "8.0" in result

    def test_find_closest_higher_version(self, sample_dotnet_releases):
        """Test finding closest higher version when no lower exists."""
        result = find_closest_version_tag(sample_dotnet_releases, "v6.0.0")
        # Should find v7.0.400 as lowest available
        assert "7.0" in result


class TestFilterAndSortTags:
    """Test filtering and sorting tags."""

    def test_filter_and_sort_no_filter(self, sample_dotnet_releases):
        """Test filtering without prefix."""
        result = filter_and_sort_tags(sample_dotnet_releases, None)
        assert len(result) > 0
        # Should be sorted by version descending
        assert result[0]["tag_name"] == "v9.0.100"

    def test_filter_and_sort_with_prefix(self, sample_dotnet_releases):
        """Test filtering with version prefix."""
        result = filter_and_sort_tags(sample_dotnet_releases, "v8")
        assert all("8" in t["tag_name"] for t in result)
        assert len(result) == 2  # v8.0.400 and v8.0.300

    def test_filter_and_sort_with_prefix_no_v(self, sample_dotnet_releases):
        """Test filtering with prefix without 'v'."""
        result = filter_and_sort_tags(sample_dotnet_releases, "9")
        assert any("9.0" in t["tag_name"] for t in result)

    def test_filter_and_sort_empty_result(self, sample_dotnet_releases):
        """Test filtering with no matches."""
        result = filter_and_sort_tags(sample_dotnet_releases, "v99")
        assert len(result) == 0


class TestGetNugetVersions:
    """Test fetching NuGet versions."""

    @patch('urllib.request.urlopen')
    def test_get_nuget_versions_success(self, mock_urlopen, sample_nuget_versions):
        """Test successfully fetching NuGet versions."""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.read.return_value = json.dumps({
            "versions": sample_nuget_versions
        }).encode()
        mock_urlopen.return_value.__enter__.return_value = mock_response

        result = get_nuget_versions("microsoft.netcore.app.runtime.linux-x64")
        assert len(result) == len(sample_nuget_versions)
        assert "9.0.0" in result

    @patch('urllib.request.urlopen')
    def test_get_nuget_versions_http_error(self, mock_urlopen):
        """Test handling HTTP error from NuGet."""
        mock_response = MagicMock()
        mock_response.status = 404
        mock_urlopen.return_value.__enter__.return_value = mock_response

        result = get_nuget_versions("invalid-package")
        assert result == []

    @patch('urllib.request.urlopen')
    def test_get_nuget_versions_network_error(self, mock_urlopen):
        """Test handling network error."""
        mock_urlopen.side_effect = Exception("Network error")

        result = get_nuget_versions("microsoft.netcore.app.runtime.linux-x64")
        assert result == []


class TestDownloadFile:
    """Test file download functionality."""

    @patch('urllib.request.urlopen')
    @patch('shutil.copyfileobj')
    def test_download_file_success(self, mock_copy, mock_urlopen, temp_file):
        """Test successful file download."""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.headers = {"Content-Type": "application/gzip"}
        mock_urlopen.return_value.__enter__.return_value = mock_response

        download_file("https://example.com/file.tar.gz", temp_file)
        mock_copy.assert_called_once()

    @patch('urllib.request.urlopen')
    def test_download_file_http_error(self, mock_urlopen):
        """Test download with HTTP error."""
        mock_response = MagicMock()
        mock_response.status = 404
        mock_urlopen.return_value.__enter__.return_value = mock_response

        from typer import Exit
        with pytest.raises(Exit):
            download_file("https://example.com/notfound.tar.gz", "/tmp/file.tar.gz")

    @patch('urllib.request.urlopen')
    def test_download_file_html_content(self, mock_urlopen):
        """Test download with HTML content (error)."""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.headers = {"Content-Type": "text/html"}
        mock_urlopen.return_value.__enter__.return_value = mock_response

        from typer import Exit
        with pytest.raises(Exit):
            download_file("https://example.com/file.tar.gz", "/tmp/file.tar.gz")


class TestExtractTarball:
    """Test tarball extraction functionality."""

    def test_extract_tarball_success(self, temp_dir):
        """Test successful tarball extraction."""
        # Create a test tarball
        tar_path = os.path.join(temp_dir, "test.tar.gz")
        extract_dir = os.path.join(temp_dir, "extracted")
        os.makedirs(extract_dir)

        # Create a simple tar file with test content
        with tarfile.open(tar_path, "w:gz") as tar:
            # Create test file in memory
            import io
            test_content = b"test content"
            tarinfo = tarfile.TarInfo(name="testfile.txt")
            tarinfo.size = len(test_content)
            tar.addfile(tarinfo, io.BytesIO(test_content))

        # Extract and verify
        extract_tarball(tar_path, extract_dir)
        assert os.path.exists(os.path.join(extract_dir, "testfile.txt"))

    def test_extract_invalid_tarball(self, temp_file):
        """Test extraction of invalid tarball."""
        # Create invalid tarball file
        with open(temp_file, 'w') as f:
            f.write("not a tarball")

        from typer import Exit
        with pytest.raises(Exit):
            extract_tarball(temp_file, "/tmp/extract")


class TestFetchJson:
    """Test JSON fetching from URLs."""

    @patch('urllib.request.urlopen')
    def test_fetch_json_success(self, mock_urlopen):
        """Test successfully fetching JSON."""
        test_data = [{"tag_name": "v9.0.100"}, {"tag_name": "v8.0.400"}]
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.read.return_value = json.dumps(test_data).encode()
        mock_urlopen.return_value.__enter__.return_value = mock_response

        result = fetch_json("https://api.github.com/repos/test/test/releases")
        assert result == test_data

    @patch('urllib.request.urlopen')
    def test_fetch_json_http_error(self, mock_urlopen):
        """Test fetch with HTTP error."""
        mock_response = MagicMock()
        mock_response.status = 404
        mock_urlopen.return_value.__enter__.return_value = mock_response

        from typer import Exit
        with pytest.raises(Exit):
            fetch_json("https://api.github.com/repos/test/notfound/releases")


class TestGetAllTags:
    """Test fetching all tags from GitHub."""

    def test_get_all_tags_function_exists(self):
        """Test that get_all_tags function is callable."""
        assert callable(get_all_tags)


class TestGetReleaseByTag:
    """Test fetching specific release by tag."""

    def test_get_release_by_tag_function_exists(self):
        """Test that get_release_by_tag function is callable."""
        assert callable(get_release_by_tag)


class TestSetupEnvironment:
    """Test environment setup."""

    @patch('os.makedirs')
    @patch('os.chmod')
    @patch('builtins.open', new_callable=mock_open)
    def test_setup_environment(self, mock_file, mock_chmod, mock_makedirs):
        """Test setting up environment variables."""
        setup_environment()
        mock_makedirs.assert_called()
        mock_file.assert_called()
        mock_chmod.assert_called()


class TestVerifyInstallation:
    """Test installation verification."""

    @patch('shutil.which')
    @patch('os.system')
    def test_verify_installation_success(self, mock_system, mock_which):
        """Test successful installation verification."""
        mock_which.return_value = "/usr/share/dotnet/dotnet"

        verify_installation()
        mock_which.assert_called()
        mock_system.assert_called()

    @patch('shutil.which')
    def test_verify_installation_missing_dotnet(self, mock_which):
        """Test verification with missing dotnet."""
        mock_which.return_value = None

        from typer import Exit
        with pytest.raises(Exit):
            verify_installation()


class TestIntegrationDownloadAndExtract:
    """Integration tests for download and extract workflow."""

    def test_download_extract_workflow(self, temp_dir, mocker):
        """Test complete download and extract workflow."""
        # Create a test tar file
        tar_path = os.path.join(temp_dir, "dotnet.tar.gz")
        with tarfile.open(tar_path, "w:gz") as tar:
            import io
            content = b"dotnet content"
            info = tarfile.TarInfo(name="dotnet/bin/dotnet")
            info.size = len(content)
            tar.addfile(info, io.BytesIO(content))

        # Mock download to create the tar file
        def mock_download(url, dest):
            import shutil
            shutil.copy(tar_path, dest)

        mocker.patch('dotnet_install.download_file', side_effect=mock_download)

        # Extract
        extract_dir = os.path.join(temp_dir, "extracted")
        os.makedirs(extract_dir)
        extract_tarball(tar_path, extract_dir)

        assert os.path.exists(os.path.join(extract_dir, "dotnet/bin/dotnet"))
