package cli

import (
	"fmt"
	"os"
	"path/filepath"
	"strings"

	"github.com/spf13/cobra"

	"luum-agent-os/cmd/cos/internal/project"
)

var (
	installPrimitiveHarness      = "claude"
	installProfileHarness        = "claude"
	installPrimitiveDryRun       bool
	installProfileDryRun         bool
	installPrimitiveRuntimeSmoke bool
	installProfileRuntimeSmoke   bool
)

var installPrimitiveCmd = &cobra.Command{
	Use:   "primitive <family/name>",
	Short: "Install a harness-aware primitive projection from the canonical COS catalog",
	Long: `Install or dry-run one canonical Cognitive OS primitive projection.

This command is intentionally source-of-truth-first: it reads the current
project/repo catalog surfaces and reports the harness projection boundary while keeping .cognitive-os as the canonical installed surface.

Examples:
  cos install primitive skill/cos-status --harness cursor
  cos install primitive hook/session-init --harness codex
  cos install primitive rule/trust-score --harness claude`,
	Args: cobra.ExactArgs(1),
	RunE: runInstallPrimitive,
}

var installProfileCmd = &cobra.Command{
	Use:   "profile <name>",
	Short: "Install a harness-aware profile projection",
	Long: `Install or dry-run a Cognitive OS profile projection.

Profiles are projected through scripts/cos_init.py and retain .cognitive-os as
the canonical primitive source. The currently implemented first-run profiles are
default and full.

Examples:
  cos install profile default --harness cursor
  cos install profile full --harness claude
  cos install profile sre --harness claude`,
	Args: cobra.ExactArgs(1),
	RunE: runInstallProfile,
}

func init() {
	installPrimitiveCmd.Flags().StringVar(&installPrimitiveHarness, "harness", "claude", "Target harness projection")
	installPrimitiveCmd.Flags().BoolVar(&installPrimitiveDryRun, "dry-run", false, "Show projection plan without writing files")
	installPrimitiveCmd.Flags().BoolVar(&installPrimitiveRuntimeSmoke, "runtime-smoke", false, "Run optional harness binary smoke when the binary is installed")
	installProfileCmd.Flags().StringVar(&installProfileHarness, "harness", "claude", "Target harness projection")
	installProfileCmd.Flags().BoolVar(&installProfileDryRun, "dry-run", false, "Show projection plan without writing files")
	installProfileCmd.Flags().BoolVar(&installProfileRuntimeSmoke, "runtime-smoke", false, "Run optional harness binary smoke when the binary is installed")
	installCmd.AddCommand(installPrimitiveCmd)
	installCmd.AddCommand(installProfileCmd)
}

func runInstallPrimitive(cmd *cobra.Command, args []string) error {
	spec := args[0]
	if err := validateHarness(installPrimitiveHarness); err != nil {
		return err
	}
	root := project.FindRootOrCwd()
	family, name, canonical, err := resolvePrimitiveSpec(root, spec)
	if err != nil {
		return err
	}

	if installPrimitiveDryRun {
		fmt.Fprintf(cmd.OutOrStdout(), "Primitive projection plan\n")
		fmt.Fprintf(cmd.OutOrStdout(), "primitive:        %s/%s\n", family, name)
		fmt.Fprintf(cmd.OutOrStdout(), "canonical_source: %s\n", canonical)
		fmt.Fprintf(cmd.OutOrStdout(), "harness:          %s\n", installPrimitiveHarness)
		fmt.Fprintf(cmd.OutOrStdout(), "projection_path:  %s\n", harnessProjectionPath(installPrimitiveHarness))
		fmt.Fprintf(cmd.OutOrStdout(), "proof_level:      %s\n", harnessProofSummary(installPrimitiveHarness))
		fmt.Fprintf(cmd.OutOrStdout(), "apply:            rerun without --dry-run to install the primitive and write a receipt\n")
		return nil
	}

	receipt, err := applyPrimitiveProjection(root, spec, family, name, canonical, installPrimitiveHarness, installPrimitiveRuntimeSmoke)
	if err != nil {
		return err
	}
	fmt.Fprintf(cmd.OutOrStdout(), "Primitive projection applied\n")
	fmt.Fprintf(cmd.OutOrStdout(), "primitive:        %s/%s\n", family, name)
	fmt.Fprintf(cmd.OutOrStdout(), "target:           %s\n", receipt.Target)
	fmt.Fprintf(cmd.OutOrStdout(), "harness:          %s\n", installPrimitiveHarness)
	fmt.Fprintf(cmd.OutOrStdout(), "projection_path:  %s\n", receipt.ProjectionPath)
	fmt.Fprintf(cmd.OutOrStdout(), "proof_level:      %s\n", receipt.ProofLevel)
	fmt.Fprintf(cmd.OutOrStdout(), "backups:          %d\n", len(receipt.Backups))
	fmt.Fprintf(cmd.OutOrStdout(), "runtime_smoke:    %s\n", receipt.RuntimeSmoke["status"])
	return nil
}

