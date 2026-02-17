# Nix Skeleton Service Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Create a skeleton Nix flake repo that users clone and run `just package go` to generate a working Nix package for any Go service, with CI workflows matching pg-image-strip's pattern.

**Architecture:** Flake-parts based flake with nixpkgs following supabase/postgres develop. Package config lives in `.package-config.json` which Nix reads directly. A Python script handles interactive setup, hash computation, and config writing.

**Tech Stack:** Nix (flake-parts, buildGoModule, treefmt-nix, git-hooks.nix, devshell, nix-eval-jobs), Python 3, just, GitHub Actions

---

### Task 1: Create flake.nix

**Files:**
- Create: `flake.nix`

**Step 1: Write flake.nix**

```nix
{
  description = (builtins.fromJSON (builtins.readFile ./.package-config.json)).description;

  inputs = {
    supabase-postgres.url = "github:supabase/postgres/develop";
    nixpkgs.follows = "supabase-postgres/nixpkgs";
    flake-parts.url = "github:hercules-ci/flake-parts";
    flake-utils.url = "github:numtide/flake-utils";
    treefmt-nix.url = "github:numtide/treefmt-nix";
    treefmt-nix.inputs.nixpkgs.follows = "nixpkgs";
    git-hooks.url = "github:cachix/git-hooks.nix";
    git-hooks.inputs.nixpkgs.follows = "nixpkgs";
    devshell.url = "github:numtide/devshell";
    devshell.inputs.nixpkgs.follows = "nixpkgs";
    nix-eval-jobs.url = "github:nix-community/nix-eval-jobs";
    nix-eval-jobs.inputs.flake-parts.follows = "flake-parts";
    nix-eval-jobs.inputs.treefmt-nix.follows = "treefmt-nix";
  };

  outputs =
    { flake-utils, ... }@inputs:
    inputs.flake-parts.lib.mkFlake { inherit inputs; } (_: {
      systems = with flake-utils.lib; [
        system.x86_64-linux
        system.aarch64-linux
        system.aarch64-darwin
      ];

      imports = [
        nix/devShells.nix
        nix/fmt.nix
        nix/hooks.nix
        nix/packages
      ];
    });
}
```

**Step 2: Create `.package-config.json` with placeholders**

```json
{
  "name": "my-go-service",
  "description": "My Go service",
  "owner": "your-org",
  "repo": "your-repo",
  "ref": "v0.0.0",
  "sha256": "sha256-AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=",
  "vendorHash": "sha256-AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA="
}
```

---

### Task 2: Create Nix modules (fmt, hooks, devShells)

**Files:**
- Create: `nix/fmt.nix`
- Create: `nix/hooks.nix`
- Create: `nix/devShells.nix`

**Step 1: Create `nix/fmt.nix`**

```nix
{ inputs, ... }:
{
  imports = [ inputs.treefmt-nix.flakeModule ];
  perSystem =
    { pkgs, ... }:
    {
      treefmt = {
        programs = {
          deadnix.enable = true;
          nixfmt = {
            enable = true;
            package = pkgs.nixfmt-rfc-style;
          };
          ruff-format.enable = true;
        };

        settings = {
          global.excludes = [
            "*.sum"
            "vendor/*"
          ];
        };
      };
    };
}
```

**Step 2: Create `nix/hooks.nix`**

```nix
{ inputs, ... }:
let
  ghWorkflows = builtins.attrNames (builtins.readDir ../.github/workflows);
  lintedWorkflows = [
    "nix-eval.yml"
    "nix-build.yml"
  ];
in
{
  imports = [ inputs.git-hooks.flakeModule ];
  perSystem =
    { config, ... }:
    {
      pre-commit = {
        check.enable = true;
        settings = {
          hooks = {
            actionlint = {
              enable = true;
              excludes = builtins.filter (name: !builtins.elem name lintedWorkflows) ghWorkflows;
              verbose = true;
            };

            treefmt = {
              enable = true;
              package = config.treefmt.build.wrapper;
              pass_filenames = false;
              verbose = true;
            };
          };
        };
      };
    };
}
```

**Step 3: Create `nix/devShells.nix`**

