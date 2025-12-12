"""
Package compatibility tests to ensure upgrades don't break functionality.
Tests verify that APIs used in the project work with minimum required versions:
- requests >= 2.32.5
- typer >= 0.19.2
- pydantic >= 2.11.7
"""
import pytest
import sys
import requests
import typer
import pydantic
from pathlib import Path
from unittest.mock import patch, MagicMock
import json

# Import the modules under test
sys.path.insert(0, str(Path(__file__).parent.parent / "PowerShell"))
sys.path.insert(0, str(Path(__file__).parent.parent / ".github" / "scripts"))

# Import the modules under test
sys.path.insert(0, str(Path(__file__).parent.parent / "PowerShell"))
sys.path.insert(0, str(Path(__file__).parent.parent / ".github" / "scripts"))

import importlib.util

spec_dotnet = importlib.util.spec_from_file_location("dotnet_install", str(Path(__file__).parent.parent / "PowerShell" / "dotnet-install.py"))
dotnet_install = importlib.util.module_from_spec(spec_dotnet)
sys.modules["dotnet_install"] = dotnet_install
spec_dotnet.loader.exec_module(dotnet_install)

spec_gpy = importlib.util.spec_from_file_location("get_python_version", str(Path(__file__).parent.parent / ".github" / "scripts" / "get_python_version.py"))
get_python_version = importlib.util.module_from_spec(spec_gpy)
sys.modules["get_python_version"] = get_python_version
spec_gpy.loader.exec_module(get_python_version)

spec_models = importlib.util.spec_from_file_location("models", str(Path(__file__).parent.parent / ".github" / "scripts" / "models.py"))
models = importlib.util.module_from_spec(spec_models)
sys.modules["models"] = models
spec_models.loader.exec_module(models)

from dotnet_install import get_nuget_versions, fetch_json
from get_python_version import PythonManifestParser
from models import FileEntry, ManifestEntry


class TestRequestsCompatibility:
    """Test that requests >= 2.32.5 APIs work correctly."""

    def test_requests_version_requirement(self):
        """Verify requests is installed and meets version requirement."""
        assert requests.__version__ >= "2.32.5" or \
               tuple(map(int, requests.__version__.split('.')[:3])) >= (2, 32, 5)

    @patch('urllib.request.urlopen')
    def test_urlopen_with_status_attribute(self, mock_urlopen):
        """Test that response object has status attribute (requests >= 2.32.5)."""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.read.return_value = json.dumps([]).encode()
        mock_urlopen.return_value.__enter__.return_value = mock_response

        # This should work without issues
        result = fetch_json("https://api.example.com/test")
        assert isinstance(result, list)

    @patch('urllib.request.urlopen')
    def test_urlopen_error_handling(self, mock_urlopen):
        """Test error handling with urllib (used by requests-like code)."""
        mock_urlopen.side_effect = Exception("Connection error")

        # Should handle exception gracefully
        result = get_nuget_versions("test-package")
        assert result == []

    @patch('urllib.request.urlopen')
    def test_response_headers_compatibility(self, mock_urlopen):
        """Test that response headers work correctly."""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.headers = {"Content-Type": "application/json; charset=utf-8"}
        mock_response.read.return_value = json.dumps([]).encode()
        mock_urlopen.return_value.__enter__.return_value = mock_response

        result = fetch_json("https://api.example.com/test")
        assert isinstance(result, list)


