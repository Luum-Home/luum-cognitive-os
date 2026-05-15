package cli

import (
	"fmt"

	"github.com/spf13/cobra"
)

var (
	projectHarness = "claude"
	projectProfile = "default"
)

var projectCmd = &cobra.Command{
	Use:   "project",
	Short: "Plan project-local harness projection",
	Long: `Plan a project-local Cognitive OS harness projection.

The command reports the cos_init.py projection command and proof boundary for
the selected harness/profile. It keeps .cognitive-os as the canonical primitive
source and does not claim runtime enforcement for structural harnesses.

Examples:
  cos project --harness cursor
  cos project --harness claude --profile full
  cos project --harness windsurf`,
	Args: cobra.NoArgs,
	RunE: runProjectProjectionPlan,
}

func init() {
	projectCmd.Flags().StringVar(&projectHarness, "harness", "claude", "Target harness projection")
	projectCmd.Flags().StringVar(&projectProfile, "profile", "default", "Projection profile (default|full)")
	rootCmd.AddCommand(projectCmd)
}

func runProjectProjectionPlan(cmd *cobra.Command, args []string) error {
	if err := validateHarness(projectHarness); err != nil {
		return err
	}
	command, registered := profileProjectionCommand(projectProfile, projectHarness)
	if !registered {
		return fmt.Errorf("unsupported project profile %q: supported profiles are default, full", projectProfile)
	}

	fmt.Fprintf(cmd.OutOrStdout(), "Project projection plan\n")
	fmt.Fprintf(cmd.OutOrStdout(), "profile:         %s\n", projectProfile)
	fmt.Fprintf(cmd.OutOrStdout(), "harness:         %s\n", projectHarness)
	fmt.Fprintf(cmd.OutOrStdout(), "projection_path: %s\n", harnessProjectionPath(projectHarness))
	fmt.Fprintf(cmd.OutOrStdout(), "proof_level:     %s\n", harnessProofSummary(projectHarness))
	fmt.Fprintf(cmd.OutOrStdout(), "command:         %s\n", command)
	return nil
}
