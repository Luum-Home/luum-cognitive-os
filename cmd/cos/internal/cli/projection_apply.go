package cli

import (
	"bytes"
	"encoding/json"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"strings"
	"time"
)

type projectionReceipt struct {
	Kind           string            `json:"kind"`
	Harness        string            `json:"harness"`
	Profile        string            `json:"profile,omitempty"`
	Primitive      string            `json:"primitive,omitempty"`
	Source         string            `json:"source,omitempty"`
	Target         string            `json:"target,omitempty"`
	ProjectionPath string            `json:"projection_path,omitempty"`
	ProofLevel     string            `json:"proof_level"`
	Command        []string          `json:"command,omitempty"`
	Backups        []string          `json:"backups,omitempty"`
	RuntimeSmoke   map[string]string `json:"runtime_smoke,omitempty"`
	AppliedAt      string            `json:"applied_at"`
}

func cognitiveOSSourceRoot() (string, error) {
	if root := os.Getenv("COS_SOURCE_DIR"); root != "" {
		if _, err := os.Stat(filepath.Join(root, "scripts", "cos_init.py")); err == nil {
			return root, nil
		}
		return "", fmt.Errorf("COS_SOURCE_DIR=%s does not contain scripts/cos_init.py", root)
	}
	_, file, _, ok := runtime.Caller(0)
	if !ok {
		return "", fmt.Errorf("cannot resolve compiled source path")
	}
	root := filepath.Clean(filepath.Join(filepath.Dir(file), "..", "..", "..", ".."))
	if _, err := os.Stat(filepath.Join(root, "scripts", "cos_init.py")); err != nil {
		return "", fmt.Errorf("cannot resolve COS source root from %s: %w", file, err)
	}
	return root, nil
}

func applyProfileProjection(projectRoot, harness, profile string, smoke bool) (*projectionReceipt, string, error) {
	sourceRoot, err := cognitiveOSSourceRoot()
	if err != nil {
		return nil, "", err
	}
	profileFlag := "--default"
	if profile == "full" {
		profileFlag = "--full"
	}
	projectionPath := harnessProjectionPath(harness)
	stamp := receiptStamp()
	projectionPaths := harnessProjectionPaths(harness)
	jsonSnapshots, err := captureJSONSettings(projectRoot, projectionPaths)
	if err != nil {
		return nil, "", err
	}
	backups, err := backupExistingProjectionPaths(projectRoot, stamp, projectionPaths)
	if err != nil {
		return nil, "", err
	}

	command := []string{"python3", filepath.Join(sourceRoot, "scripts", "cos_init.py"), profileFlag, "--harness", harness}
	proc := exec.Command(command[0], command[1:]...)
	proc.Dir = projectRoot
	proc.Env = append(os.Environ(), "COS_SOURCE_DIR="+sourceRoot)
	var output bytes.Buffer
	proc.Stdout = &output
	proc.Stderr = &output
	if err := proc.Run(); err != nil {
		return nil, output.String(), fmt.Errorf("projection command failed: %w\n%s", err, output.String())
	}
	if err := mergeCapturedJSONSettings(projectRoot, jsonSnapshots); err != nil {
		return nil, output.String(), err
	}

	smokeResult := runOptionalHarnessRuntimeSmoke(harness, smoke)
	receipt := &projectionReceipt{
		Kind:           "profile-projection",
		Harness:        harness,
		Profile:        profile,
		ProjectionPath: projectionPath,
		ProofLevel:     harnessProofSummary(harness),
		Command:        command,
		Backups:        backups,
		RuntimeSmoke:   smokeResult,
		AppliedAt:      time.Now().UTC().Format(time.RFC3339),
	}
	if err := writeProjectionReceipt(projectRoot, stamp, receipt); err != nil {
		return nil, output.String(), err
	}
	return receipt, output.String(), nil
}

