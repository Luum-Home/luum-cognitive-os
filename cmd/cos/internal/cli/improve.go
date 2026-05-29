package cli

import (
	"github.com/spf13/cobra"
)

var improveCmd = &cobra.Command{
	Use:   "improve",
	Short: "Run benchmark-bound Cognitive OS self-improvement primitives",
	Long: `Run SIA-inspired, COS-governed self-improvement primitives.

The improve surface is benchmark-bound and propose-only. It writes run artifacts
under .cognitive-os/improvement-runs and never applies runtime changes without a
separate approval gate.`,
}

var improveRunCmd = &cobra.Command{
	Use:                "run",
	Short:              "Run a benchmark-bound generational loop",
	DisableFlagParsing: true,
	RunE: func(cmd *cobra.Command, args []string) error {
		return runProjectPythonScript("scripts/cos_improve.py", append([]string{"run"}, args...)...)
	},
}

var improveFeedbackCmd = &cobra.Command{
	Use:                "feedback",
	Short:              "Produce gated feedback proposals from run artifacts",
	DisableFlagParsing: true,
	RunE: func(cmd *cobra.Command, args []string) error {
		return runProjectPythonScript("scripts/cos_improve.py", append([]string{"feedback"}, args...)...)
	},
}

var improveContextCmd = &cobra.Command{
	Use:                "context",
	Short:              "Render context.md for an improvement run",
	DisableFlagParsing: true,
	RunE: func(cmd *cobra.Command, args []string) error {
		return runProjectPythonScript("scripts/cos_improve.py", append([]string{"context"}, args...)...)
	},
}

func init() {
	improveCmd.AddCommand(improveRunCmd, improveFeedbackCmd, improveContextCmd)
	rootCmd.AddCommand(improveCmd)
}
