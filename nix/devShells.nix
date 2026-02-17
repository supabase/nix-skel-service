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
