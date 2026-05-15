package cli

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"sort"

	"github.com/spf13/cobra"

	"luum-agent-os/cmd/cos/internal/project"
)

var (
	doctorHarnessName string
	doctorHarnessJSON bool
)

type harnessDoctorPayload struct {
	Harness        string         `json:"harness"`
	Status         string         `json:"status"`
	ProjectionPath string         `json:"projection_path"`
	ProofLevel     string         `json:"proof_level"`
	SettingsPaths  []string       `json:"settings_paths"`
	Receipts       receiptSummary `json:"receipts"`
	RuntimeSmoke   map[string]int `json:"runtime_smoke"`
	NextAction     string         `json:"next_action,omitempty"`
}

type receiptSummary struct {
	Total       int            `json:"total"`
	ByKind      map[string]int `json:"by_kind"`
	BackupCount int            `json:"backup_count"`
	Latest      string         `json:"latest,omitempty"`
}

var doctorCmd = &cobra.Command{
	Use:   "doctor",
	Short: "Run Cognitive OS diagnostics",
}

var doctorHarnessCmd = &cobra.Command{
	Use:   "harness",
	Short: "Report active harness projection receipts and proof level",
	Args:  cobra.NoArgs,
	RunE:  runDoctorHarness,
}

func init() {
	doctorHarnessCmd.Flags().StringVar(&doctorHarnessName, "harness", "", "Harness to inspect (defaults to .cognitive-os/install-meta.json or claude)")
	doctorHarnessCmd.Flags().BoolVar(&doctorHarnessJSON, "json", false, "Emit JSON")
	doctorCmd.AddCommand(doctorHarnessCmd)
	rootCmd.AddCommand(doctorCmd)
}

func runDoctorHarness(cmd *cobra.Command, args []string) error {
	root := project.FindRootOrCwd()
	harness := doctorHarnessName
	if harness == "" {
		harness = installedHarnessOrDefault(root)
	}
	if err := validateHarness(harness); err != nil {
		return err
	}
	row, _, err := findHarness(harness)
	if err != nil {
		return err
	}
	payload, err := buildHarnessDoctorPayload(root, row)
	if err != nil {
		return err
	}
	if doctorHarnessJSON {
		data, err := json.MarshalIndent(payload, "", "  ")
		if err != nil {
			return err
		}
		fmt.Fprintln(cmd.OutOrStdout(), string(data))
		return nil
	}
	fmt.Fprintf(cmd.OutOrStdout(), "Harness doctor\n")
	fmt.Fprintf(cmd.OutOrStdout(), "harness:         %s\n", payload.Harness)
	fmt.Fprintf(cmd.OutOrStdout(), "status:          %s\n", payload.Status)
	fmt.Fprintf(cmd.OutOrStdout(), "projection_path: %s\n", payload.ProjectionPath)
	fmt.Fprintf(cmd.OutOrStdout(), "proof_level:     %s\n", payload.ProofLevel)
	fmt.Fprintf(cmd.OutOrStdout(), "settings_paths:  %d\n", len(payload.SettingsPaths))
	fmt.Fprintf(cmd.OutOrStdout(), "receipts:        %d\n", payload.Receipts.Total)
	fmt.Fprintf(cmd.OutOrStdout(), "backups:         %d\n", payload.Receipts.BackupCount)
	fmt.Fprintf(cmd.OutOrStdout(), "runtime_smoke:   %v\n", payload.RuntimeSmoke)
	if payload.NextAction != "" {
		fmt.Fprintf(cmd.OutOrStdout(), "next_action:     %s\n", payload.NextAction)
	}
	return nil
}

func buildHarnessDoctorPayload(root string, row harnessRegistryEntry) (harnessDoctorPayload, error) {
	receipts, smoke, err := summarizeProjectionReceipts(root, row.ID)
	if err != nil {
		return harnessDoctorPayload{}, err
	}
	return harnessDoctorPayload{
		Harness:        row.ID,
		Status:         row.Status,
		ProjectionPath: row.PrimarySettingsPath,
		ProofLevel:     row.ProofLevel,
		SettingsPaths:  row.SettingsPaths,
		Receipts:       receipts,
		RuntimeSmoke:   smoke,
		NextAction:     row.NextAction,
	}, nil
}

func installedHarnessOrDefault(root string) string {
	metaPath := filepath.Join(root, ".cognitive-os", "install-meta.json")
	data, err := os.ReadFile(metaPath)
	if err != nil {
		return "claude"
	}
	var payload map[string]any
	if err := json.Unmarshal(data, &payload); err != nil {
		return "claude"
	}
	if harness, ok := payload["harness"].(string); ok && harness != "" {
		return harness
	}
	return "claude"
}

func summarizeProjectionReceipts(root, harness string) (receiptSummary, map[string]int, error) {
	paths, err := filepath.Glob(filepath.Join(root, ".cognitive-os", "receipts", "projection-*.json"))
	if err != nil {
		return receiptSummary{}, nil, err
	}
	sort.Strings(paths)
	summary := receiptSummary{ByKind: map[string]int{}}
	smoke := map[string]int{}
	for _, path := range paths {
		data, err := os.ReadFile(path)
		if err != nil {
			return receiptSummary{}, nil, err
		}
		var receipt projectionReceipt
		if err := json.Unmarshal(data, &receipt); err != nil {
			continue
		}
		if receipt.Harness != harness {
			continue
		}
		summary.Total++
		summary.ByKind[receipt.Kind]++
		summary.BackupCount += len(receipt.Backups)
		summary.Latest = filepath.Base(path)
		if receipt.RuntimeSmoke != nil {
			smoke[receipt.RuntimeSmoke["status"]]++
		}
	}
	return summary, smoke, nil
}
