package cli

import (
	"fmt"

	"github.com/spf13/cobra"

	"luum-agent-os/cmd/cos/internal/ui"
)

var (
	verbose bool
	noColor bool
)

var rootCmd = &cobra.Command{
	Use:   "cos",
	Short: "cos — Cognitive OS Package Manager",
	Long: `cos — Cognitive OS Package Manager

A package manager for AI agent components: skills, rules, hooks, agents, and templates.

Commands:
  init        Create a new cos-package.yaml
  validate    Validate cos-package.yaml in the current directory
  install     Install a cos package from local path, GitHub, or URL`,
	Version: "0.1.0",
}

// Execute runs the root command.
func Execute() error {
	ui.Initialize(noColor, verbose)

	if err := rootCmd.Execute(); err != nil {
		return fmt.Errorf("command execution failed: %w", err)
	}
	return nil
}

func init() {
	rootCmd.PersistentFlags().BoolVar(&verbose, "verbose", false, "Enable verbose output")
	rootCmd.PersistentFlags().BoolVar(&noColor, "no-color", false, "Disable colored output")
}
