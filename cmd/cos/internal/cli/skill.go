package cli

import (
	"github.com/spf13/cobra"
)

var (
	skillApprovedBy  string
	skillAutoPromote bool
)

var skillCmd = &cobra.Command{
	Use:   "skill",
	Short: "Govern Cognitive OS skills",
	Long: `Govern Cognitive OS skills.

The suggest/draft/promote subcommands implement the governed self-improvement
loop. They delegate to the canonical Python implementation so the Go CLI and
hook/runtime paths share one behavior contract.`,
}

var skillSuggestCmd = &cobra.Command{
	Use:   "suggest",
	Short: "Suggest evidence-backed skill improvements",
	Args:  cobra.NoArgs,
	RunE: func(cmd *cobra.Command, args []string) error {
		return runGovernedSkillCommand("suggest")
	},
}

var skillDraftCmd = &cobra.Command{
	Use:   "draft <signal-slug>",
	Short: "Create a governed skill draft from a signal",
	Args:  cobra.ExactArgs(1),
	RunE: func(cmd *cobra.Command, args []string) error {
		return runGovernedSkillCommand("draft", args[0])
	},
}

var skillInspectCmd = &cobra.Command{
	Use:   "inspect <draft-id>",
	Short: "Inspect a governed skill draft",
	Args:  cobra.ExactArgs(1),
	RunE: func(cmd *cobra.Command, args []string) error {
		return runGovernedSkillCommand("inspect", args[0])
	},
}

var skillPromoteCmd = &cobra.Command{
	Use:   "promote <draft-id>",
	Short: "Promote an approved governed skill draft",
	Args:  cobra.ExactArgs(1),
	RunE: func(cmd *cobra.Command, args []string) error {
		cmdArgs := []string{"promote", args[0]}
		if skillApprovedBy != "" {
			cmdArgs = append(cmdArgs, "--approved-by", skillApprovedBy)
		}
		if skillAutoPromote {
			cmdArgs = append(cmdArgs, "--auto-promote")
		}
		return runGovernedSkillCommand(cmdArgs...)
	},
}

func init() {
	skillPromoteCmd.Flags().StringVar(&skillApprovedBy, "approved-by", "", "Reviewer or system approving promotion")
	skillPromoteCmd.Flags().BoolVar(&skillAutoPromote, "auto-promote", false, "Promote without reviewer approval when the project explicitly opts in")

	skillCmd.AddCommand(skillSuggestCmd)
	skillCmd.AddCommand(skillDraftCmd)
	skillCmd.AddCommand(skillInspectCmd)
	skillCmd.AddCommand(skillPromoteCmd)
	rootCmd.AddCommand(skillCmd)
}

func runGovernedSkillCommand(args ...string) error {
	return runProjectPythonScript("scripts/cos-governed-self-improvement.py", args...)
}
