package cli

import (
	"fmt"
	"os"
	"os/exec"
	"path/filepath"

	"github.com/spf13/cobra"

	"luum-agent-os/cmd/cos/internal/project"
)

var provenanceCmd = &cobra.Command{
	Use:   "provenance",
	Short: "Run Cognitive OS provenance guardrails",
}

var provenanceScanCmd = &cobra.Command{
	Use:                "scan [paths...]",
	Short:              "Scan for sensitive provenance and local-source leaks",
	DisableFlagParsing: true,
	Long: `Scan repository files for host-local paths, sensitive source-project terms,
prohibited import roots, non-portable path hacks, and sensitive provenance wording.

Examples:
  cos provenance scan
  cos provenance scan --staged
  cos provenance scan --config .cognitive-os/provenance-scan.yaml src/`,
	RunE: runProvenanceScan,
}

func init() {
	provenanceCmd.AddCommand(provenanceScanCmd)
	rootCmd.AddCommand(provenanceCmd)
}

func runProvenanceScan(cmd *cobra.Command, args []string) error {
	sourceRoot, err := cognitiveOSSourceRoot()
	if err != nil {
		return err
	}
	script := filepath.Join(sourceRoot, "scripts", "provenance_scan.py")
	if _, err := os.Stat(script); err != nil {
		return fmt.Errorf("provenance scanner not found: %w", err)
	}

	root := project.FindRootOrCwd()
	pyArgs := append([]string{script, "--root", root}, args...)
	proc := exec.Command("python3", pyArgs...)
	proc.Dir = root
	proc.Env = os.Environ()
	proc.Stdout = cmd.OutOrStdout()
	proc.Stderr = cmd.ErrOrStderr()
	if err := proc.Run(); err != nil {
		if exitErr, ok := err.(*exec.ExitError); ok {
			return newExitError(exitErr.ExitCode(), fmt.Errorf("provenance scan failed"))
		}
		return err
	}
	return nil
}
