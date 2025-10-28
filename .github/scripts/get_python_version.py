import requests
import sys
import argparse
import json
import re
from functools import cmp_to_key

MANIFEST_URL = "https://raw.githubusercontent.com/actions/python-versions/main/versions-manifest.json"
MANIFEST_FILE = "versions-manifest.json"

class PythonManifestParser:
    def __init__(self, manifest):
        if not manifest or not isinstance(manifest, list):
            raise ValueError("Manifest is empty or invalid.")
        self.manifest = manifest

    @staticmethod
    def is_alpha(version):
        return version.endswith("alpha") or "-alpha." in version or "-alpha" in version

    @staticmethod
    def is_beta(version):
        return version.endswith("beta") or "-beta." in version or "-beta" in version

    @staticmethod
    def is_rc(version):
        return version.endswith("rc") or "-rc." in version or "-rc" in version

    @classmethod
    def is_stable(cls, version):
        return not (cls.is_alpha(version) or cls.is_beta(version) or cls.is_rc(version))

    @staticmethod
    def parse_version(version):
        # Support variants like 3.9.0rc1 or 3.9.0-rc.1 or 3.9.0-rc1
        match = re.match(r"(\d+)\.(\d+)\.(\d+)(?:-?([a-z]+)(?:\.|)(\d+))?", version)
        if not match:
            return (0, 0, 0, 0, 0)
        major, minor, patch, pre, pre_num = match.groups()
        pre = pre or ''
        pre_num = int(pre_num) if pre_num else 0
        pre_order = {'': 0, 'rc': 1, 'beta': 2, 'alpha': 3}
        return (
            int(major),
            int(minor),
            int(patch),
            -pre_order.get(pre, 4),
            -pre_num
        )

    @classmethod
    def version_compare(cls, a, b):
        pa = cls.parse_version(a)
        pb = cls.parse_version(b)
        return (pa > pb) - (pa < pb)

    def filter_versions(self, include_beta=False, include_alpha=False, include_rc=False, only_stable=False, version_filter=None):
        versions = []
        include_prerelease = include_alpha or include_beta or include_rc

        for entry in self.manifest:
            version = entry.get("version")
            if not version:
                continue

            if only_stable:
                # Include only stable versions
                if self.is_stable(version):
                    versions.append(version)
                continue

            if include_prerelease:
                # Include only requested pre-release versions, exclude stable
                if include_alpha and self.is_alpha(version):
                    versions.append(version)
                elif include_beta and self.is_beta(version):
                    versions.append(version)
                elif include_rc and self.is_rc(version):
                    versions.append(version)
                # Do NOT include stable versions here
            else:
                # No flags - include stable versions only
                if self.is_stable(version):
                    versions.append(version)

        if version_filter:
            versions = [v for v in versions if PythonManifestParser.version_matches_filter(v, version_filter)]

        return versions

    @staticmethod
    def version_matches_filter(version, pattern):
        # Convert glob-like pattern (e.g., 3.5.*, 3.*.0) to regex
        regex = re.escape(pattern).replace(r'\*', '.*')
        return re.fullmatch(regex, version) is not None

    def list_versions(self, include_beta=False, include_alpha=False, include_rc=False, only_stable=False, version_filter=None):
        versions = self.filter_versions(include_beta, include_alpha, include_rc, only_stable, version_filter)
        versions.sort(key=cmp_to_key(self.version_compare), reverse=True)
        return versions

    def get_latest_version(self, include_beta=False, include_alpha=False, include_rc=False, only_stable=False, version_filter=None):
        versions = self.filter_versions(include_beta, include_alpha, include_rc, only_stable, version_filter)
        if not versions:
            return None
        versions.sort(key=cmp_to_key(self.version_compare), reverse=True)
        return versions[0]

def main():
    parser = argparse.ArgumentParser(
        description=(
            "Get or list Python versions from GitHub Actions manifest.\n"
            "By default, includes stable and any selected pre-release versions.\n"
            "Use --stable to only include stable versions."
        ),
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument('--list', action='store_true', help='List matching Python versions')
    parser.add_argument('--alpha', action='store_true', help='Include alpha versions')
    parser.add_argument('--beta', action='store_true', help='Include beta versions')
    parser.add_argument('--rc', action='store_true', help='Include release candidate versions')
    parser.add_argument('--stable', action='store_true', help='Only include stable versions')
    parser.add_argument('--latest', action='store_true', help='Print only the latest matching version')
    parser.add_argument('--filter', type=str, help='Glob pattern to filter versions (e.g., 3.5.*, 3.9.*, 3.*.0)')
    args = parser.parse_args()

    if not (args.list or args.latest):
        parser.print_help()
        sys.exit(0)

    try:
        resp = requests.get(MANIFEST_URL)
        resp.raise_for_status()
    except Exception as e:
        print(f"Failed to download manifest: {e}", file=sys.stderr)
        sys.exit(1)

    with open(MANIFEST_FILE, "wb") as f:
        f.write(resp.content)

    try:
        with open(MANIFEST_FILE, "r", encoding="utf-8") as f:
            manifest = json.load(f)
    except Exception as e:
        print(f"Failed to read manifest: {e}", file=sys.stderr)
        sys.exit(1)

    try:
        parser_obj = PythonManifestParser(manifest)
    except Exception as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)

    if args.list:
        for v in parser_obj.list_versions(
            include_beta=args.beta,
            include_alpha=args.alpha,
            include_rc=args.rc,
            only_stable=args.stable,
            version_filter=args.filter
        ):
            print(v)
    elif args.latest:
        latest = parser_obj.get_latest_version(
            include_beta=args.beta,
            include_alpha=args.alpha,
            include_rc=args.rc,
            only_stable=args.stable,
            version_filter=args.filter
        )
        if latest:
            print(latest)
        else:
            print("No version found with the specified filters.", file=sys.stderr)
            sys.exit(1)

if __name__ == "__main__":
    main()
