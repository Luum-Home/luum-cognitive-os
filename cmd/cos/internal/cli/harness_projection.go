package cli

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"sync"
)

type harnessRegistry struct {
	SchemaVersion    string                 `json:"schema_version"`
	ImplementedOrder []string               `json:"implemented_order"`
	Harnesses        []harnessRegistryEntry `json:"harnesses"`
}

type harnessRegistryEntry struct {
	ID                  string   `json:"id"`
	DisplayName         string   `json:"display_name"`
	Status              string   `json:"status"`
	ProjectionMode      string   `json:"projection_mode"`
	ProofLevel          string   `json:"proof_level"`
	SettingsPaths       []string `json:"settings_paths"`
	PrimarySettingsPath string   `json:"primary_settings_path"`
	RuntimeSmokeCommand []string `json:"runtime_smoke_command"`
	NextAction          string   `json:"next_action"`
}

var (
	harnessRegistryOnce sync.Once
	harnessRegistryData *harnessRegistry
	harnessRegistryErr  error
)

func loadHarnessRegistry() (*harnessRegistry, error) {
	harnessRegistryOnce.Do(func() {
		root, err := cognitiveOSSourceRoot()
		if err != nil {
			harnessRegistryErr = err
			return
		}
		path := filepath.Join(root, "manifests", "harness-projection-registry.json")
		data, err := os.ReadFile(path)
		if err != nil {
			harnessRegistryErr = fmt.Errorf("read harness projection registry: %w", err)
			return
		}
		var registry harnessRegistry
		if err := json.Unmarshal(data, &registry); err != nil {
			harnessRegistryErr = fmt.Errorf("parse harness projection registry: %w", err)
			return
		}
		harnessRegistryData = &registry
	})
	return harnessRegistryData, harnessRegistryErr
}

func implementedHarnesses() ([]harnessRegistryEntry, error) {
	registry, err := loadHarnessRegistry()
	if err != nil {
		return nil, err
	}
	byID := make(map[string]harnessRegistryEntry, len(registry.Harnesses))
	for _, row := range registry.Harnesses {
		byID[row.ID] = row
	}
	out := make([]harnessRegistryEntry, 0, len(registry.ImplementedOrder))
	for _, id := range registry.ImplementedOrder {
		row, ok := byID[id]
		if !ok || row.Status != "implemented" {
			continue
		}
		out = append(out, row)
	}
	return out, nil
}

func supportedHarnessNames() ([]string, error) {
	rows, err := implementedHarnesses()
	if err != nil {
		return nil, err
	}
	out := make([]string, 0, len(rows))
	for _, row := range rows {
		out = append(out, row.ID)
	}
	return out, nil
}

func findHarness(harness string) (harnessRegistryEntry, bool, error) {
	registry, err := loadHarnessRegistry()
	if err != nil {
		return harnessRegistryEntry{}, false, err
	}
	for _, row := range registry.Harnesses {
		if row.ID == harness {
			return row, true, nil
		}
	}
	return harnessRegistryEntry{}, false, nil
}

func validateHarness(harness string) error {
	row, ok, err := findHarness(harness)
	if err != nil {
		return err
	}
	if ok && row.Status == "implemented" {
		return nil
	}
	if ok && row.Status == "planned" {
		reason := row.NextAction
		if reason == "" {
			reason = "driver/proof is not implemented yet"
		}
		return fmt.Errorf("unsupported harness %q: planned in manifests/harness-projection.yaml; %s", harness, reason)
	}
	names, err := supportedHarnessNames()
	if err != nil {
		return err
	}
	return fmt.Errorf("unsupported harness %q: supported harnesses are %s", harness, strings.Join(names, ", "))
}

func harnessProjectionPath(harness string) string {
	row, ok, err := findHarness(harness)
	if err == nil && ok && row.PrimarySettingsPath != "" {
		return row.PrimarySettingsPath
	}
	return ".cognitive-os/install-meta.json"
}

func harnessProofSummary(harness string) string {
	row, ok, err := findHarness(harness)
	if err == nil && ok && row.ProofLevel != "" {
		return row.ProofLevel
	}
	return "unknown"
}

func harnessRuntimeSmokeCommand(harness string) []string {
	row, ok, err := findHarness(harness)
	if err != nil || !ok || len(row.RuntimeSmokeCommand) == 0 {
		return nil
	}
	return append([]string{}, row.RuntimeSmokeCommand...)
}