func applyPrimitiveProjection(projectRoot, spec, family, name, canonical, harness string, smoke bool) (*projectionReceipt, error) {
	sourcePath := canonical
	if !filepath.IsAbs(sourcePath) {
		sourcePath = filepath.Join(projectRoot, canonical)
	}
	if _, err := os.Stat(sourcePath); err != nil {
		return nil, fmt.Errorf("canonical primitive source not readable: %w", err)
	}
	targetRel, err := primitiveTargetPath(family, name)
	if err != nil {
		return nil, err
	}
	stamp := receiptStamp()
	paths := append([]string{targetRel}, harnessProjectionPaths(harness)...)
	backups, err := backupExistingProjectionPaths(projectRoot, stamp, paths)
	if err != nil {
		return nil, err
	}
	targetAbs := filepath.Join(projectRoot, targetRel)
	if err := copyFileConflictSafe(sourcePath, targetAbs); err != nil {
		return nil, err
	}

	smokeResult := runOptionalHarnessRuntimeSmoke(harness, smoke)
	receipt := &projectionReceipt{
		Kind:           "primitive-projection",
		Harness:        harness,
		Primitive:      spec,
		Source:         canonical,
		Target:         targetRel,
		ProjectionPath: harnessProjectionPath(harness),
		ProofLevel:     harnessProofSummary(harness),
		Backups:        backups,
		RuntimeSmoke:   smokeResult,
		AppliedAt:      time.Now().UTC().Format(time.RFC3339),
	}
	if err := writeProjectionReceipt(projectRoot, stamp, receipt); err != nil {
		return nil, err
	}
	return receipt, nil
}

func harnessProjectionPaths(harness string) []string {
	row, ok, err := findHarness(harness)
	if err != nil || !ok || len(row.SettingsPaths) == 0 {
		return []string{harnessProjectionPath(harness)}
	}
	return append([]string{}, row.SettingsPaths...)
}

type jsonSettingsSnapshot struct {
	RelPath string
	Data    any
}

func captureJSONSettings(projectRoot string, relPaths []string) ([]jsonSettingsSnapshot, error) {
	snapshots := []jsonSettingsSnapshot{}
	seen := map[string]struct{}{}
	for _, rel := range relPaths {
		if _, ok := seen[rel]; ok || !isJSONSettingsPath(rel) {
			continue
		}
		seen[rel] = struct{}{}
		abs := filepath.Join(projectRoot, rel)
		data, err := os.ReadFile(abs)
		if err != nil {
			if os.IsNotExist(err) {
				continue
			}
			return nil, err
		}
		var decoded any
		if err := json.Unmarshal(data, &decoded); err != nil {
			return nil, fmt.Errorf("parse existing JSON settings %s before projection: %w", rel, err)
		}
		snapshots = append(snapshots, jsonSettingsSnapshot{RelPath: rel, Data: decoded})
	}
	return snapshots, nil
}

func mergeCapturedJSONSettings(projectRoot string, snapshots []jsonSettingsSnapshot) error {
	for _, snapshot := range snapshots {
		abs := filepath.Join(projectRoot, snapshot.RelPath)
		data, err := os.ReadFile(abs)
		if err != nil {
			if os.IsNotExist(err) {
				continue
			}
			return err
		}
		var generated any
		if err := json.Unmarshal(data, &generated); err != nil {
			return fmt.Errorf("parse generated JSON settings %s after projection: %w", snapshot.RelPath, err)
		}
		merged := mergeJSONValues(snapshot.Data, generated)
		encoded, err := json.MarshalIndent(merged, "", "  ")
		if err != nil {
			return err
		}
		if err := os.WriteFile(abs, append(encoded, '\n'), 0644); err != nil {
			return err
		}
	}
	return nil
}

func mergeJSONValues(existing any, generated any) any {
	existingMap, existingIsMap := existing.(map[string]any)
	generatedMap, generatedIsMap := generated.(map[string]any)
	if existingIsMap && generatedIsMap {
		out := map[string]any{}
		for key, value := range generatedMap {
			out[key] = value
		}
		for key, existingValue := range existingMap {
			if generatedValue, ok := out[key]; ok {
				out[key] = mergeJSONValues(existingValue, generatedValue)
			} else {
				out[key] = existingValue
			}
		}
		return out
	}
	existingSlice, existingIsSlice := existing.([]any)
	generatedSlice, generatedIsSlice := generated.([]any)
	if existingIsSlice && generatedIsSlice {
		return mergeJSONSlices(existingSlice, generatedSlice)
	}
	if existing != nil {
		return existing
	}
	return generated
}

