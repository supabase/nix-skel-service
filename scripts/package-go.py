#!/usr/bin/env python3
"""Interactive scaffold script for packaging a Go service with Nix."""

import json
import os
import re
import subprocess
import sys

CONFIG_FILE = ".package-config.json"


def load_existing_config():
    """Load existing config if present, return defaults otherwise."""
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE) as f:
            return json.load(f)
    return None


def prompt(message, default=None):
    """Prompt user for input with optional default."""
    if default:
        value = input(f"{message} [{default}]: ").strip()
        return value if value else default
    while True:
        value = input(f"{message}: ").strip()
        if value:
            return value
        print("  Value cannot be empty.")


def parse_github_url(url):
    """Parse owner/repo from various GitHub URL formats."""
    url = url.strip().rstrip("/")
    # Handle: github.com/owner/repo, https://github.com/owner/repo,
    #         github.com/owner/repo.git
    url = re.sub(r"^https?://", "", url)
    url = re.sub(r"\.git$", "", url)
    match = re.match(r"^github\.com/([^/]+)/([^/]+)$", url)
    if not match:
        return None, None
    return match.group(1), match.group(2)


def validate_github_ref(owner, repo, ref):
    """Check that the GitHub tarball URL resolves (HTTP HEAD)."""
    url = f"https://github.com/{owner}/{repo}/archive/{ref}.tar.gz"
    try:
        result = subprocess.run(
            ["curl", "-sS", "-o", "/dev/null", "-w", "%{http_code}", "--head", url],
            capture_output=True,
            text=True,
            timeout=30,
        )
        status = result.stdout.strip()
        # GitHub returns 302 redirect for valid archives
        return status in ("200", "302")
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError):
        return False


