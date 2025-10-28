"""
.NET SDK Installer for IBM Architectures (s390x, ppc64le)

This script automates the process of selecting and installing a .NET SDK version
that is available on both IBM's GitHub releases and NuGet.org.
This ensures compatibility between platform-specific binaries (IBM) and official metadata (NuGet).
"""

# Standard library imports
import os
import re
import tarfile
import tempfile
import shutil
import json
import urllib.request
import bisect
from typing import Optional, List, Tuple, NamedTuple

# Third-party imports
import typer

# Constants
GH_USER = "IBM"
GH_REPO = "dotnet-s390x"
INSTALL_DIR = "/usr/share/dotnet"
NUGET_PACKAGE = "microsoft.netcore.app.runtime.linux-x64"

app = typer.Typer()

def get_nuget_versions(package: str) -> List[str]:
    """Fetch official .NET runtime versions from NuGet.org."""
    url = f"https://api.nuget.org/v3-flatcontainer/{package}/index.json"
    try:
        with urllib.request.urlopen(url) as response:
            if response.status >= 400:
                return []
            data = json.loads(response.read())
            return data.get("versions", [])
    except Exception:
        return []

class Version(NamedTuple):
    major: int
    minor: int
    patch: int
    stage_priority: int
    stage_number: int
    build: Tuple[int, ...]

def parse_version(tag: str) -> Version:
    """Parse a .NET SDK tag string into a Version tuple for comparison and sorting."""
    tag = tag.lstrip("v")
    base_part, _, suffix = tag.partition("-")
    parts = base_part.split(".")
    major, minor, patch = map(int, parts[:3])

    # Priority order: stable > rtm > rc > preview > alpha > unknown
    stage_priority_map = {
        "alpha": 0,
        "preview": 1,
        "rc": 2,
        "rtm": 3,
        None: 4  # stable (no suffix)
    }

    stage = None
    stage_number = 0
    build = ()

    if suffix:
        # Match full format: preview.7.25351.106
        full_match = re.match(r"(alpha|preview|rc|rtm)\.(\d+)\.([\d.]+)", suffix)
        if full_match:
            stage = full_match.group(1)
            stage_number = int(full_match.group(2))
            build = tuple(map(int, full_match.group(3).split(".")))
        else:
            # Match short format: rtm.24503.15
            simple_match = re.match(r"(alpha|preview|rc|rtm)\.([\d.]+)", suffix)
            if simple_match:
                stage = simple_match.group(1)
                stage_number = 0
                build = tuple(map(int, simple_match.group(2).split(".")))
            else:
                # Unknown format: assign lowest priority
                stage = "unknown"
                stage_number = 0
                build = ()

    return Version(
        major=major,
        minor=minor,
        patch=patch,
        stage_priority=stage_priority_map.get(stage, -1),
        stage_number=stage_number,
        build=build
    )

def version_to_string(v: Version) -> str:
    """Convert a Version tuple back to a NuGet-style version string."""
    base = f"{v.major}.{v.minor}.{v.patch}"
    if v.stage_priority < 4:
        suffix = {
            0: "alpha",
            1: "preview",
            2: "rc",
            3: "rtm"
        }[v.stage_priority]
        build = ".".join(str(x) for x in v.build)
        return f"{base}-{suffix}.{v.stage_number}.{build}"
    return base

def is_version_in_nuget(nuget_versions: set, version: Version) -> bool:
    """Return True if the normalized version exists in the NuGet version set."""
    return normalized_version_for_nuget(version) in nuget_versions

def normalized_version_for_nuget(v: Version) -> str:
    """Normalize IBM Version to NuGet-style for version comparison (patch=0)."""
    base = f"{v.major}.{v.minor}.0"
    if v.stage_priority < 4:
        suffix = {
            0: "alpha",
            1: "preview",
            2: "rc",
            3: "rtm"
        }[v.stage_priority]
        build = ".".join(str(x) for x in v.build)
        return f"{base}-{suffix}.{v.stage_number}.{build}"
    return base

def resolve_tag(tag_input: Optional[str], tags: List[dict]) -> str:
    """Return the best tag match for the given input or raise if not found."""
    if not tag_input:
        return None
    matched = [t for t in tags if t["tag_name"] == tag_input]
    if matched:
        return matched[0]["tag_name"]
    prefix_matches = [t for t in tags if t["tag_name"].startswith(tag_input)]
    if prefix_matches:
        sorted_matches = sorted(prefix_matches, key=lambda x: parse_version(x["tag_name"]), reverse=True)
        chosen = sorted_matches[0]["tag_name"]
        typer.echo(f"⚠️ Exact tag not found. Using nearest match: {chosen}")
        return chosen
    typer.echo(f"❌ No matching or compatible version found for: {tag_input}")
    raise typer.Exit(1)

