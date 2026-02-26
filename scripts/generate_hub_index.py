#!/usr/bin/env python3
"""
Generate hub/scoda-hub-index.json from package repo releases.

Reads hub/sources.json for the list of source repositories,
queries GitHub REST API for their latest releases, collects package
metadata (from *.manifest.json assets or fallback from release info),
and writes hub/scoda-hub-index.json.

Usage:
  python scripts/generate_hub_index.py              # generate scoda-hub-index.json
  python scripts/generate_hub_index.py --dry-run    # preview without writing
  python scripts/generate_hub_index.py --all        # include all versions, not just latest

No external dependencies — uses only Python stdlib (urllib).
Set GITHUB_TOKEN env var for higher API rate limits (optional for public repos).
"""

import argparse
import json
import os
import re
import sys
import urllib.request
import urllib.error
from datetime import datetime, timezone

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
SOURCES_PATH = os.path.join(PROJECT_ROOT, 'hub', 'sources.json')
INDEX_PATH = os.path.join(PROJECT_ROOT, 'hub', 'scoda-hub-index.json')

# Pattern for versioned .scoda filenames: name-version.scoda
SCODA_FILENAME_RE = re.compile(r'^(.+?)-(\d+\.\d+\.\d+)\.scoda$')

GITHUB_API = 'https://api.github.com'


def _api_headers():
    """Build HTTP headers for GitHub API requests."""
    headers = {
        'Accept': 'application/vnd.github+json',
        'User-Agent': 'scoda-hub-index-generator',
    }
    token = os.environ.get('GITHUB_TOKEN')
    if token:
        headers['Authorization'] = f'Bearer {token}'
    return headers


def _api_get(url):
    """GET a GitHub API URL and return parsed JSON."""
    req = urllib.request.Request(url, headers=_api_headers())
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        print(f"  HTTP {e.code} for {url}", file=sys.stderr)
        return None


def _download_text(url):
    """Download a URL and return content as string."""
    headers = _api_headers()
    # For asset downloads, accept octet-stream
    headers['Accept'] = 'application/octet-stream'
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.read().decode()
    except urllib.error.HTTPError:
        return None


def fetch_releases(repo, all_versions=False):
    """Fetch releases from a GitHub repo via REST API.

    Args:
        repo: GitHub repo in 'owner/repo' format.
        all_versions: If True, fetch all releases. Otherwise only latest.

    Returns:
        List of release dicts.
    """
    if all_versions:
        data = _api_get(f'{GITHUB_API}/repos/{repo}/releases')
        return data if isinstance(data, list) else []
    else:
        data = _api_get(f'{GITHUB_API}/repos/{repo}/releases/latest')
        return [data] if data else []


def process_release(repo, release):
    """Process a single release and extract package entries.

    Tries to use *.manifest.json assets first.
    Falls back to inferring metadata from .scoda asset filenames.

    Returns:
        List of (package_id, version, entry_dict) tuples.
    """
    tag = release.get('tag_name', '')
    published = release.get('published_at', '')
    assets = release.get('assets', [])

    results = []

    # Collect asset info by name
    asset_map = {}
    for asset in assets:
        name = asset.get('name', '')
        asset_map[name] = {
            'download_url': asset.get('browser_download_url', ''),
            'api_url': asset.get('url', ''),  # for downloading via API
            'size': asset.get('size', 0),
        }

    # Strategy 1: Use *.manifest.json files
    manifest_assets = [n for n in asset_map if n.endswith('.manifest.json')]
    for manifest_name in manifest_assets:
        api_url = asset_map[manifest_name]['api_url']
        content = _download_text(api_url)
        if not content:
            continue
        try:
            manifest = json.loads(content)
        except json.JSONDecodeError:
            print(f"  WARNING: Invalid JSON in {manifest_name}", file=sys.stderr)
            continue

        pkg_id = manifest.get('package_id', '')
        version = manifest.get('version', '')
        if not pkg_id or not version:
            continue

        # Find corresponding .scoda asset
        filename = manifest.get('filename', f'{pkg_id}-{version}.scoda')
        scoda_info = asset_map.get(filename, {})

        entry = {
            'title': manifest.get('title', pkg_id),
            'description': manifest.get('description', ''),
            'download_url': scoda_info.get('download_url', ''),
            'sha256': manifest.get('sha256', ''),
            'size_bytes': scoda_info.get('size') or manifest.get('size_bytes', 0),
            'dependencies': manifest.get('dependencies', {}),
            'engine_compat': manifest.get('engine_compat', ''),
            'scoda_format_version': manifest.get('scoda_format_version', '1.0'),
            'license': manifest.get('license', ''),
            'created_at': manifest.get('created_at', published),
            'source_release': f'https://github.com/{repo}/releases/tag/{tag}',
        }
        results.append((pkg_id, version, entry))

    # Strategy 2: Fallback — infer from .scoda filenames
    if not manifest_assets:
        scoda_assets = [n for n in asset_map if n.endswith('.scoda')]
        for scoda_name in scoda_assets:
            m = SCODA_FILENAME_RE.match(scoda_name)
            if not m:
                continue
            pkg_id = m.group(1)
            version = m.group(2)
            info = asset_map[scoda_name]

            entry = {
                'title': pkg_id,
                'description': '',
                'download_url': info['download_url'],
                'sha256': '',
                'size_bytes': info['size'],
                'dependencies': {},
                'engine_compat': '',
                'scoda_format_version': '1.0',
                'license': '',
                'created_at': published,
                'source_release': f'https://github.com/{repo}/releases/tag/{tag}',
            }
            results.append((pkg_id, version, entry))

    return results