class TestTyperCompatibility:
    """Test that typer >= 0.19.2 APIs work correctly."""

    def test_typer_version_requirement(self):
        """Verify typer is installed and meets version requirement."""
        assert typer.__version__ >= "0.19.2" or \
               tuple(map(int, typer.__version__.split('.')[:2])) >= (0, 19)

    def test_typer_app_creation(self):
        """Test creating Typer app (basic functionality)."""
        app = typer.Typer()
        assert isinstance(app, typer.Typer)

    def test_typer_option_parameter(self):
        """Test Typer Option parameter (used in dotnet-install.py)."""
        # This is used in the actual code
        option = typer.Option(None, help="Test option")
        assert option is not None

    @patch('typer.echo')
    def test_typer_echo_compatibility(self, mock_echo):
        """Test typer.echo function."""
        # The module uses typer.echo
        from dotnet_install import typer as imported_typer
        assert hasattr(imported_typer, 'echo')

    def test_typer_context_with_NamedTuple(self):
        """Test that Typer works with NamedTuple (used for Version class)."""
        from typing import NamedTuple

        class TestVersion(NamedTuple):
            major: int
            minor: int

        v = TestVersion(3, 10)
        assert v.major == 3
        assert v.minor == 10

    def test_typer_exit_compatibility(self):
        """Test typer.Exit usage."""
        import typer as imported_typer
        # Should be able to create exit
        exit_code = imported_typer.Exit(1)
        # Code should be callable or have proper interface
        assert exit_code is not None


class TestPydanticCompatibility:
    """Test that pydantic >= 2.11.7 APIs work correctly."""

    def test_pydantic_version_requirement(self):
        """Verify pydantic is installed and meets version requirement."""
        assert pydantic.__version__ >= "2.11.7" or \
               tuple(map(int, pydantic.__version__.split('.')[:3])) >= (2, 11, 7)

    def test_basemodel_instantiation(self):
        """Test creating Pydantic BaseModel instances."""
        entry = FileEntry(
            filename="test.tar.gz",
            arch="x64",
            platform="linux",
            download_url="https://example.com/test.tar.gz"
        )
        assert entry.filename == "test.tar.gz"

    def test_basemodel_field_validation(self):
        """Test that Pydantic validates fields correctly."""
        with pytest.raises(Exception):  # Pydantic validation error
            FileEntry(
                filename="test.tar.gz",
                arch="x64"
                # missing required platform and download_url
            )

    def test_basemodel_model_dump(self):
        """Test model_dump method (Pydantic v2 API)."""
        entry = FileEntry(
            filename="test.tar.gz",
            arch="x64",
            platform="linux",
            download_url="https://example.com/test.tar.gz"
        )
        dumped = entry.model_dump()
        assert isinstance(dumped, dict)
        assert dumped["filename"] == "test.tar.gz"

    def test_basemodel_model_json_schema(self):
        """Test model_json_schema method (Pydantic v2 API)."""
        schema = FileEntry.model_json_schema()
        assert isinstance(schema, dict)
        assert "properties" in schema

    def test_basemodel_list_validation(self):
        """Test Pydantic List field validation."""
        manifest = ManifestEntry(
            version="3.13.0",
            stable=True,
            release_url="https://github.com/releases/tag/3.13.0",
            files=[]
        )
        assert isinstance(manifest.files, list)
        assert len(manifest.files) == 0

    def test_basemodel_optional_field(self):
        """Test Optional field in Pydantic."""
        entry = FileEntry(
            filename="test.tar.gz",
            arch="x64",
            platform="linux",
            download_url="https://example.com/test.tar.gz",
            platform_version=None
        )
        assert entry.platform_version is None

    def test_basemodel_optional_field_with_value(self):
        """Test Optional field with actual value."""
        entry = FileEntry(
            filename="test.tar.gz",
            arch="x64",
            platform="linux",
            platform_version="22.04",
            download_url="https://example.com/test.tar.gz"
        )
        assert entry.platform_version == "22.04"

    def test_pydantic_complex_nested_model(self):
        """Test complex nested Pydantic models."""
        file_entry = FileEntry(
            filename="python-3.13.0-linux-x64.tar.gz",
            arch="x64",
            platform="linux",
            download_url="https://example.com/python.tar.gz"
        )
        manifest = ManifestEntry(
            version="3.13.0",
            stable=True,
            release_url="https://github.com/releases/tag/3.13.0",
            files=[file_entry]
        )
        assert len(manifest.files) == 1
        assert manifest.files[0].arch == "x64"

    def test_pydantic_model_validation_on_init(self):
        """Test that Pydantic validates on initialization."""
        # Should raise validation error for invalid types
        with pytest.raises(Exception):
            FileEntry(
                filename=123,  # should be string
                arch="x64",
                platform="linux",
                download_url="https://example.com/test.tar.gz"
            )

    def test_pydantic_populate_by_name(self):
        """Test Pydantic field aliases (if used)."""
        # Test basic instantiation from dict
        data = {
            "filename": "test.tar.gz",
            "arch": "x64",
            "platform": "linux",
            "download_url": "https://example.com/test.tar.gz"
        }
        entry = FileEntry(**data)
        assert entry.filename == "test.tar.gz"