func mergeJSONSlices(existing []any, generated []any) []any {
	out := append([]any{}, existing...)
	seen := map[string]struct{}{}
	for _, item := range out {
		seen[jsonIdentity(item)] = struct{}{}
	}
	for _, item := range generated {
		identity := jsonIdentity(item)
		if _, ok := seen[identity]; ok {
			continue
		}
		seen[identity] = struct{}{}
		out = append(out, item)
	}
	return out
}

func jsonIdentity(value any) string {
	data, err := json.Marshal(value)
	if err != nil {
		return fmt.Sprintf("%v", value)
	}
	return string(data)
}

func isJSONSettingsPath(rel string) bool {
	lower := strings.ToLower(rel)
	return strings.HasSuffix(lower, ".json")
}

func primitiveTargetPath(family, name string) (string, error) {
	switch family {
	case "skill":
		return filepath.Join(".cognitive-os", "skills", "cos", name, "SKILL.md"), nil
	case "hook":
		return filepath.Join(".cognitive-os", "hooks", "cos", name+".sh"), nil
	case "rule":
		return filepath.Join(".cognitive-os", "rules", "cos", name+".md"), nil
	default:
		return "", fmt.Errorf("unsupported primitive family %q", family)
	}
}

func copyFileConflictSafe(source, target string) error {
	data, err := os.ReadFile(source)
	if err != nil {
		return err
	}
	if err := os.MkdirAll(filepath.Dir(target), 0755); err != nil {
		return err
	}
	return os.WriteFile(target, data, 0644)
}

func backupExistingProjectionPaths(projectRoot, stamp string, relPaths []string) ([]string, error) {
	backups := []string{}
	for _, rel := range relPaths {
		if rel == "" {
			continue
		}
		source := filepath.Join(projectRoot, rel)
		info, err := os.Stat(source)
		if err != nil || info.IsDir() {
			continue
		}
		backupRel := filepath.Join(".cognitive-os", "backups", stamp, rel)
		backupAbs := filepath.Join(projectRoot, backupRel)
		if err := os.MkdirAll(filepath.Dir(backupAbs), 0755); err != nil {
			return nil, err
		}
		data, err := os.ReadFile(source)
		if err != nil {
			return nil, err
		}
		if err := os.WriteFile(backupAbs, data, info.Mode().Perm()); err != nil {
			return nil, err
		}
		backups = append(backups, backupRel)
	}
	return backups, nil
}

func writeProjectionReceipt(projectRoot, stamp string, receipt *projectionReceipt) error {
	dir := filepath.Join(projectRoot, ".cognitive-os", "receipts")
	if err := os.MkdirAll(dir, 0755); err != nil {
		return err
	}
	data, err := json.MarshalIndent(receipt, "", "  ")
	if err != nil {
		return err
	}
	return os.WriteFile(filepath.Join(dir, "projection-"+stamp+".json"), append(data, '\n'), 0644)
}

func receiptStamp() string {
	return time.Now().UTC().Format("20060102T150405.000000000Z")
}

func runOptionalHarnessRuntimeSmoke(harness string, enabled bool) map[string]string {
	if !enabled {
		return map[string]string{"status": "not_requested"}
	}
	command := harnessRuntimeSmokeCommand(harness)
	if len(command) == 0 {
		return map[string]string{"status": "not_available_for_harness"}
	}
	if _, err := exec.LookPath(command[0]); err != nil {
		return map[string]string{"status": "skipped_missing_binary", "binary": command[0]}
	}
	proc := exec.Command(command[0], command[1:]...)
	out, err := proc.CombinedOutput()
	trimmed := strings.TrimSpace(string(out))
	if len(trimmed) > 500 {
		trimmed = trimmed[:500]
	}
	if err != nil {
		return map[string]string{"status": "failed", "binary": command[0], "output": trimmed, "error": err.Error()}
	}
	return map[string]string{"status": "passed", "binary": command[0], "output": trimmed}
}
