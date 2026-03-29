package cli

import (
	"fmt"
	"os"
	"path/filepath"
	"strings"

	"github.com/spf13/cobra"

	"luum-agent-os/cmd/cos-test/internal/ui"
)

func resolveVersion() string {
	if Version != "" {
		return Version
	}
	// Try reading VERSION file from project root
	cwd, _ := os.Getwd()
	for dir := cwd; dir != "/" && dir != "."; dir = filepath.Dir(dir) {
		data, err := os.ReadFile(filepath.Join(dir, "VERSION"))
		if err == nil {
			return strings.TrimSpace(string(data))
		}
	}
	return "dev"
}

var (
	ciMode  bool
	verbose bool
	noColor bool
)

var rootCmd = &cobra.Command{
	Use:   "cos-test",
	Short: "Cognitive OS Test Runner",
	Long: `Cognitive OS Test Runner

A TUI-based test runner for the Cognitive OS project.
Wraps pytest with live progress, coverage analysis, and an interactive dashboard.

Commands:
  run         Run tests with live TUI progress
  coverage    Show test coverage across all dimensions
  dashboard   Interactive test dashboard
  watch       Watch for file changes and rerun tests`,
}

// Version can be set via ldflags at build time.
var Version string

// Execute runs the root command.
func Execute() error {
	if rootCmd.Version == "" {
		rootCmd.Version = resolveVersion()
	}
	ui.Initialize(noColor, verbose, ciMode)

	if err := rootCmd.Execute(); err != nil {
		return fmt.Errorf("command execution failed: %w", err)
	}
	return nil
}

func init() {
	rootCmd.PersistentFlags().BoolVar(&ciMode, "ci", false, "Run in CI mode (plain text, no TUI)")
	rootCmd.PersistentFlags().BoolVar(&verbose, "verbose", false, "Enable verbose output")
	rootCmd.PersistentFlags().BoolVar(&noColor, "no-color", false, "Disable colored output")

	// Auto-detect CI.
	if os.Getenv("CI") == "true" || os.Getenv("GITHUB_ACTIONS") == "true" {
		ciMode = true
	}
}