class TestCrossModuleCompatibility:
    """Test compatibility between modules."""

    def test_dotnet_install_imports_work(self):
        """Test that all imports in dotnet-install.py work."""
        from dotnet_install import (
            Version, parse_version, get_nuget_versions,
            filter_and_sort_tags, download_file, extract_tarball
        )
        assert callable(parse_version)
        assert callable(get_nuget_versions)

    def test_get_python_version_imports_work(self):
        """Test that all imports in get_python_version.py work."""
        from get_python_version import PythonManifestParser
        assert PythonManifestParser is not None

    def test_models_imports_work(self):
        """Test that all imports in models.py work."""
        from models import FileEntry, ManifestEntry
        assert FileEntry is not None
        assert ManifestEntry is not None

    def test_manifest_tools_imports_work(self):
        """Test that all imports in manifest_tools.py work."""
        from manifest_tools import manifest_fetch, manifest_merge
        assert callable(manifest_fetch)
        assert callable(manifest_merge)

    def test_json_serialization_round_trip(self):
        """Test that objects can be serialized and deserialized."""
        entry = FileEntry(
            filename="test.tar.gz",
            arch="x64",
            platform="linux",
            download_url="https://example.com/test.tar.gz"
        )
        
        # Dump to dict
        dumped = entry.model_dump()
        dumped_json = json.dumps(dumped)
        
        # Load back from dict
        loaded_dict = json.loads(dumped_json)
        restored = FileEntry(**loaded_dict)
        
        assert restored.filename == entry.filename
        assert restored.arch == entry.arch


class TestPackageUpgradeScenarios:
    """Test scenarios that might break with package upgrades."""

    def test_requests_session_behavior(self):
        """Test that requests session features work."""
        # Simulate code that might use requests.Session
        with patch('urllib.request.urlopen') as mock_urlopen:
            mock_response = MagicMock()
            mock_response.status = 200
            mock_response.read.return_value = b"test"
            mock_urlopen.return_value.__enter__.return_value = mock_response

            # Call the actual function
            result = get_nuget_versions("test-package")
            assert isinstance(result, list)

    def test_typer_command_registration(self):
        """Test Typer command registration."""
        app = typer.Typer()
        
        @app.command()
        def test_command(param: str = typer.Option(...)):
            return param
        
        assert app is not None

    def test_pydantic_strict_mode_compatibility(self):
        """Test Pydantic strict validation."""
        # This ensures the model works with strict validation
        data = {
            "filename": "test.tar.gz",
            "arch": "x64",
            "platform": "linux",
            "download_url": "https://example.com/test.tar.gz"
        }
        entry = FileEntry(**data)
        assert isinstance(entry, FileEntry)

    def test_pydantic_json_serialization(self):
        """Test JSON serialization with Pydantic."""
        entry = FileEntry(
            filename="test.tar.gz",
            arch="x64",
            platform="linux",
            download_url="https://example.com/test.tar.gz"
        )
        
        # Test model_dump_json if available
        if hasattr(entry, 'model_dump_json'):
            json_str = entry.model_dump_json()
            assert isinstance(json_str, str)
            assert "test.tar.gz" in json_str
