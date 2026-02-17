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
        devshell.startup.welcome.text = ''
          echo ""
          echo "  Tip: You can run commands directly (e.g. 'package go')"
          echo "       or via just (e.g. 'just package go') — both work."
          echo ""
        '';

        commands = [
          {
            name = "package";
            help = "Package a service for Nix (e.g. `package go`)";
            command = "just package $@";
            category = "scaffold";
          }
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
