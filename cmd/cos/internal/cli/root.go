package cli

import (
	"fmt"

	"github.com/spf13/cobra"

	"luum-agent-os/cmd/cos/internal/project"
	"luum-agent-os/cmd/cos/internal/ui"
)

var (
	verbose bool
	noColor bool
)

// Version can be set at build time via ldflags:
//
//	go build -ldflags "-X luum-agent-os/cmd/cos/internal/cli.Version=1.2.3"
//
// If not set (empty), the version is read from the VERSION file at runtime.
var Version string

var rootCmd = &cobra.Command{
	Use:   "cos",
	Short: "cos — Cognitive OS Package Manager",
	Long: `cos — Cognitive OS Package Manager

A package manager for AI agent components: skills, rules, hooks, agents, and templates.

Commands:
  new         Create a new project with COS pre-configured
  init        Create a new cos-package.yaml
  validate    Validate cos-package.yaml in the current directory
  add         Search and install skills in one step (search + install)
  install     Install a cos package from local path, GitHub, or URL
  remove      Remove an installed package
  list        List installed packages
  info        Show detailed information about a package
  search      Search for cos packages across configured registries
  registry    Manage package registries (list, add, enable, disable)
  publish     Validate and prepare package for publishing
  audit       Run security audit on a package
  update      Update installed packages
  map         Show system knowledge graph
  perf        Show performance dashboard
  version     Show OS and package versions
  release     Create a new release
  status      Show release status of all packages
  release-all Release all packages with unreleased changes`,
}

// resolveVersion returns the CLI version from ldflags or the VERSION file.
func resolveVersion() string {
	if Version != "" {
		return Version
	}
	return readVersionFile(project.FindRootOrCwd())
}

// Execute runs the root command.
func Execute() error {
	ui.Initialize(noColor, verbose)

	// Set version dynamically so `cos --version` works correctly.
	rootCmd.Version = resolveVersion()

	if err := rootCmd.Execute(); err != nil {
		return fmt.Errorf("command execution failed: %w", err)
	}
	return nil
}

func init() {
	rootCmd.PersistentFlags().BoolVar(&verbose, "verbose", false, "Enable verbose output")
	rootCmd.PersistentFlags().BoolVar(&noColor, "no-color", false, "Disable colored output")
}
