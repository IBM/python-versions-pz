import json
from models import ManifestEntry, FileEntry
import typer

app = typer.Typer()

# Fetch remote manifest and save as new file
def manifest_fetch(url: str, output_file: str):
    import requests
    response = requests.get(url)
    response.raise_for_status()
    manifest_data = response.json()
    manifest = [ManifestEntry(**entry) for entry in manifest_data]
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump([entry.model_dump() for entry in manifest], f, indent=2)
    print(f"Remote manifest saved to {output_file}")

# Merge two manifest files and save result
def manifest_merge(existing_file: str, remote_file: str, output_file: str):
    with open(existing_file, 'r', encoding='utf-8') as f:
        existing_data = json.load(f)
    with open(remote_file, 'r', encoding='utf-8') as f:
        remote_data = json.load(f)
    existing = [ManifestEntry(**entry) for entry in existing_data]
    remote = [ManifestEntry(**entry) for entry in remote_data]
    combined = {entry.version: entry for entry in existing}
    for entry in remote:
        if entry.version in combined:
            # Merge files arrays, avoid duplicates by filename
            existing_files = {f.filename: f for f in combined[entry.version].files}
            for f in entry.files:
                if f.filename not in existing_files:
                    combined[entry.version].files.append(f)
        else:
            combined[entry.version] = entry
    merged = list(combined.values())
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump([entry.model_dump() for entry in merged], f, indent=2)
    print(f"Merged manifest saved to {output_file}")

@app.command("download", help="Fetch remote manifest and save as new file.")
def download(url: str, output_file: str):
    manifest_fetch(url, output_file)

@app.command("merge", help="Merge two manifest files and save result.")
def merge(existing_file: str, remote_file: str, output_file: str):
    manifest_merge(existing_file, remote_file, output_file)

@app.command("update_version", help="Append a new file entry to a given version in the manifest. Creates version block if it doesn't exist.")
def update_version(
    existing_file: str,
    version: str = typer.Option(..., help="Manifest version (e.g., 3.14.0-beta.1)"),
    filename: str = typer.Option(..., help="Artifact filename"),
    arch: str = typer.Option(..., help="Architecture (e.g., x64, arm64, x64-freethreaded)"),
    platform: str = typer.Option(..., help="Platform (e.g., linux, darwin)"),
    download_url: str = typer.Option(..., help="Direct download URL"),
    platform_version: str = typer.Option(None, help="Platform version (optional, e.g., 22.04)"),
    stable: bool = typer.Option(False, help="Is this a stable release?")
):
    with open(existing_file, 'r', encoding='utf-8') as f:
        manifest = [ManifestEntry(**entry) for entry in json.load(f)]
    new_file = FileEntry(
        filename=filename,
        arch=arch,
        platform=platform,
        platform_version=platform_version,
        download_url=download_url
    )
    for entry in manifest:
        if entry.version == version:
            # Check if file entry already exists by filename, arch, platform, and platform_version
            exists = any(
                f.filename == filename and f.arch == arch and f.platform == platform and f.platform_version == platform_version
                for f in entry.files
            )
            if not exists:
                entry.files.append(new_file)
                with open(existing_file, 'w', encoding='utf-8') as f:
                    json.dump([entry.model_dump() for entry in manifest], f, indent=2)
                print(f"✅ File added to version: {version}")
            else:
                print(f"⚠️ File entry already exists for version: {version}")
            break
    else:
        manifest.append(ManifestEntry(
            version=version,
            stable=stable,
            release_url="",
            files=[new_file]
        ))
        with open(existing_file, 'w', encoding='utf-8') as f:
            json.dump([entry.model_dump() for entry in manifest], f, indent=2)
        print(f"✅ File added to version: {version}")

if __name__ == "__main__":
    app()
