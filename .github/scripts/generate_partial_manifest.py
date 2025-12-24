import argparse
import json
import sys
from typing import Any, Dict, List, Optional, Tuple

PREFIXES = ("python-", "trivy-python-")
SUFFIXES = (".tar.gz", ".sbom.json", ".json", ".log")


def validate_download_url(url: str, owner: str, repo: str, tag: str, filename: str) -> bool:
    """Validate that download_url is well-formed and points to a release asset.
    
    Note: GitHub may initially serve assets via temporary "untagged" URLs.
    We validate the basic structure and accept it, knowing we'll construct
    the final URL ourselves to avoid issues with ephemeral URLs.
    """
    if not url or not url.strip():
        return False
    
    # Must be HTTPS and from GitHub releases
    if not url.startswith("https://github.com/"):
        return False
    
    # Must be from the correct owner/repo releases
    expected_base = f"https://github.com/{owner}/{repo}/releases/download/"
    if not url.startswith(expected_base):
        return False
    
    # URL structure is valid - we'll construct the final URL ourselves
    # to avoid issues with temporary "untagged-" URLs from GitHub
    return True


def strip_known_wrappers(filename: str) -> str:
    """Remove known prefixes and suffixes from the asset name."""
    cleaned = filename
    for prefix in PREFIXES:
        if cleaned.startswith(prefix):
            cleaned = cleaned[len(prefix) :]
            break
    for suffix in SUFFIXES:
        if cleaned.endswith(suffix):
            cleaned = cleaned[: -len(suffix)]
            break
    return cleaned


def parse_filename(filename: str) -> Optional[Dict[str, str]]:
    """Extract platform metadata from a release asset filename."""
    stripped = strip_known_wrappers(filename)
    parts = stripped.split("-")
    if len(parts) < 4:
        return None

    return {
        "version": parts[0],
        "platform": parts[1],
        "platform_version": parts[2],
        "arch": parts[3],
    }


def should_skip(name: str) -> bool:
    return not name.endswith(".tar.gz") or "trivy" in name


def build_manifest_entries(tag: str, assets: List[Dict[str, Any]], owner: str, repo: str) -> Tuple[List[Dict[str, str]], List[str]]:
    """Build manifest entries and return (entries, validation_errors)."""
    entries: List[Dict[str, str]] = []
    errors: List[str] = []
    
    for asset in assets:
        name = asset.get("name", "")
        if should_skip(name):
            continue

        parsed = parse_filename(name)
        if not parsed:
            errors.append(f"Filename parsing failed for asset '{name}'")
            continue

        download_url = asset.get("browser_download_url", "")
        
        # Validate URL structure (basic sanity check)
        if not validate_download_url(download_url, owner, repo, tag, name):
            errors.append(
                f"Invalid download_url for '{name}': expected "
                f"'https://github.com/{owner}/{repo}/releases/download/{tag}/{name}', "
                f"got '{download_url}'"
            )
            continue

        # Construct the permanent, tagged download URL to avoid "untagged-*" ephemeral URLs
        # GitHub may initially serve assets via temporary URLs, so we construct the final one
        final_download_url = f"https://github.com/{owner}/{repo}/releases/download/{tag}/{name}"

        entries.append(
            {
                "version": tag,
                "filename": name,
                "arch": parsed["arch"],
                "platform": parsed["platform"],
                "platform_version": parsed["platform_version"],
                "download_url": final_download_url,
            }
        )
    
    return entries, errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate partial manifest entries from release assets.")
    parser.add_argument("--tag", required=True, help="Release tag used for the manifest version field.")
    parser.add_argument("--owner", required=True, help="GitHub repository owner (e.g., 'IBM').")
    parser.add_argument("--repo", required=True, help="GitHub repository name (e.g., 'python-versions-pz').")
    
    # Mutually exclusive group: Accept EITHER string OR file
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--assets", help="Raw JSON string (Legacy/Direct Input)")
    group.add_argument("--assets-file", help="Path to JSON file containing assets (Recommended for CI)")
    
    args = parser.parse_args()

    # Logic to load assets from either source
    assets = []
    try:
        if args.assets_file:
            print(f"Reading assets from file: {args.assets_file}", file=sys.stderr)
            with open(args.assets_file, 'r', encoding='utf-8') as f:
                assets = json.load(f)
        elif args.assets:
            # Legacy support for workflows passing raw strings
            print(f"Parsing assets from command-line string", file=sys.stderr)
            assets = json.loads(args.assets)
    except json.JSONDecodeError as exc:
        print(f"Error decoding JSON: {exc}", file=sys.stderr)
        return 1
    except FileNotFoundError as exc:
        print(f"Assets file not found: {args.assets_file}", file=sys.stderr)
        return 1

    manifest_entries, errors = build_manifest_entries(args.tag, assets, args.owner, args.repo)
    
    # Report validation errors
    if errors:
        for error in errors:
            print(f"Validation error: {error}", file=sys.stderr)
        if not manifest_entries:
            print(f"ERROR: No valid assets found after validation. Aborting.", file=sys.stderr)
            return 1
        # Warn but continue if some assets are valid
        print(f"Warning: {len(errors)} asset(s) failed validation but {len(manifest_entries)} remain.", file=sys.stderr)
    
    json.dump(manifest_entries, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
