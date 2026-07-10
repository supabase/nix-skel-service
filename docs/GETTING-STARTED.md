# Getting Started

Step-by-step guide to packaging a Go service with this skeleton.

## 1. Install Nix

Follow the [installation instructions](https://github.com/supabase/postgres/blob/develop/nix/docs/start-here.md).

Log out and back in, then verify:

    nix --version

## 2. Clone this repository

    git clone <this-repo-url> nix-<myname>-service
    cd nix-<myname>-service

## 3. Enter the development shell

    nix develop

This drops you into a shell with `just` and formatting tools.

## 4. Run the scaffold (for instance if packaging Go)

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

- **x86_64-linux** — Blacksmith ephemeral runners with sticky disk cache
- **aarch64-linux** — Blacksmith ephemeral ARM runners with sticky disk cache
- **aarch64-darwin** — GitHub-hosted macOS runners

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
