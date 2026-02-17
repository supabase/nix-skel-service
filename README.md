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
