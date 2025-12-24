import argparse
import json
from pathlib import Path
from typing import Iterable, List, Tuple

from manifest_tools import update_version

REQUIRED_FIELDS = {"version", "filename", "arch", "platform", "download_url"}


def discover_partial_files(partials_dir: Path) -> List[Path]:
    return sorted(partials_dir.rglob("*.json"))


def load_entries(file_path: Path) -> List[dict]:
    with file_path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if isinstance(data, list):
        return data
    return []


def valid_entry(entry: dict) -> bool:
    return REQUIRED_FIELDS.issubset(entry.keys())


def ensure_manifest_file(manifest_file: Path) -> None:
    manifest_file.parent.mkdir(parents=True, exist_ok=True)
    if not manifest_file.exists():
        manifest_file.write_text("[]\n", encoding="utf-8")


def apply_entries(entries: Iterable[Tuple[Path, dict]], manifest_dir: Path) -> int:
    applied = 0
    for file_path, entry in entries:
        if not valid_entry(entry):
            continue
        manifest_file = manifest_dir / f"{entry['version']}-{entry['arch']}.json"
        ensure_manifest_file(manifest_file)
        update_version(  # type: ignore[arg-type]
            existing_file=str(manifest_file),
            version=entry["version"],
            filename=entry["filename"],
            arch=entry["arch"],
            platform=entry["platform"],
            download_url=entry["download_url"],
            platform_version=entry.get("platform_version"),
            stable=True,
        )
        applied += 1
        print(f"Applied entry from {file_path.name} to {manifest_file}")
    return applied


def main() -> int:
    parser = argparse.ArgumentParser(description="Apply partial manifest artifacts to arch-specific manifests.")
    parser.add_argument("--partials-dir", default="manifest-parts", help="Directory containing manifest-part artifacts")
    parser.add_argument("--manifest-dir", default="versions-manifests", help="Directory for arch-specific manifests")
    args = parser.parse_args()

    partials_path = Path(args.partials_dir)
    manifest_path = Path(args.manifest_dir)

    if not partials_path.exists():
        print(f"No partial manifests found in {partials_path}")
        return 0

    files = discover_partial_files(partials_path)
    if not files:
        print(f"No JSON files discovered under {partials_path}")
        return 0

    entries: List[Tuple[Path, dict]] = []
    for file_path in files:
        try:
            file_entries = load_entries(file_path)
        except json.JSONDecodeError as exc:
            print(f"Skipping {file_path}: invalid JSON ({exc})")
            continue
        for entry in file_entries:
            entries.append((file_path, entry))

    applied = apply_entries(entries, manifest_path)
    print(f"Applied {applied} manifest entries from {len(files)} partial files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
