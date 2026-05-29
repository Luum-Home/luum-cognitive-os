package cli

import (
	"encoding/json"
	"fmt"
	"time"

	"github.com/spf13/cobra"

	"luum-agent-os/cmd/cos-test/internal/config"
	"luum-agent-os/cmd/cos-test/internal/quarantine"
)

var (
	quarantineManifestPath string
	quarantineToday        string
	quarantineJSON         bool
)

var quarantineCmd = &cobra.Command{
	Use:   "quarantine",
	Short: "Audit the formal test quarantine manifest.",
	Long: `Audit the formal test quarantine manifest.

The manifest lives at .cognitive-os/test-quarantine.yaml by default. Every
quarantine entry must name an exact pytest nodeid and include owner, reason,
and an expires date. Expired or malformed entries fail the audit so temporary
quarantines cannot become silent permanent skips.`,
}

var quarantineAuditCmd = &cobra.Command{
	Use:   "audit",
	Short: "Fail when quarantined tests are expired or malformed.",
	RunE: func(cmd *cobra.Command, args []string) error {
		cfg := config.DefaultConfig()
		manifestPath := quarantineManifestPath
		if manifestPath == "" {
			manifestPath = quarantine.DefaultPath(cfg.ProjectRoot)
		}
		today, err := resolveQuarantineToday(quarantineToday)
		if err != nil {
			return err
		}
		return runQuarantineAudit(manifestPath, today, quarantineJSON)
	},
}

func init() {
	quarantineAuditCmd.Flags().StringVar(&quarantineManifestPath, "manifest", "",
		"Path to test quarantine manifest (default .cognitive-os/test-quarantine.yaml)")
	quarantineAuditCmd.Flags().StringVar(&quarantineToday, "today", "",
		"Override today's date for deterministic audits (YYYY-MM-DD)")
	quarantineAuditCmd.Flags().BoolVar(&quarantineJSON, "json", false,
		"Emit machine-readable quarantine audit output")
	quarantineCmd.AddCommand(quarantineAuditCmd)
	rootCmd.AddCommand(quarantineCmd)
}

func runQuarantineAudit(manifestPath string, today time.Time, emitJSON bool) error {
	manifest, err := quarantine.Load(manifestPath)
	if err != nil {
		return err
	}
	findings := quarantine.Audit(manifest, today)
	if emitJSON {
		payload := map[string]any{
			"schema_version": "test-quarantine-audit/v1",
			"status":         "pass",
			"manifest":       manifestPath,
			"entry_count":    len(manifest.Entries),
			"finding_count":  len(findings),
			"findings":       []string{},
		}
		if len(findings) > 0 {
			payload["status"] = "fail"
			values := make([]string, 0, len(findings))
			for _, finding := range findings {
				values = append(values, finding.String())
			}
			payload["findings"] = values
		}
		encoded, encodeErr := json.MarshalIndent(payload, "", "  ")
		if encodeErr != nil {
			return encodeErr
		}
		fmt.Println(string(encoded))
	} else if len(findings) == 0 {
		fmt.Printf("[cos-test quarantine] OK: %s (%d entries)\n", manifestPath, len(manifest.Entries))
	} else {
		fmt.Printf("[cos-test quarantine] FAIL: %s (%d findings)\n", manifestPath, len(findings))
		for _, finding := range findings {
			fmt.Printf("[cos-test quarantine] - %s\n", finding.String())
		}
	}
	if len(findings) > 0 {
		return fmt.Errorf("test quarantine audit failed")
	}
	return nil
}

func resolveQuarantineToday(value string) (time.Time, error) {
	if value == "" {
		return time.Now().UTC(), nil
	}
	parsed, err := time.Parse(time.DateOnly, value)
	if err != nil {
		return time.Time{}, fmt.Errorf("--today must be YYYY-MM-DD: %w", err)
	}
	return parsed, nil
}