func runInstallProfile(cmd *cobra.Command, args []string) error {
	profile := args[0]
	if err := validateHarness(installProfileHarness); err != nil {
		return err
	}

	command, registered := profileProjectionCommand(profile, installProfileHarness)
	if installProfileDryRun || !registered {
		fmt.Fprintf(cmd.OutOrStdout(), "Profile projection plan\n")
		fmt.Fprintf(cmd.OutOrStdout(), "profile:         %s\n", profile)
		fmt.Fprintf(cmd.OutOrStdout(), "registered:      %t\n", registered)
		fmt.Fprintf(cmd.OutOrStdout(), "harness:         %s\n", installProfileHarness)
		fmt.Fprintf(cmd.OutOrStdout(), "projection_path: %s\n", harnessProjectionPath(installProfileHarness))
		fmt.Fprintf(cmd.OutOrStdout(), "proof_level:     %s\n", harnessProofSummary(installProfileHarness))
		if registered {
			fmt.Fprintf(cmd.OutOrStdout(), "command:         %s\n", command)
			fmt.Fprintf(cmd.OutOrStdout(), "apply:           rerun without --dry-run to project this profile and write a receipt\n")
		} else {
			fmt.Fprintf(cmd.OutOrStdout(), "command:         no registered profile command yet; add it to manifests/primitive-projection-profiles.yaml before applying\n")
		}
		return nil
	}

	root := project.FindRootOrCwd()
	receipt, output, err := applyProfileProjection(root, installProfileHarness, profile, installProfileRuntimeSmoke)
	if err != nil {
		return err
	}
	fmt.Fprintf(cmd.OutOrStdout(), "Profile projection applied\n")
	fmt.Fprintf(cmd.OutOrStdout(), "profile:         %s\n", profile)
	fmt.Fprintf(cmd.OutOrStdout(), "harness:         %s\n", installProfileHarness)
	fmt.Fprintf(cmd.OutOrStdout(), "projection_path: %s\n", receipt.ProjectionPath)
	fmt.Fprintf(cmd.OutOrStdout(), "proof_level:     %s\n", receipt.ProofLevel)
	fmt.Fprintf(cmd.OutOrStdout(), "backups:         %d\n", len(receipt.Backups))
	fmt.Fprintf(cmd.OutOrStdout(), "runtime_smoke:   %s\n", receipt.RuntimeSmoke["status"])
	if strings.TrimSpace(output) != "" {
		fmt.Fprintf(cmd.OutOrStdout(), "cos_init_output:\n%s", output)
	}
	return nil
}

func profileProjectionCommand(profile string, harness string) (string, bool) {
	switch profile {
	case "default":
		return fmt.Sprintf("python3 scripts/cos_init.py --default --harness %s", harness), true
	case "full":
		return fmt.Sprintf("python3 scripts/cos_init.py --full --harness %s", harness), true
	default:
		return "", false
	}
}

func resolvePrimitiveSpec(root string, spec string) (string, string, string, error) {
	parts := strings.Split(spec, "/")
	if len(parts) != 2 {
		return "", "", "", fmt.Errorf("primitive must be family/name, for example skill/cos-status")
	}
	family, name := parts[0], parts[1]
	if name == "" {
		return "", "", "", fmt.Errorf("primitive name must not be empty")
	}
	candidates, normalizedFamily, err := primitiveCandidates(root, family, name)
	if err != nil {
		return "", "", "", err
	}
	for _, candidate := range candidates {
		if _, err := os.Stat(candidate); err == nil {
			rel, relErr := filepath.Rel(root, candidate)
			if relErr == nil {
				return normalizedFamily, name, rel, nil
			}
			return normalizedFamily, name, candidate, nil
		}
	}
	return "", "", "", fmt.Errorf("primitive %q not found in canonical repo or installed project surfaces", spec)
}

func primitiveCandidates(root string, family string, name string) ([]string, string, error) {
	switch family {
	case "skill", "skills":
		return []string{
			filepath.Join(root, "skills", name, "SKILL.md"),
			filepath.Join(root, ".cognitive-os", "skills", "cos", name, "SKILL.md"),
		}, "skill", nil
	case "hook", "hooks":
		return []string{
			filepath.Join(root, "hooks", name+".sh"),
			filepath.Join(root, ".cognitive-os", "hooks", "cos", name+".sh"),
		}, "hook", nil
	case "rule", "rules":
		return []string{
			filepath.Join(root, "rules", name+".md"),
			filepath.Join(root, ".cognitive-os", "rules", "cos", name+".md"),
		}, "rule", nil
	default:
		return nil, "", fmt.Errorf("unsupported primitive family %q: use skill, hook, or rule", family)
	}
}
