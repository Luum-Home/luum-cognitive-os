package cli

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"

	"github.com/spf13/cobra"

	"luum-agent-os/cmd/cos/internal/project"
)

var (
	primitiveStatsHarness string
	primitiveStatsJSON    bool
)

type primitiveStatsPayload struct {
	Harness        string            `json:"harness"`
	ProjectionPath string            `json:"projection_path"`
	ProofLevel     string            `json:"proof_level"`
	Installed      map[string]int    `json:"installed"`
	Receipts       receiptSummary    `json:"receipts"`
	RuntimeSmoke   map[string]int    `json:"runtime_smoke"`
	Registry       map[string]string `json:"registry"`
}

var primitiveCmd = &cobra.Command{
	Use:   "primitive",
	Short: "Inspect Cognitive OS agentic primitives",
}

var primitiveStatsCmd = &cobra.Command{
	Use:   "stats",
	Short: "Report primitive projection stats for a harness",
	Args:  cobra.NoArgs,
	RunE:  runPrimitiveStats,
}

func init() {
	primitiveStatsCmd.Flags().StringVar(&primitiveStatsHarness, "harness", "", "Harness to inspect (defaults to .cognitive-os/install-meta.json or claude)")
	primitiveStatsCmd.Flags().BoolVar(&primitiveStatsJSON, "json", false, "Emit JSON")
	primitiveCmd.AddCommand(primitiveStatsCmd)
	rootCmd.AddCommand(primitiveCmd)
}

func runPrimitiveStats(cmd *cobra.Command, args []string) error {
	root := project.FindRootOrCwd()
	harness := primitiveStatsHarness
	if harness == "" {
		harness = installedHarnessOrDefault(root)
	}
	if err := validateHarness(harness); err != nil {
		return err
	}
	receipts, smoke, err := summarizeProjectionReceipts(root, harness)
	if err != nil {
		return err
	}
	payload := primitiveStatsPayload{
		Harness:        harness,
		ProjectionPath: harnessProjectionPath(harness),
		ProofLevel:     harnessProofSummary(harness),
		Installed:      installedPrimitiveCounts(root),
		Receipts:       receipts,
		RuntimeSmoke:   smoke,
		Registry: map[string]string{
			"source":             "manifests/agentic-primitive-registry.lock.yaml",
			"harness_projection": "manifests/harness-projection-registry.json",
		},
	}
	if primitiveStatsJSON {
		data, err := json.MarshalIndent(payload, "", "  ")
		if err != nil {
			return err
		}
		fmt.Fprintln(cmd.OutOrStdout(), string(data))
		return nil
	}
	fmt.Fprintf(cmd.OutOrStdout(), "Primitive stats\n")
	fmt.Fprintf(cmd.OutOrStdout(), "harness:         %s\n", payload.Harness)
	fmt.Fprintf(cmd.OutOrStdout(), "projection_path: %s\n", payload.ProjectionPath)
	fmt.Fprintf(cmd.OutOrStdout(), "proof_level:     %s\n", payload.ProofLevel)
	fmt.Fprintf(cmd.OutOrStdout(), "skills:          %d\n", payload.Installed["skills"])
	fmt.Fprintf(cmd.OutOrStdout(), "hooks:           %d\n", payload.Installed["hooks"])
	fmt.Fprintf(cmd.OutOrStdout(), "rules:           %d\n", payload.Installed["rules"])
	fmt.Fprintf(cmd.OutOrStdout(), "receipts:        %d\n", payload.Receipts.Total)
	fmt.Fprintf(cmd.OutOrStdout(), "runtime_smoke:   %v\n", payload.RuntimeSmoke)
	return nil
}

func installedPrimitiveCounts(root string) map[string]int {
	return map[string]int{
		"skills": countDirs(filepath.Join(root, ".cognitive-os", "skills", "cos")),
		"hooks":  countGlob(filepath.Join(root, ".cognitive-os", "hooks", "cos", "*.sh")),
		"rules":  countGlob(filepath.Join(root, ".cognitive-os", "rules", "cos", "*.md")),
	}
}

func countDirs(path string) int {
	entries, err := os.ReadDir(path)
	if err != nil {
		return 0
	}
	count := 0
	for _, entry := range entries {
		if entry.IsDir() {
			count++
		}
	}
	return count
}

func countGlob(pattern string) int {
	matches, err := filepath.Glob(pattern)
	if err != nil {
		return 0
	}
	return len(matches)
}
