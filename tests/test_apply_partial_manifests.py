import json
import sys
from pathlib import Path

import apply_partial_manifests as apm


def write_partial(base_path: Path, name: str, entries):
    folder = base_path / name
    folder.mkdir(parents=True, exist_ok=True)
    file_path = folder / f"{name}.json"
    file_path.write_text(json.dumps(entries), encoding="utf-8")
    return file_path


def test_apply_partial_manifests_creates_manifest(tmp_path, monkeypatch):
    partial_dir = tmp_path / "partials"
    manifest_dir = tmp_path / "manifests"
    partial_dir.mkdir()
    manifest_dir.mkdir()

    sample_entry = {
        "version": "3.13.3",
        "filename": "python-3.13.3-linux-22.04-ppc64le.tar.gz",
        "arch": "ppc64le",
        "platform": "linux",
        "platform_version": "22.04",
        "download_url": "https://example.com/python.tar.gz",
    }
    created = write_partial(partial_dir, "manifest-part-3.13.3", [sample_entry])
    assert created.exists(), "Partial artifact fixture failed"

    args = [
        "apply_partial_manifests.py",
        "--partials-dir",
        str(partial_dir),
        "--manifest-dir",
        str(manifest_dir),
    ]
    monkeypatch.setattr(sys, "argv", args)

    exit_code = apm.main()
    assert exit_code == 0

    manifest_file = manifest_dir / "3.13.3-ppc64le.json"
    assert manifest_file.exists()
    data = json.loads(manifest_file.read_text(encoding="utf-8"))
    assert data[0]["files"][0]["filename"].endswith("ppc64le.tar.gz")


def test_apply_partial_manifests_ignores_invalid_files(tmp_path, monkeypatch):
    partial_dir = tmp_path / "partials"
    manifest_dir = tmp_path / "manifests"
    partial_dir.mkdir()
    manifest_dir.mkdir()

    write_partial(partial_dir, "manifest-part-bad", {"foo": "bar"})

    args = [
        "apply_partial_manifests.py",
        "--partials-dir",
        str(partial_dir),
        "--manifest-dir",
        str(manifest_dir),
    ]
    monkeypatch.setattr(sys, "argv", args)

    exit_code = apm.main()
    assert exit_code == 0
    assert not list(manifest_dir.glob("*.json"))


def test_apply_partial_manifests_no_partials(tmp_path, monkeypatch):
    partial_dir = tmp_path / "partials"
    manifest_dir = tmp_path / "manifests"
    # Intentionally do not create partial_dir

    args = [
        "apply_partial_manifests.py",
        "--partials-dir",
        str(partial_dir),
        "--manifest-dir",
        str(manifest_dir),
    ]
    monkeypatch.setattr(sys, "argv", args)

    exit_code = apm.main()
    assert exit_code == 0
