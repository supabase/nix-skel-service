{
  description = "My Go service";

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
        nix/nixpkgs.nix
        nix/devShells.nix
        nix/fmt.nix
        nix/hooks.nix
        nix/packages
      ];
    });
}
