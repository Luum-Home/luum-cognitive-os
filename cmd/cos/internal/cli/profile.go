package cli

import "github.com/spf13/cobra"

var (
	profileApprovedBy  string
	profileAutoPromote bool
	profileForce       bool
)

var profileCmd = &cobra.Command{
	Use:   "profile",
	Short: "Manage Cognitive OS project profile bootstrap",
	Long: `Manage Cognitive OS project profile bootstrap.

The profile commands expose the local, source-linked Memory/Profile Bootstrap
lifecycle. They delegate to the canonical Python implementation so SessionStart,
manual scripts, and the Go CLI share one behavior contract.`,
}

var profileGenerateCmd = &cobra.Command{
	Use:   "generate",
	Short: "Generate a local project profile draft",
	Args:  cobra.NoArgs,
	RunE: func(cmd *cobra.Command, args []string) error {
		cmdArgs := []string{"generate"}
		if profileForce {
			cmdArgs = append(cmdArgs, "--force")
		}
		return runProjectProfileCommand(cmdArgs...)
	},
}

var profileInspectCmd = &cobra.Command{
	Use:   "inspect",
	Short: "Inspect the computed project profile draft",
	Args:  cobra.NoArgs,
	RunE: func(cmd *cobra.Command, args []string) error {
		return runProjectProfileCommand("inspect")
	},
}

var profilePromoteCmd = &cobra.Command{
	Use:   "promote",
	Short: "Promote an approved project profile draft",
	Args:  cobra.NoArgs,
	RunE: func(cmd *cobra.Command, args []string) error {
		cmdArgs := []string{"promote"}
		if profileApprovedBy != "" {
			cmdArgs = append(cmdArgs, "--approved-by", profileApprovedBy)
		}
		if profileAutoPromote {
			cmdArgs = append(cmdArgs, "--auto-promote")
		}
		return runProjectProfileCommand(cmdArgs...)
	},
}

var profileWipeCmd = &cobra.Command{
	Use:   "wipe",
	Short: "Remove local project profile draft and active profile artifacts",
	Args:  cobra.NoArgs,
	RunE: func(cmd *cobra.Command, args []string) error {
		return runProjectProfileCommand("wipe")
	},
}

func init() {
	profileGenerateCmd.Flags().BoolVar(&profileForce, "force", false, "Regenerate even after the bootstrap window")
	profilePromoteCmd.Flags().StringVar(&profileApprovedBy, "approved-by", "", "Reviewer or system approving profile promotion")
	profilePromoteCmd.Flags().BoolVar(&profileAutoPromote, "auto-promote", false, "Promote without reviewer approval only when explicitly opted in")

	profileCmd.AddCommand(profileGenerateCmd)
	profileCmd.AddCommand(profileInspectCmd)
	profileCmd.AddCommand(profilePromoteCmd)
	profileCmd.AddCommand(profileWipeCmd)
	rootCmd.AddCommand(profileCmd)
}

func runProjectProfileCommand(args ...string) error {
	return runProjectPythonScript("scripts/cos_profile_bootstrap.py", args...)
}