```nix
{ ... }:
{
  perSystem =
    { pkgs, config, ... }:
    {
      devShells.default = pkgs.devshell.mkShell {
        packages = with pkgs; [
          just
          config.treefmt.build.wrapper
        ];

        devshell.startup.pre-commit.text = config.pre-commit.installationScript;

        commands = [
          {
            name = "fmt";
            help = "Format code";
            command = "nix fmt";
            category = "check";
          }
          {
            name = "check";
            help = "Run all checks";
            command = "nix flake -L check -v";
            category = "check";
          }
          {
            name = "lint";
            help = "Lint code";
            command = "pre-commit run --all-files";
            category = "check";
          }
        ];
      };
    };
}
```

---

### Task 3: Create Go package definition

**Files:**
- Create: `nix/packages/default.nix`

**Step 1: Create `nix/packages/default.nix`**

```nix
{ ... }:
{
  perSystem =
    { pkgs, lib, ... }:
    let
      config = builtins.fromJSON (builtins.readFile ../../.package-config.json);
    in
    {
      packages.${config.name} = pkgs.buildGoModule {
        pname = config.name;
        version = config.ref;
        src = pkgs.fetchFromGitHub {
          owner = config.owner;
          repo = config.repo;
          rev = config.ref;
          hash = config.sha256;
        };
        vendorHash = config.vendorHash;
        meta = with lib; {
          description = config.description;
        };
      };
    };
}
```

---

### Task 4: Create github-matrix package

**Files:**
- Create: `nix/packages/github-matrix/default.nix`
- Create: `nix/packages/github-matrix/github_matrix.py`

**Step 1: Copy `github_matrix.py` from pg-image-strip**

Copy `/Users/samrose/pg-image-strip/nix/packages/github-matrix/github_matrix.py` to `nix/packages/github-matrix/github_matrix.py` exactly as-is.

**Step 2: Copy `default.nix` from pg-image-strip**

Copy `/Users/samrose/pg-image-strip/nix/packages/github-matrix/default.nix` to `nix/packages/github-matrix/default.nix` exactly as-is.

**Step 3: Update `nix/packages/default.nix` to expose github-matrix**

Update the packages default.nix to also expose the github-matrix package:

```nix
{ inputs, ... }:
{
  perSystem =
    { pkgs, lib, ... }:
    let
      config = builtins.fromJSON (builtins.readFile ../../.package-config.json);
    in
    {
      packages.${config.name} = pkgs.buildGoModule {
        pname = config.name;
        version = config.ref;
        src = pkgs.fetchFromGitHub {
          owner = config.owner;
          repo = config.repo;
          rev = config.ref;
          hash = config.sha256;
        };
        vendorHash = config.vendorHash;
        meta = with lib; {
          description = config.description;
        };
      };

      packages.github-matrix = pkgs.callPackage ./github-matrix {
        nix-eval-jobs = inputs.nix-eval-jobs.outputs.packages.${pkgs.stdenv.hostPlatform.system}.default;
      };

      legacyPackages.${config.name} = pkgs.buildGoModule {
        pname = config.name;
        version = config.ref;
        src = pkgs.fetchFromGitHub {
          owner = config.owner;
          repo = config.repo;
          rev = config.ref;
          hash = config.sha256;
        };
        vendorHash = config.vendorHash;
        meta = with lib; {
          description = config.description;
        };
      };
    };
}
```

Note: `legacyPackages` is needed for the github-matrix eval workflow which evaluates `legacyPackages`.

---

### Task 5: Create GitHub Actions workflows and actions

**Files:**
- Create: `.github/actions/nix-install-ephemeral/action.yml`
- Create: `.github/actions/nix-install-self-hosted/action.yml`
- Create: `.github/workflows/nix-eval.yml`
- Create: `.github/workflows/nix-build.yml`

**Step 1: Copy nix-install-ephemeral action**

Copy `/Users/samrose/pg-image-strip/.github/actions/nix-install-ephemeral/action.yml` exactly as-is.

**Step 2: Copy nix-install-self-hosted action**

Copy `/Users/samrose/pg-image-strip/.github/actions/nix-install-self-hosted/action.yml` exactly as-is.

**Step 3: Copy nix-eval.yml**

Copy `/Users/samrose/pg-image-strip/.github/workflows/nix-eval.yml` exactly as-is.

**Step 4: Create nix-build.yml**

Simplified version of pg-image-strip's — eval + build packages + build checks per system, no downstream jobs:

```yaml
name: Nix CI

on:
  push:
    branches:
      - main
  pull_request:
  merge_group:
  workflow_dispatch:

permissions:
  id-token: write
  contents: write
  packages: write

concurrency:
  group: ${{ github.workflow }}-${{ github.event.pull_request.number || github.ref }}
  cancel-in-progress: ${{ github.event_name == 'pull_request' }}

jobs:
  nix-eval:
    uses: ./.github/workflows/nix-eval.yml
    secrets:
      DEV_AWS_ROLE: ${{ secrets.DEV_AWS_ROLE }}
      NIX_SIGN_SECRET_KEY: ${{ secrets.NIX_SIGN_SECRET_KEY }}

  nix-build-packages-aarch64-linux:
    name: >-
      ${{ matrix.name }} (aarch64-linux)
    needs: nix-eval
    runs-on: ${{ matrix.runs_on.group && matrix.runs_on || matrix.runs_on.labels }}
    if: ${{ fromJSON(needs.nix-eval.outputs.packages_matrix).aarch64_linux != null }}
    strategy:
      fail-fast: false
      max-parallel: 5
      matrix: ${{ fromJSON(needs.nix-eval.outputs.packages_matrix).aarch64_linux }}
    steps:
      - name: Checkout Repo
        if: ${{ matrix.attr != '' }}
        uses: actions/checkout@34e114876b0b11c390a56381ad16ebd13914f8d5 # v4.3.1
      - name: Install nix (ephemeral)
        if: ${{ matrix.attr != '' && matrix.runs_on.group != 'self-hosted-runners-nix' }}
        uses: ./.github/actions/nix-install-ephemeral
        with:
          push-to-cache: 'true'
        env:
          DEV_AWS_ROLE: ${{ secrets.DEV_AWS_ROLE }}
          NIX_SIGN_SECRET_KEY: ${{ secrets.NIX_SIGN_SECRET_KEY }}
      - name: Install nix (self-hosted)
        if: ${{ matrix.attr != '' && matrix.runs_on.group == 'self-hosted-runners-nix' }}
        uses: ./.github/actions/nix-install-self-hosted
      - name: nix build
        if: ${{ matrix.attr != '' }}
        shell: bash
        run: nix build --accept-flake-config -L .#${{ matrix.attr }}

  nix-build-checks-aarch64-linux:
    name: >-
      ${{ matrix.name }} (aarch64-linux)
    needs: [nix-eval, nix-build-packages-aarch64-linux]
    runs-on: ${{ matrix.runs_on.group && matrix.runs_on || matrix.runs_on.labels }}
    if: ${{ fromJSON(needs.nix-eval.outputs.checks_matrix).aarch64_linux != null }}
    strategy:
      fail-fast: false
      max-parallel: 5
      matrix: ${{ fromJSON(needs.nix-eval.outputs.checks_matrix).aarch64_linux }}
    steps:
      - name: Checkout Repo
        if: ${{ matrix.attr != '' }}
        uses: actions/checkout@34e114876b0b11c390a56381ad16ebd13914f8d5 # v4.3.1
      - name: Install nix (ephemeral)
        if: ${{ matrix.attr != '' && matrix.runs_on.group != 'self-hosted-runners-nix' }}
        uses: ./.github/actions/nix-install-ephemeral
        with:
          push-to-cache: 'true'
        env:
          DEV_AWS_ROLE: ${{ secrets.DEV_AWS_ROLE }}
          NIX_SIGN_SECRET_KEY: ${{ secrets.NIX_SIGN_SECRET_KEY }}
      - name: Install nix (self-hosted)
        if: ${{ matrix.attr != '' && matrix.runs_on.group == 'self-hosted-runners-nix' }}
        uses: ./.github/actions/nix-install-self-hosted
      - name: nix build
        if: ${{ matrix.attr != '' }}
        shell: bash
        run: nix build --accept-flake-config -L .#${{ matrix.attr }}

  nix-build-packages-aarch64-darwin:
    name: >-
      ${{ matrix.name }} (aarch64-darwin)
    needs: nix-eval
    runs-on: ${{ matrix.attr != '' && matrix.runs_on.group && matrix.runs_on || matrix.runs_on.labels }}
    if: ${{ fromJSON(needs.nix-eval.outputs.packages_matrix).aarch64_darwin != null }}
    strategy:
      fail-fast: false
      max-parallel: 5
      matrix: ${{ fromJSON(needs.nix-eval.outputs.packages_matrix).aarch64_darwin }}
    steps:
      - name: Checkout Repo
        if: ${{ matrix.attr != '' }}
        uses: actions/checkout@34e114876b0b11c390a56381ad16ebd13914f8d5 # v4.3.1
      - name: Install nix
        if: ${{ matrix.attr != '' }}
        uses: ./.github/actions/nix-install-self-hosted
      - name: nix build
        if: ${{ matrix.attr != '' }}
        shell: bash
        run: nix build --accept-flake-config -L .#${{ matrix.attr }}

  nix-build-checks-aarch64-darwin:
    name: >-
      ${{ matrix.name }} (aarch64-darwin)
    needs: [nix-eval, nix-build-packages-aarch64-darwin]
    runs-on: ${{ matrix.attr != '' && matrix.runs_on.group && matrix.runs_on || matrix.runs_on.labels }}
    if: ${{ fromJSON(needs.nix-eval.outputs.checks_matrix).aarch64_darwin != null }}
    strategy:
      fail-fast: false
      max-parallel: 5
      matrix: ${{ fromJSON(needs.nix-eval.outputs.checks_matrix).aarch64_darwin }}
    steps:
      - name: Checkout Repo
        if: ${{ matrix.attr != '' }}
        uses: actions/checkout@34e114876b0b11c390a56381ad16ebd13914f8d5 # v4.3.1
      - name: Install nix
        if: ${{ matrix.attr != '' }}
        uses: ./.github/actions/nix-install-self-hosted
      - name: nix build
        if: ${{ matrix.attr != '' }}
        shell: bash
        run: nix build --accept-flake-config -L .#${{ matrix.attr }}

  nix-build-packages-x86_64-linux:
    name: >-
      ${{ matrix.name }} (x86_64-linux)
    needs: nix-eval
    runs-on: ${{ matrix.attr != '' && matrix.runs_on.group && matrix.runs_on || matrix.runs_on.labels }}
    if: ${{ fromJSON(needs.nix-eval.outputs.packages_matrix).x86_64_linux != null }}
    strategy:
      fail-fast: false
      max-parallel: 5
      matrix: ${{ fromJSON(needs.nix-eval.outputs.packages_matrix).x86_64_linux }}
    steps:
      - name: Checkout Repo
        if: ${{ matrix.attr != '' }}
        uses: actions/checkout@34e114876b0b11c390a56381ad16ebd13914f8d5 # v4.3.1
      - name: Install nix
        if: ${{ matrix.attr != '' }}
        uses: ./.github/actions/nix-install-ephemeral
        with:
          push-to-cache: 'true'
        env:
          DEV_AWS_ROLE: ${{ secrets.DEV_AWS_ROLE }}
          NIX_SIGN_SECRET_KEY: ${{ secrets.NIX_SIGN_SECRET_KEY }}
      - name: nix build
        if: ${{ matrix.attr != '' }}
        shell: bash
        run: nix build --accept-flake-config -L .#${{ matrix.attr }}

  nix-build-checks-x86_64-linux:
    name: >-
      ${{ matrix.name }} (x86_64-linux)
    needs: [nix-eval, nix-build-packages-x86_64-linux]
    runs-on: ${{ matrix.attr != '' && matrix.runs_on.group && matrix.runs_on || matrix.runs_on.labels }}
    if: ${{ fromJSON(needs.nix-eval.outputs.checks_matrix).x86_64_linux != null }}
    strategy:
      fail-fast: false
      max-parallel: 5
      matrix: ${{ fromJSON(needs.nix-eval.outputs.checks_matrix).x86_64_linux }}
    steps:
      - name: Checkout Repo
        if: ${{ matrix.attr != '' }}
        uses: actions/checkout@34e114876b0b11c390a56381ad16ebd13914f8d5 # v4.3.1
      - name: Install nix
        if: ${{ matrix.attr != '' }}
        uses: ./.github/actions/nix-install-ephemeral
        with:
          push-to-cache: 'true'
        env:
          DEV_AWS_ROLE: ${{ secrets.DEV_AWS_ROLE }}
          NIX_SIGN_SECRET_KEY: ${{ secrets.NIX_SIGN_SECRET_KEY }}
      - name: nix build
        if: ${{ matrix.attr != '' }}
        shell: bash
        run: nix build --accept-flake-config -L .#${{ matrix.attr }}
```