def prefetch_source(owner, repo, ref):
    """Prefetch source tarball and return SRI hash."""
    url = f"https://github.com/{owner}/{repo}/archive/{ref}.tar.gz"
    print(f"  Prefetching source from {url} ...")
    try:
        result = subprocess.run(
            ["nix-prefetch-url", "--unpack", "--type", "sha256", url],
            capture_output=True,
            text=True,
            timeout=300,
        )
        if result.returncode != 0:
            print(f"  Error: nix-prefetch-url failed:\n{result.stderr}")
            return None
        nix_hash = result.stdout.strip().split("\n")[-1]

        # Convert to SRI format
        sri_result = subprocess.run(
            [
                "nix",
                "hash",
                "convert",
                "--to",
                "sri",
                "--hash-algo",
                "sha256",
                nix_hash,
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if sri_result.returncode != 0:
            print(f"  Error: nix hash convert failed:\n{sri_result.stderr}")
            return None
        return sri_result.stdout.strip()
    except subprocess.TimeoutExpired:
        print("  Error: prefetch timed out.")
        return None


def compute_vendor_hash(config):
    """Compute vendorHash by building with fakeHash and extracting the real hash."""
    print("  Computing vendorHash (building with fake hash to get real one)...")

    # Write temp config with fakeHash for vendor
    tmp_config = config.copy()
    tmp_config["vendorHash"] = "sha256-AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA="
    with open(CONFIG_FILE, "w") as f:
        json.dump(tmp_config, f, indent=2)
        f.write("\n")

    try:
        result = subprocess.run(
            ["nix", "build", f".#{config['name']}", "--no-link"],
            capture_output=True,
            text=True,
            timeout=600,
        )
        stderr = result.stderr

        # Look for the "got:" line with the real hash
        for line in stderr.split("\n"):
            line = line.strip()
            if line.startswith("got:"):
                vendor_hash = line.split()[-1]
                if vendor_hash.startswith("sha256-"):
                    return vendor_hash

        # If we didn't find a hash mismatch, the build failed for another reason
        if result.returncode != 0:
            print("  Error: nix build failed for a reason other than hash mismatch:")
            print(stderr[-2000:] if len(stderr) > 2000 else stderr)
            return None

        # Build succeeded with fake hash — this means no vendor deps (unlikely for Go)
        return "sha256-AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA="
    except subprocess.TimeoutExpired:
        print("  Error: nix build timed out.")
        return None


def main():
    if len(sys.argv) < 2 or sys.argv[1] != "go":
        print("Usage: package-go.py go")
        print("Only 'go' is supported currently.")
        sys.exit(1)

    print("=== Nix Go Service Packager ===\n")

    existing = load_existing_config()
    is_retry = existing is not None and existing.get("name") != "my-go-service"

    if is_retry:
        print(
            f"Found existing config for '{existing['name']}'. Values shown as defaults.\n"
        )

    # 1. Gather inputs
    name = prompt(
        "Package name (e.g. auth)",
        existing["name"] if is_retry else None,
    )

    description = prompt(
        "Description (e.g. Supabase Auth server)",
        existing.get("description") if is_retry else None,
    )

    default_url = (
        f"github.com/{existing['owner']}/{existing['repo']}" if is_retry else None
    )
    while True:
        gh_url = prompt("GitHub URL (e.g. github.com/supabase/auth)", default_url)
        owner, repo = parse_github_url(gh_url)
        if owner and repo:
            break
        print("  Invalid GitHub URL. Expected format: github.com/owner/repo")

    ref = prompt(
        "Git tag or commit to package (e.g. v2.175.0)",
        existing.get("ref") if is_retry else None,
    )

    # 2. Validate ref exists
    print(f"\nValidating {owner}/{repo} @ {ref} ...")
    if not validate_github_ref(owner, repo, ref):
        print(f"  Error: Could not resolve {owner}/{repo} at ref '{ref}'.")
        print("  Check the URL and ref, then re-run `just package go`.")
        sys.exit(1)
    print("  OK\n")

    # 3. Prefetch source hash
    sha256 = prefetch_source(owner, repo, ref)
    if not sha256:
        print("  Failed to compute source hash. Re-run `just package go` to retry.")
        sys.exit(1)
    print(f"  Source hash: {sha256}\n")

    # 4. Compute vendorHash
    config = {
        "name": name,
        "description": description,
        "owner": owner,
        "repo": repo,
        "ref": ref,
        "sha256": sha256,
        "vendorHash": "",
    }

    vendor_hash = compute_vendor_hash(config)
    if not vendor_hash:
        print("  Failed to compute vendorHash. Re-run `just package go` to retry.")
        sys.exit(1)
    print(f"  Vendor hash: {vendor_hash}\n")

    config["vendorHash"] = vendor_hash

    # 5. Show summary and confirm
    print("=== Summary ===")
    print(f"  Package name:  {config['name']}")
    print(f"  Description:   {config['description']}")
    print(f"  Source:        github.com/{config['owner']}/{config['repo']}")
    print(f"  Ref:           {config['ref']}")
    print(f"  Source hash:   {config['sha256']}")
    print(f"  Vendor hash:   {config['vendorHash']}")
    print()

    confirm = input("Apply these changes? [Y/n]: ").strip().lower()
    if confirm in ("n", "no"):
        print("Cancelled. Re-run `just package go` to try again.")
        sys.exit(0)

    # 6. Write final config
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)
        f.write("\n")
    print(f"\n  Wrote {CONFIG_FILE}")

    # 7. Verify build
    print(f"\n  Verifying: nix build .#{name} ...")
    result = subprocess.run(
        ["nix", "build", f".#{name}", "--no-link"],
        timeout=600,
    )
    if result.returncode == 0:
        print(f"\n  Success! Run `nix build .#{name}` anytime to rebuild.")
        print("  To update to a new release, re-run `just package go`.")
    else:
        print("\n  Build failed. Check the output above.")
        print("  The config has been saved — re-run `just package go` to retry.")
        sys.exit(1)


if __name__ == "__main__":
    main()
