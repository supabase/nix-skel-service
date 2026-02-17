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
