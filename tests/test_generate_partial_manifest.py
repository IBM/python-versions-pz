import json
import sys

import pytest

import generate_partial_manifest as gpm


def test_validate_download_url_valid():
    """Test URL validation with correct URL."""
    url = "https://github.com/IBM/python-versions-pz/releases/download/3.13.3/python-3.13.3-linux-22.04-ppc64le.tar.gz"
    assert gpm.validate_download_url(url, "IBM", "python-versions-pz", "3.13.3", "python-3.13.3-linux-22.04-ppc64le.tar.gz")


def test_validate_download_url_empty():
    """Test URL validation with empty URL."""
    assert not gpm.validate_download_url("", "IBM", "python-versions-pz", "3.13.3", "python.tar.gz")


def test_validate_download_url_untagged_release():
    """Test that untagged releases are rejected."""
    url = "https://github.com/IBM/python-versions-pz/releases/download/untagged-abc123/python-3.13.3-linux-22.04-ppc64le.tar.gz"
    assert not gpm.validate_download_url(url, "IBM", "python-versions-pz", "3.13.3", "python-3.13.3-linux-22.04-ppc64le.tar.gz")


def test_validate_download_url_wrong_owner():
    """Test URL validation with wrong owner."""
    url = "https://github.com/WRONG/python-versions-pz/releases/download/3.13.3/python-3.13.3-linux-22.04-ppc64le.tar.gz"
    assert not gpm.validate_download_url(url, "IBM", "python-versions-pz", "3.13.3", "python-3.13.3-linux-22.04-ppc64le.tar.gz")


def test_validate_download_url_wrong_tag():
    """Test URL validation with wrong tag."""
    url = "https://github.com/IBM/python-versions-pz/releases/download/3.12.0/python-3.13.3-linux-22.04-ppc64le.tar.gz"
    assert not gpm.validate_download_url(url, "IBM", "python-versions-pz", "3.13.3", "python-3.13.3-linux-22.04-ppc64le.tar.gz")


def test_validate_download_url_wrong_filename():
    """Test URL validation with mismatched filename."""
    url = "https://github.com/IBM/python-versions-pz/releases/download/3.13.3/python-3.12.0-linux-22.04-ppc64le.tar.gz"
    assert not gpm.validate_download_url(url, "IBM", "python-versions-pz", "3.13.3", "python-3.13.3-linux-22.04-ppc64le.tar.gz")


def test_parse_filename_valid_asset():
    name = "python-3.13.3-linux-22.04-ppc64le.tar.gz"
    parsed = gpm.parse_filename(name)
    assert parsed == {
        "version": "3.13.3",
        "platform": "linux",
        "platform_version": "22.04",
        "arch": "ppc64le",
    }


def test_parse_filename_invalid_asset():
    assert gpm.parse_filename("python-3.13.3-linux.tar.gz") is None


def test_build_manifest_entries_filters_assets():
    assets = [
        {
            "name": "python-3.13.3-linux-22.04-ppc64le.tar.gz",
            "browser_download_url": "https://github.com/IBM/python-versions-pz/releases/download/3.13.3/python-3.13.3-linux-22.04-ppc64le.tar.gz",
        },
        {
            "name": "trivy-python-3.13.3-linux-22.04-ppc64le.tar.gz",
            "browser_download_url": "https://example.com/trivy.tar.gz",
        },
        {
            "name": "python-3.13.3-linux-22.04-ppc64le.log",
            "browser_download_url": "https://example.com/python.log",
        },
    ]

    entries, errors = gpm.build_manifest_entries("3.13.3", assets, "IBM", "python-versions-pz")
    assert len(entries) == 1
    assert entries[0]["filename"].endswith("tar.gz")
    assert entries[0]["arch"] == "ppc64le"
    assert len(errors) == 0  # Valid URLs should have no errors


def test_build_manifest_entries_invalid_urls():
    """Test that invalid URLs are rejected with validation errors."""
    assets = [
        {
            "name": "python-3.13.3-linux-22.04-ppc64le.tar.gz",
            "browser_download_url": "https://github.com/IBM/python-versions-pz/releases/download/3.12.0/python-3.13.3-linux-22.04-ppc64le.tar.gz",  # Wrong tag
        },
    ]

    entries, errors = gpm.build_manifest_entries("3.13.3", assets, "IBM", "python-versions-pz")
    assert len(entries) == 0
    assert len(errors) > 0
    assert "Invalid download_url" in errors[0]


def test_main_outputs_manifest(monkeypatch, capsys):
    assets = [
        {
            "name": "python-3.13.3-linux-22.04-ppc64le.tar.gz",
            "browser_download_url": "https://github.com/IBM/python-versions-pz/releases/download/3.13.3/python-3.13.3-linux-22.04-ppc64le.tar.gz",
        }
    ]
    args = [
        "generate_partial_manifest.py",
        "--tag",
        "3.13.3",
        "--owner",
        "IBM",
        "--repo",
        "python-versions-pz",
        "--assets",
        json.dumps(assets),
    ]
    monkeypatch.setattr(sys, "argv", args)

    exit_code = gpm.main()
    assert exit_code == 0

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert payload[0]["download_url"].endswith("python-3.13.3-linux-22.04-ppc64le.tar.gz")


def test_main_outputs_manifest_from_file(monkeypatch, capsys, tmp_path):
    """Test that main() reads from --assets-file correctly."""
    assets = [
        {
            "name": "python-3.13.3-linux-22.04-ppc64le.tar.gz",
            "browser_download_url": "https://github.com/IBM/python-versions-pz/releases/download/3.13.3/python-3.13.3-linux-22.04-ppc64le.tar.gz",
        }
    ]
    
    assets_file = tmp_path / "assets.json"
    assets_file.write_text(json.dumps(assets), encoding='utf-8')
    
    args = [
        "generate_partial_manifest.py",
        "--tag",
        "3.13.3",
        "--owner",
        "IBM",
        "--repo",
        "python-versions-pz",
        "--assets-file",
        str(assets_file),
    ]
    monkeypatch.setattr(sys, "argv", args)

    exit_code = gpm.main()
    assert exit_code == 0

    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert payload[0]["download_url"].endswith("python-3.13.3-linux-22.04-ppc64le.tar.gz")


def test_main_rejects_invalid_urls(monkeypatch, capsys):
    """Test that main() rejects invalid URLs and returns error code."""
    assets = [
        {
            "name": "python-3.13.3-linux-22.04-ppc64le.tar.gz",
            "browser_download_url": "https://github.com/IBM/python-versions-pz/releases/download/untagged-abc123/python-3.13.3-linux-22.04-ppc64le.tar.gz",
        }
    ]
    args = [
        "generate_partial_manifest.py",
        "--tag",
        "3.13.3",
        "--owner",
        "IBM",
        "--repo",
        "python-versions-pz",
        "--assets",
        json.dumps(assets),
    ]
    monkeypatch.setattr(sys, "argv", args)

    exit_code = gpm.main()
    assert exit_code == 1

    captured = capsys.readouterr()
    assert "ERROR: No valid assets found after validation" in captured.err


def test_main_invalid_json(monkeypatch, capsys):
    args = [
        "generate_partial_manifest.py",
        "--tag",
        "3.13.3",
        "--owner",
        "IBM",
        "--repo",
        "python-versions-pz",
        "--assets",
        "{invalid-json}",
    ]
    monkeypatch.setattr(sys, "argv", args)

    exit_code = gpm.main()
    assert exit_code == 1

    captured = capsys.readouterr()
    assert "Error decoding JSON" in captured.err