---

### Task 6: Create the `scripts/package-go.py` scaffold script

**Files:**
- Create: `scripts/package-go.py`

**Step 1: Write the script**

```python
#!/usr/bin/env python3
"""Interactive scaffold script for packaging a Go service with Nix."""

import json
import os
import re
import subprocess
import sys
import tempfile
import shutil

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
        print(f"Found existing config for '{existing['name']}'. Values shown as defaults.\n")

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
```

---

### Task 7: Create justfile

**Files:**
- Create: `justfile`

**Step 1: Write justfile**

```just
# Package a service for Nix
package language:
    python3 scripts/package-go.py {{language}}
```

---

### Task 8: Create documentation

**Files:**
- Create: `README.md`
- Create: `docs/GETTING-STARTED.md`

**Step 1: Write README.md**

```markdown
# nix-skel-service

Skeleton Nix flake for packaging Go-based services. Clone this repo, run the
interactive setup, and get a fully working Nix package with CI workflows.

## Quick Start

See [docs/GETTING-STARTED.md](docs/GETTING-STARTED.md) for step-by-step
instructions.

## What You Get

- Nix package using `buildGoModule` with `fetchFromGitHub`
- Development shell with formatting and linting tools
- GitHub Actions CI: nix-eval + nix-build across x86_64-linux, aarch64-linux,
  aarch64-darwin
- Pre-commit hooks: actionlint + treefmt (nixfmt, deadnix, ruff)
- Pinned to the same nixpkgs as supabase/postgres

## Prerequisites

- [Nix](https://nixos.org/download/) (with flakes enabled)
```

