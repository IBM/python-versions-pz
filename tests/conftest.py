"""
Pytest configuration and shared fixtures for the test suite.
"""
import pytest
import sys
import os
import tempfile
from pathlib import Path

# Add parent directories to path so we can import modules
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "PowerShell"))
sys.path.insert(0, str(Path(__file__).parent.parent / ".github" / "scripts"))


@pytest.fixture
def temp_dir():
    """Provide a temporary directory that is cleaned up after the test."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def temp_file():
    """Provide a temporary file that is cleaned up after the test."""
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
        temp_path = f.name
    yield temp_path
    if os.path.exists(temp_path):
        os.remove(temp_path)


@pytest.fixture
def sample_manifest():
    """Provide sample Python manifest data."""
    return [
        {
            "version": "3.13.0",
            "stable": True,
            "release_url": "https://github.com/actions/python-versions/releases/tag/3.13.0-1234",
            "files": [
                {
                    "filename": "python-3.13.0-linux-x64.tar.gz",
                    "arch": "x64",
                    "platform": "linux",
                    "platform_version": None,
                    "download_url": "https://example.com/python-3.13.0.tar.gz"
                }
            ]
        },
        {
            "version": "3.12.5",
            "stable": True,
            "release_url": "https://github.com/actions/python-versions/releases/tag/3.12.5-1234",
            "files": []
        },
        {
            "version": "3.11.0-rc.1",
            "stable": False,
            "release_url": "https://github.com/actions/python-versions/releases/tag/3.11.0-rc.1",
            "files": []
        },
        {
            "version": "3.10.0-beta.2",
            "stable": False,
            "release_url": "https://github.com/actions/python-versions/releases/tag/3.10.0-beta.2",
            "files": []
        },
        {
            "version": "3.9.0-alpha.1",
            "stable": False,
            "release_url": "https://github.com/actions/python-versions/releases/tag/3.9.0-alpha.1",
            "files": []
        },
        {
            "version": "3.8.10",
            "stable": True,
            "release_url": "https://github.com/actions/python-versions/releases/tag/3.8.10-1234",
            "files": []
        }
    ]


@pytest.fixture
def sample_dotnet_releases():
    """Provide sample .NET releases from GitHub API."""
    return [
        {
            "tag_name": "v9.0.100",
            "name": "dotnet-sdk-9.0.100-ppc64le",
            "assets": [
                {
                    "name": "dotnet-sdk-9.0.100-linux-ppc64le.tar.gz",
                    "browser_download_url": "https://github.com/IBM/dotnet-s390x/releases/download/v9.0.100/dotnet-sdk-9.0.100-linux-ppc64le.tar.gz"
                }
            ]
        },
        {
            "tag_name": "v8.0.400",
            "name": "dotnet-sdk-8.0.400-ppc64le",
            "assets": [
                {
                    "name": "dotnet-sdk-8.0.400-linux-ppc64le.tar.gz",
                    "browser_download_url": "https://github.com/IBM/dotnet-s390x/releases/download/v8.0.400/dotnet-sdk-8.0.400-linux-ppc64le.tar.gz"
                }
            ]
        },
        {
            "tag_name": "v8.0.300",
            "name": "dotnet-sdk-8.0.300-s390x",
            "assets": [
                {
                    "name": "dotnet-sdk-8.0.300-linux-s390x.tar.gz",
                    "browser_download_url": "https://github.com/IBM/dotnet-s390x/releases/download/v8.0.300/dotnet-sdk-8.0.300-linux-s390x.tar.gz"
                }
            ]
        },
        {
            "tag_name": "v7.0.400",
            "name": "dotnet-sdk-7.0.400",
            "assets": []
        }
    ]


@pytest.fixture
def sample_nuget_versions():
    """Provide sample NuGet version data."""
    return [
        "9.0.0",
        "8.0.400",
        "8.0.300",
        "8.0.200",
        "8.0.0",
        "7.0.400",
        "7.0.0",
        "6.0.0"
    ]