def find_closest_version_tag(all_tags: List[dict], input_tag: str) -> str:
    """Find the closest matching tag by version order."""
    normalized = input_tag if input_tag.startswith("v") else f"v{input_tag}"
    parsed_tags = []
    version_to_tag_map = {}
    for tag in all_tags:
        try:
            version_tuple = parse_version(tag["tag_name"])
            parsed_tags.append(version_tuple)
            version_to_tag_map[version_tuple] = tag["tag_name"]
        except Exception:
            # Skip tags that cannot be parsed
            continue
    parsed_tags.sort()
    target_version = parse_version(normalized)
    if target_version in version_to_tag_map:
        return version_to_tag_map[target_version]
    index = bisect.bisect_left(parsed_tags, target_version)
    if index > 0:
        return version_to_tag_map[parsed_tags[index - 1]]
    elif index < len(parsed_tags):
        return version_to_tag_map[parsed_tags[index]]
    raise typer.Exit(f"❌ No compatible version found for: {input_tag}")

PROFILE_SCRIPT = "/etc/profile.d/dotnet.sh"

def fetch_json(url: str) -> List[dict]:
    """Download and parse JSON response from a given URL."""
    with urllib.request.urlopen(url) as response:
        if response.status >= 400:
            raise typer.Exit(f"❌ Failed to fetch {url}")
        return json.loads(response.read())

def get_all_tags() -> List[dict]:
    """Fetch all release tags from the IBM GitHub repository."""
    all_tags = []
    page = 1
    while True:
        url = f"https://api.github.com/repos/{GH_USER}/{GH_REPO}/releases?per_page=100&page={page}"
        page_data = fetch_json(url)
        if not page_data:
            break
        all_tags.extend(page_data)
        page += 1
    return all_tags

def get_release_by_tag(tag: str) -> dict:
    """Fetch release metadata for a specific tag from GitHub."""
    if tag == "latest":
        url = f"https://api.github.com/repos/{GH_USER}/{GH_REPO}/releases/latest"
    else:
        url = f"https://api.github.com/repos/{GH_USER}/{GH_REPO}/releases/tags/{tag}"
    return fetch_json(url)

def filter_and_sort_tags(tags: List[dict], prefix: Optional[str]) -> List[dict]:
    """Filter tags by prefix and sort by version descending."""
    filtered = [t for t in tags if t.get("tag_name")]
    if prefix:
        # Remove leading 'v' from filter if present
        norm_prefix = prefix[1:] if prefix.startswith('v') else prefix
        # Escape regex special chars except '*', then replace '*' with '.*'
        regex_pattern = re.escape(norm_prefix).replace(r'\*', '.*')
        # Allow optional leading 'v' and match anywhere in the tag
        regex = re.compile(rf"v?{regex_pattern}", re.IGNORECASE)
        filtered = [t for t in filtered if regex.search(t["tag_name"])]
    return sorted(filtered, key=lambda x: parse_version(x["tag_name"]), reverse=True)

def select_tag_interactive(tags: List[dict], filter_prefix: Optional[str]) -> str:
    """Prompt user to select a tag interactively."""
    filtered = filter_and_sort_tags(tags, filter_prefix)
    if not filtered:
        typer.echo("❌ No matching tags found.")
        raise typer.Exit()
    typer.echo("\n--- Available Tags ---")
    typer.echo("0) latest (Recommended)")
    for i, tag in enumerate(filtered, start=1):
        typer.echo(f"{i}) {tag['tag_name']}")
    typer.echo("----------------------")
    while True:
        choice = typer.prompt("Enter the number of the tag to install", default="0")
        if choice.isdigit():
            index = int(choice)
            if index == 0:
                return "latest"
            if 1 <= index <= len(filtered):
                return filtered[index - 1]["tag_name"]
        typer.echo("❌ Invalid choice. Try again.")

def download_file(url: str, dest_path: str) -> None:
    """Download a file from a URL to a destination path."""
    with urllib.request.urlopen(url) as response:
        if response.status >= 400:
            raise typer.Exit(f"❌ Failed to download {url}")
        if "html" in response.headers.get("Content-Type", "").lower():
            raise typer.Exit("❌ Downloaded file is HTML, not a tarball.")
        with open(dest_path, "wb") as out_file:
            shutil.copyfileobj(response, out_file)

def extract_tarball(tar_path: str, dest_dir: str) -> None:
    """Extract a tar.gz archive to a destination directory."""
    if not tarfile.is_tarfile(tar_path):
        raise typer.Exit("❌ Downloaded file is not a valid tar archive.")
    with tarfile.open(tar_path, "r:gz") as tar:
        tar.extractall(dest_dir)

