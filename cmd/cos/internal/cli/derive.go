package cli

import (
	"fmt"
	"os"
	"os/exec"

	"github.com/spf13/cobra"

	"luum-agent-os/cmd/cos/internal/project"
)

var (
	deriveCheck bool
	deriveSync  bool
)

var deriveCmd = &cobra.Command{
	Use:   "derive",
	Short: "Check or sync generated Cognitive OS artifacts",
	Long: `Check or sync generated Cognitive OS artifacts.

The check mode centralizes scripts/derived_artifact_gate.py. The sync mode runs
the existing synchronizers for known derived artifacts, then runs the same gate
as a final verification step.

Preferred usage:
  cos derive check
  cos derive sync

Compatibility usage:
  cos derive --check
  cos derive --sync`,
	RunE: runDerive,
}

var deriveCheckCmd = &cobra.Command{
	Use:   "check",
	Short: "Run the derived artifact gate",
	Args:  cobra.NoArgs,
	RunE: func(cmd *cobra.Command, args []string) error {
		return runDeriveCheck()
	},
}

var deriveSyncCmd = &cobra.Command{
	Use:   "sync",
	Short: "Synchronize generated artifacts, then run the derived artifact gate",
	Args:  cobra.NoArgs,
	RunE: func(cmd *cobra.Command, args []string) error {
		return runDeriveSync()
	},
}

func init() {
	deriveCmd.Flags().BoolVar(&deriveCheck, "check", false, "Run the derived artifact gate")
	deriveCmd.Flags().BoolVar(&deriveSync, "sync", false, "Synchronize derived artifacts, then run the gate")
	deriveCmd.AddCommand(deriveCheckCmd, deriveSyncCmd)
	rootCmd.AddCommand(deriveCmd)
}

func runDerive(cmd *cobra.Command, args []string) error {
	if len(args) > 0 {
		return fmt.Errorf("unknown derive mode %q; use check or sync", args[0])
	}
	if deriveCheck == deriveSync {
		return fmt.Errorf("choose exactly one of check, sync, --check, or --sync")
	}
	if deriveCheck {
		return runDeriveCheck()
	}
	return runDeriveSync()
}

func runDeriveCheck() error {
	return runProjectCommand("derived artifact gate", "python3", "scripts/derived_artifact_gate.py")
}

func runDeriveSync() error {
	steps := []struct {
		name string
		cmd  string
		args []string
	}{
		{name: "hook quality manifest sync", cmd: "python3", args: []string{"scripts/hook_quality_audit.py", "--sync"}},
		{name: "Claude settings projection sync", cmd: "bash", args: []string{"scripts/_lib/settings-driver-claude-code.sh"}},
		{name: "Codex settings projection sync", cmd: "bash", args: []string{"scripts/_lib/settings-driver-codex.sh"}},
		{name: "derived artifact gate", cmd: "python3", args: []string{"scripts/derived_artifact_gate.py"}},
	}
	for _, step := range steps {
		if err := runProjectCommand(step.name, step.cmd, step.args...); err != nil {
			return err
		}
	}
	return nil
}

func runProjectCommand(stepName string, command string, args ...string) error {
	projectRoot := project.FindRootOrCwd()
	cmd := exec.Command(command, args...)
	cmd.Dir = projectRoot
	cmd.Env = append(os.Environ(),
		fmt.Sprintf("PROJECT_DIR=%s", projectRoot),
		fmt.Sprintf("PYTHONPATH=%s", projectRoot),
	)
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr
	if err := cmd.Run(); err != nil {
		return fmt.Errorf("%s failed: %w", stepName, err)
	}
	return nil
}