def generate_index(sources, all_versions=False):
    """Generate index dict from source repos.

    Args:
        sources: List of source dicts from hub/sources.json.
        all_versions: If True, include all release versions.

    Returns:
        index dict ready to serialize as JSON.
    """
    packages = {}

    for src in sources:
        repo = src['repo']
        src_type = src.get('type', 'github_releases')

        if src_type != 'github_releases':
            print(f"  WARNING: Unknown source type '{src_type}' for {repo}, skipping",
                  file=sys.stderr)
            continue

        print(f"Fetching releases from {repo}...")
        releases = fetch_releases(repo, all_versions=all_versions)
        if not releases:
            print(f"  No releases found for {repo}")
            continue

        print(f"  Found {len(releases)} release(s)")

        for release in releases:
            entries = process_release(repo, release)
            for pkg_id, version, entry in entries:
                if pkg_id not in packages:
                    packages[pkg_id] = {'latest': version, 'versions': {}}
                packages[pkg_id]['versions'][version] = entry
                print(f"  Collected: {pkg_id} v{version}")

    # Determine latest version for each package (highest semver)
    for pkg_id, pkg_data in packages.items():
        versions = sorted(pkg_data['versions'].keys(), key=_semver_key, reverse=True)
        if versions:
            pkg_data['latest'] = versions[0]

    source_list = [{'repo': s['repo'], 'type': s.get('type', 'github_releases')}
                   for s in sources]

    return {
        'hub_version': '1.0',
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'sources': source_list,
        'packages': packages,
    }


def _semver_key(version_str):
    """Parse version string into sortable tuple."""
    parts = version_str.split('.')
    result = []
    for p in parts:
        try:
            result.append(int(p))
        except ValueError:
            result.append(0)
    while len(result) < 3:
        result.append(0)
    return tuple(result)


def main():
    parser = argparse.ArgumentParser(
        description='Generate hub/scoda-hub-index.json from package repo releases')
    parser.add_argument(
        '--sources', default=SOURCES_PATH,
        help=f'Path to sources.json (default: hub/sources.json)')
    parser.add_argument(
        '--output', default=INDEX_PATH,
        help=f'Output path (default: hub/scoda-hub-index.json)')
    parser.add_argument(
        '--all', action='store_true',
        help='Include all release versions (default: latest only)')
    parser.add_argument(
        '--dry-run', action='store_true',
        help='Print index to stdout without writing file')
    args = parser.parse_args()

    # Load sources
    if not os.path.exists(args.sources):
        print(f"Error: Sources file not found: {args.sources}", file=sys.stderr)
        sys.exit(1)

    with open(args.sources) as f:
        sources = json.load(f)

    if not sources:
        print("Error: No sources defined in sources.json", file=sys.stderr)
        sys.exit(1)

    print(f"Sources: {len(sources)} repo(s)")

    # Generate index
    index = generate_index(sources, all_versions=args.all)

    pkg_count = len(index['packages'])
    version_count = sum(len(p['versions']) for p in index['packages'].values())
    print(f"\nGenerated: {pkg_count} package(s), {version_count} version(s)")

    if args.dry_run:
        print("\n--- scoda-hub-index.json (dry-run) ---")
        print(json.dumps(index, indent=2, ensure_ascii=False))
    else:
        os.makedirs(os.path.dirname(args.output), exist_ok=True)
        with open(args.output, 'w') as f:
            json.dump(index, f, indent=2, ensure_ascii=False)
            f.write('\n')
        print(f"Written: {args.output}")


if __name__ == '__main__':
    main()
