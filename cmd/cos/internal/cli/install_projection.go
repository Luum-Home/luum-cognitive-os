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
	installPrimitiveHarness = "claude"
	installProfileHarness   = "claude"
)

var installPrimitiveCmd = &cobra.Command{
	Use:   "primitive <family/name>",
	Short: "Plan a harness-aware primitive projection from the canonical COS catalog",
	Long: `Plan installation/projection for one canonical Cognitive OS primitive.

This command is intentionally source-of-truth-first: it reads the current
project/repo catalog surfaces and reports the harness projection boundary instead
of copying marketplace content into .claude/*.

Examples:
  cos install primitive skill/cos-status --harness cursor
  cos install primitive hook/session-init --harness codex
  cos install primitive rule/trust-score --harness claude`,
	Args: cobra.ExactArgs(1),
	RunE: runInstallPrimitive,
}

var installProfileCmd = &cobra.Command{
	Use:   "profile <name>",
	Short: "Plan a harness-aware profile projection",
	Long: `Plan installation/projection for a Cognitive OS profile.

Profiles are projected through scripts/cos_init.py and retain .cognitive-os as
the canonical primitive source. The currently implemented first-run profiles are
default and full.

Examples:
  cos install profile default --harness cursor
  cos install profile full --harness claude
  cos install profile sre --harness claude`,
	Args: cobra.ExactArgs(1),
	RunE: runInstallProfilePlan,
}

func init() {
	installPrimitiveCmd.Flags().StringVar(&installPrimitiveHarness, "harness", "claude", "Target harness projection")
	installProfileCmd.Flags().StringVar(&installProfileHarness, "harness", "claude", "Target harness projection")
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

	fmt.Fprintf(cmd.OutOrStdout(), "Primitive projection plan\n")
	fmt.Fprintf(cmd.OutOrStdout(), "primitive:        %s/%s\n", family, name)
	fmt.Fprintf(cmd.OutOrStdout(), "canonical_source: %s\n", canonical)
	fmt.Fprintf(cmd.OutOrStdout(), "harness:          %s\n", installPrimitiveHarness)
	fmt.Fprintf(cmd.OutOrStdout(), "projection_path:  %s\n", harnessProjectionPath(installPrimitiveHarness))
	fmt.Fprintf(cmd.OutOrStdout(), "proof_level:      %s\n", harnessProofSummary(installPrimitiveHarness))
	fmt.Fprintf(cmd.OutOrStdout(), "apply:            use `cos project --harness %s` to re-project the selected profile after catalog/profile changes\n", installPrimitiveHarness)
	return nil
}

func runInstallProfilePlan(cmd *cobra.Command, args []string) error {
	profile := args[0]
	if err := validateHarness(installProfileHarness); err != nil {
		return err
	}

	command, registered := profileProjectionCommand(profile, installProfileHarness)
	fmt.Fprintf(cmd.OutOrStdout(), "Profile projection plan\n")
	fmt.Fprintf(cmd.OutOrStdout(), "profile:         %s\n", profile)
	fmt.Fprintf(cmd.OutOrStdout(), "registered:      %t\n", registered)
	fmt.Fprintf(cmd.OutOrStdout(), "harness:         %s\n", installProfileHarness)
	fmt.Fprintf(cmd.OutOrStdout(), "projection_path: %s\n", harnessProjectionPath(installProfileHarness))
	fmt.Fprintf(cmd.OutOrStdout(), "proof_level:     %s\n", harnessProofSummary(installProfileHarness))
	if registered {
		fmt.Fprintf(cmd.OutOrStdout(), "command:         %s\n", command)
	} else {
		fmt.Fprintf(cmd.OutOrStdout(), "command:         no registered profile command yet; add it to manifests/primitive-projection-profiles.yaml before applying\n")
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
			filepath.Join(root, ".cognitive-os", "skills", "cos", name, "SKILL.md"),
			filepath.Join(root, "skills", name, "SKILL.md"),
		}, "skill", nil
	case "hook", "hooks":
		return []string{
			filepath.Join(root, ".cognitive-os", "hooks", "cos", name+".sh"),
			filepath.Join(root, "hooks", name+".sh"),
		}, "hook", nil
	case "rule", "rules":
		return []string{
			filepath.Join(root, ".cognitive-os", "rules", "cos", name+".md"),
			filepath.Join(root, "rules", name+".md"),
		}, "rule", nil
	default:
		return nil, "", fmt.Errorf("unsupported primitive family %q: use skill, hook, or rule", family)
	}
}