**Step 2: Write docs/GETTING-STARTED.md**

```markdown
# Getting Started

Step-by-step guide to packaging a Go service with this skeleton.

## 1. Install Nix

Install Nix using the Determinate Systems installer:

    curl --proto '=https' --tlsv1.2 -sSf -L \
      https://install.determinate.systems/nix | sh -s -- install

This enables flakes and the nix command by default.

## 2. Clone this repository

    git clone <this-repo-url>
    cd nix-skel-service

## 3. Enter the development shell

    nix develop

This drops you into a shell with `just` and formatting tools.

## 4. Run the scaffold

    just package go

You will be prompted for:

- **Package name** — the Nix attribute name (e.g. `auth`)
- **Description** — a short description (e.g. `Supabase Auth server`)
- **GitHub URL** — the repository URL (e.g. `github.com/supabase/auth`)
- **Git tag or commit** — the version to package (e.g. `v2.175.0` or a commit hash)

The script will:

1. Validate the repository and ref exist
2. Compute the source hash (`sha256`)
3. Compute the Go module dependency hash (`vendorHash`)
4. Write `.package-config.json`
5. Verify the build succeeds

## 5. Verify the build

After the scaffold completes, verify manually:

    nix build .#<package-name>

The built binary will be in `./result/bin/`.

## 6. Updating to a new release

Re-run the scaffold at any time:

    just package go

Enter the new git tag or commit. The script will recompute all hashes and
update `.package-config.json`. Previous values are shown as defaults.

## 7. CI setup

The repository includes GitHub Actions workflows for CI:

- **nix-eval.yml** — evaluates the flake and generates a build matrix
- **nix-build.yml** — builds packages and checks across all systems

### Required secrets

If you want to push build artifacts to an S3-based Nix binary cache:

- `DEV_AWS_ROLE` — AWS IAM role ARN for cache access
- `NIX_SIGN_SECRET_KEY` — Nix signing key for the binary cache

These are optional. Without them, builds will still run but won't cache.

### Runner requirements

- **x86_64-linux** — uses ephemeral runners (Blacksmith or GitHub-hosted)
- **aarch64-linux** — uses ephemeral ARM runners or self-hosted
- **aarch64-darwin** — requires self-hosted macOS runners in a
  `self-hosted-runners-nix` runner group

## 8. Troubleshooting

### `just package go` fails at "Validating..."

The GitHub URL or git ref is wrong. Double-check:
- URL format should be `github.com/owner/repo`
- The tag or commit must exist in the repository

### `just package go` fails at "Computing vendorHash..."

The source fetched correctly but the Go build failed. Common causes:
- The project requires CGO (not currently supported in the skeleton)
- Missing system dependencies

Check the build output for details. The config has been partially saved —
re-run `just package go` to retry.

### Build fails after scaffold completes

Run `nix build .#<name> -L` for verbose output. If hashes changed upstream
(force-pushed tag), re-run `just package go` with the same ref.
```

---

### Task 9: Lock the flake and verify `nix develop` works

**Step 1: Generate flake.lock**

Run: `nix flake lock`

This fetches all inputs and generates `flake.lock`.

**Step 2: Verify dev shell**

Run: `nix develop --command echo "devshell works"`

Expected: prints "devshell works" after building the shell.

**Step 3: Verify formatting**

Run: `nix fmt`

Expected: formats all Nix and Python files.