def setup_environment() -> None:
    """Set up environment variables and profile script for dotnet CLI."""
    os.makedirs(os.path.dirname(PROFILE_SCRIPT), exist_ok=True)
    with open(PROFILE_SCRIPT, "w") as f:
        f.write(f'export DOTNET_ROOT="{INSTALL_DIR}"\n')
        f.write(r'export PATH="$DOTNET_ROOT:$PATH"\n')
    os.chmod(PROFILE_SCRIPT, 0o755)

def verify_installation() -> None:
    """Verify that dotnet CLI is available and functional."""
    os.environ["DOTNET_ROOT"] = INSTALL_DIR
    os.environ["PATH"] = f"{INSTALL_DIR}:{os.environ.get('PATH', '')}"
    if shutil.which("dotnet") is None:
        raise typer.Exit("❌ dotnet is not available in PATH.")
    typer.echo("\n--- dotnet --info ---")
    os.system("dotnet --info")
    typer.echo("---------------------")

@app.command(help="""
Install the .NET SDK for IBM Architectures (s390x, ppc64le).

Use --tag to install a specific version directly (non-interactive).
Use --filter to narrow down choices in interactive mode.
""")
def install_dotnet(
    tag: Optional[str] = typer.Option(
        None,
        help="Install a specific tag version (e.g., v9.0.100). If not provided, runs in interactive mode."
    ),
    filter: Optional[str] = typer.Option(
        None,
        "--filter",
        help="Filter tags by prefix in interactive mode (e.g., 9.0 or v8). Has no effect when using --tag."
    ),
) -> None:
    """Main command entry for installing .NET SDK."""
    arch = os.uname().machine
    if arch not in ["ppc64le", "s390x"]:
        typer.echo(f"❌ Unsupported architecture: {arch}")
        raise typer.Exit(1)
    typer.echo("📡 Fetching tags from GitHub...")
    all_tags = get_all_tags()
    if not tag:
        selected_tag = select_tag_interactive(all_tags, filter)
    else:
        requested_version = parse_version(tag.lstrip("v"))
        # Limit IBM releases to only those sharing the same major version as requested.
        ibm_parsed = []
        version_to_tag_map = {}
        for t in all_tags:
            try:
                v = parse_version(t["tag_name"])
                if v.major == requested_version.major:
                    ibm_parsed.append(v)
                    version_to_tag_map[v] = t["tag_name"]
            except Exception:
                continue
        if not ibm_parsed:
            typer.echo("❌ No IBM releases match the requested major version.")
            raise typer.Exit(1)
        ibm_parsed.sort()
        idx = bisect.bisect_left(ibm_parsed, requested_version)
        typer.echo("📡 Fetching versions from NuGet...")
        nuget_versions = get_nuget_versions(NUGET_PACKAGE)
        nuget_set = set(nuget_versions)
        chosen = None
        # Exact match check
        if idx < len(ibm_parsed) and ibm_parsed[idx] == requested_version:
            if is_version_in_nuget(nuget_set, requested_version):
                chosen = version_to_tag_map[requested_version]
        # Fallback: search in both directions for closest compatible version
        if not chosen:
            for offset in range(len(ibm_parsed)):
                for direction in [1, -1]:
                    i = idx + direction * offset
                    if i < 0 or i >= len(ibm_parsed):
                        continue
                    candidate = ibm_parsed[i]
                    if candidate.major != requested_version.major:
                        continue
                    if is_version_in_nuget(nuget_set, candidate):
                        chosen = version_to_tag_map[candidate]
                        typer.echo(f"⚠️ Using nearest IBM version: {chosen}")
                        break
                if chosen:
                    break
        if not chosen:
            typer.echo(f"❌ No matching IBM+NuGet compatible version found for: {tag}")
            raise typer.Exit(1)
        typer.echo(f"✅ Resolved tag: {chosen}")
        selected_tag = chosen
    typer.echo(f"📦 Selected tag: {selected_tag}")
    release = get_release_by_tag(selected_tag)
    assets = release.get("assets", [])
    sdk_asset = next(
        (a for a in assets if a["name"].startswith("dotnet-sdk-") and arch in a["name"] and a["name"].endswith(".tar.gz")),
        None,
    )
    if not sdk_asset:
        typer.echo("❌ No .NET SDK asset found for your architecture.")
        raise typer.Exit(1)
    with tempfile.TemporaryDirectory() as tmp:
        download_path = os.path.join(tmp, sdk_asset["name"])
        typer.echo(f"⬇️ Downloading {sdk_asset['name']}...")
        download_file(sdk_asset["browser_download_url"], download_path)
        typer.echo(f"📂 Extracting to {INSTALL_DIR}...")
        os.makedirs(INSTALL_DIR, exist_ok=True)
        extract_tarball(download_path, INSTALL_DIR)
    typer.echo("🔧 Setting up environment...")
    setup_environment()
    typer.echo("🔍 Verifying installation...")
    verify_installation()
    typer.echo("✅ .NET SDK installation complete!")

if __name__ == "__main__":
    app()
