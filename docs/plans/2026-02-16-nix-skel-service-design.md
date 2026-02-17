# Nix Skeleton Service — Design Document

## Purpose

A skeleton Nix flake repository that users clone to create a Nix packaging repo for Go-based services. Users run `just package go` inside a `nix develop` shell to interactively configure the package. The result is a fully working flake with CI workflows, formatting, and pre-commit hooks.

## Repository Structure

```
nix-skel-service/
├── flake.nix                           # flake-parts, nixpkgs follows supabase/postgres
├── justfile                            # `just package go` entry point
├── .package-config.json                # placeholder config, overwritten by just
├── scripts/
│   └── package-go.py                   # robust scaffold script
├── nix/
│   ├── packages/
│   │   ├── default.nix                 # reads .package-config.json, buildGoModule
│   │   └── github-matrix/
│   │       ├── default.nix             # nix wrapper (from pg-image-strip)
│   │       └── github_matrix.py        # matrix generator (from pg-image-strip)
│   ├── devShells.nix                   # just + treefmt
│   ├── fmt.nix                         # deadnix, nixfmt-rfc-style, ruff-format
│   └── hooks.nix                       # pre-commit: actionlint + treefmt
├── .github/
│   ├── workflows/
│   │   ├── nix-eval.yml                # reusable eval workflow (from pg-image-strip)
│   │   └── nix-build.yml              # eval -> build packages -> build checks
│   └── actions/
│       ├── nix-install-ephemeral/
│       │   └── action.yml
│       └── nix-install-self-hosted/
│           └── action.yml
├── docs/
│   └── GETTING-STARTED.md
└── README.md
```

## Key Design Decisions

### Nixpkgs Version Sync

```nix
supabase-postgres.url = "github:supabase/postgres/develop";
nixpkgs.follows = "supabase-postgres/nixpkgs";
```

Uses `follows` to always stay in sync with supabase/postgres nixpkgs. No eval or build of supabase/postgres occurs — Nix only reads its lock file to resolve the nixpkgs revision.

### Package Configuration via JSON

`.package-config.json` is the single source of truth. Ships with placeholders:

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

The Nix package reads directly from this file:

```nix
let
  config = builtins.fromJSON (builtins.readFile ../../.package-config.json);
in
pkgs.buildGoModule {
  pname = config.name;
  version = config.ref;
  src = pkgs.fetchFromGitHub {
    owner = config.owner;
    repo = config.repo;
    rev = config.ref;
    hash = config.sha256;
  };
  vendorHash = config.vendorHash;
  meta.description = config.description;
}
```

No sed on Nix files — ever. The fixed filename `.package-config.json` avoids circular dependency between filename and package name.

### `just package go` Flow

Calls `scripts/package-go.py` (Python supplied by Nix via `nix develop`).

The script:

1. Prompts for: package name, description, GitHub URL (e.g. `github.com/supabase/auth`), git tag or commit
2. Validates inputs — checks URL format, verifies repo exists and ref resolves via HTTP HEAD on the tarball URL
3. Prefetches source — `nix-prefetch-url --unpack` + `nix hash convert` for SRI format sha256
4. Applies to temp config — writes computed values to a temp file
5. Computes vendorHash — runs `nix build` with the sha256 filled in but vendorHash as fakeHash, parses the expected hash from the error output, distinguishes hash mismatch from other failures
6. Shows summary and confirms — prints all values, asks user to confirm
7. Atomic apply — writes final `.package-config.json` only after confirmation
8. Verifies — runs `nix build` to confirm success

Idempotent: re-run anytime to update for a new release. Previous values shown as defaults.

Error handling:
- Invalid URL -> clear error before any files touched
- Nonexistent ref -> clear error from prefetch, no files touched
- vendorHash build fails for non-hash reasons -> show actual error, no files touched
- User cancels -> no files touched

### Flake Structure

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

  outputs = { flake-utils, ... }@inputs:
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

### Dev Shell

```nix
{ ... }:
{
  perSystem = { pkgs, config, ... }: {
    devShells.default = pkgs.devshell.mkShell {
      packages = with pkgs; [
        just
        config.treefmt.build.wrapper
      ];
      devshell.startup.pre-commit.text = config.pre-commit.installationScript;
      commands = [
        { name = "fmt"; help = "Format code"; command = "nix fmt"; category = "check"; }
        { name = "check"; help = "Run all checks"; command = "nix flake -L check -v"; category = "check"; }
        { name = "lint"; help = "Lint code"; command = "pre-commit run --all-files"; category = "check"; }
      ];
    };
  };
}
```

### Formatting (treefmt)

- `deadnix` — detect dead Nix code
- `nixfmt-rfc-style` — Nix formatting
- `ruff-format` — Python formatting (for github-matrix script)

### Pre-commit Hooks

- `actionlint` — lint GitHub Actions workflows
- `treefmt` — format all code

### CI Workflows

Copied from pg-image-strip, simplified (no downstream jobs):

**nix-eval.yml** — reusable workflow. Runs `nix run .#github-matrix -- checks legacyPackages` to generate dynamic build matrix.

**nix-build.yml** — triggers on push (main), PR, merge_group, workflow_dispatch:
1. `nix-eval` (reusable)
2. `nix-build-packages-{aarch64-linux, aarch64-darwin, x86_64-linux}`
3. `nix-build-checks-{aarch64-linux, aarch64-darwin, x86_64-linux}`

No testinfra, docker-image-test, or test.yml downstream jobs.

**GitHub Actions** (from pg-image-strip):
- `nix-install-ephemeral` — installs Nix on ephemeral runners with optional S3 cache push
- `nix-install-self-hosted` — configures Nix on self-hosted runners

**github-matrix** package — Python script + Nix wrapper from pg-image-strip for dynamic CI matrix generation.

### Documentation

**README.md** — overview, prerequisites, points to GETTING-STARTED.md

**docs/GETTING-STARTED.md** — step-by-step:
1. Install Nix
2. Clone this repo
3. `nix develop`
4. `just package go`
5. Follow prompts (with examples for each)
6. `nix build .#<name>` to verify
7. Updating to a new release (re-run `just package go`)
8. CI setup (secrets, runner requirements)
9. Troubleshooting
