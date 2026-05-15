package cli

import (
	"fmt"
	"strings"

	"github.com/spf13/cobra"

	"luum-agent-os/cmd/cos/internal/project"
)

var (
	projectHarness      = "claude"
	projectProfile      = "default"
	projectDryRun       bool
	projectRuntimeSmoke bool
)

var projectCmd = &cobra.Command{
	Use:   "project",
	Short: "Apply project-local harness projection",
	Long: `Apply or dry-run a project-local Cognitive OS harness projection.

The command runs the cos_init.py projection command and records a receipt for
the selected harness/profile. It keeps .cognitive-os as the canonical primitive
source and does not claim runtime enforcement for structural harnesses.

Examples:
  cos project --harness cursor
  cos project --harness claude --profile full
  cos project --harness windsurf`,
	Args: cobra.NoArgs,
	RunE: runProjectProjection,
}

func init() {
	projectCmd.Flags().StringVar(&projectHarness, "harness", "claude", "Target harness projection")
	projectCmd.Flags().StringVar(&projectProfile, "profile", "default", "Projection profile (default|full)")
	projectCmd.Flags().BoolVar(&projectDryRun, "dry-run", false, "Show projection plan without writing files")
	projectCmd.Flags().BoolVar(&projectRuntimeSmoke, "runtime-smoke", false, "Run optional harness binary smoke when the binary is installed")
	rootCmd.AddCommand(projectCmd)
}

func runProjectProjection(cmd *cobra.Command, args []string) error {
	if err := validateHarness(projectHarness); err != nil {
		return err
	}
	command, registered := profileProjectionCommand(projectProfile, projectHarness)
	if !registered {
		return fmt.Errorf("unsupported project profile %q: supported profiles are default, full", projectProfile)
	}

	if projectDryRun {
		fmt.Fprintf(cmd.OutOrStdout(), "Project projection plan\n")
		fmt.Fprintf(cmd.OutOrStdout(), "profile:         %s\n", projectProfile)
		fmt.Fprintf(cmd.OutOrStdout(), "harness:         %s\n", projectHarness)
		fmt.Fprintf(cmd.OutOrStdout(), "projection_path: %s\n", harnessProjectionPath(projectHarness))
		fmt.Fprintf(cmd.OutOrStdout(), "proof_level:     %s\n", harnessProofSummary(projectHarness))
		fmt.Fprintf(cmd.OutOrStdout(), "command:         %s\n", command)
		fmt.Fprintf(cmd.OutOrStdout(), "apply:           rerun without --dry-run to project this harness/profile and write a receipt\n")
		return nil
	}

	root := project.FindRootOrCwd()
	receipt, output, err := applyProfileProjection(root, projectHarness, projectProfile, projectRuntimeSmoke)
	if err != nil {
		return err
	}
	fmt.Fprintf(cmd.OutOrStdout(), "Project projection applied\n")
	fmt.Fprintf(cmd.OutOrStdout(), "profile:         %s\n", projectProfile)
	fmt.Fprintf(cmd.OutOrStdout(), "harness:         %s\n", projectHarness)
	fmt.Fprintf(cmd.OutOrStdout(), "projection_path: %s\n", receipt.ProjectionPath)
	fmt.Fprintf(cmd.OutOrStdout(), "proof_level:     %s\n", receipt.ProofLevel)
	fmt.Fprintf(cmd.OutOrStdout(), "backups:         %d\n", len(receipt.Backups))
	fmt.Fprintf(cmd.OutOrStdout(), "runtime_smoke:   %s\n", receipt.RuntimeSmoke["status"])
	if strings.TrimSpace(output) != "" {
		fmt.Fprintf(cmd.OutOrStdout(), "cos_init_output:\n%s", output)
	}
	return nil
}
