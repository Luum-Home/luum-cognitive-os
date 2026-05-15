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
	backups, err := backupExistingProjectionPaths(projectRoot, stamp, []string{projectionPath})
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
	backups, err := backupExistingProjectionPaths(projectRoot, stamp, []string{targetRel, harnessProjectionPath(harness)})
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

var harnessRuntimeSmokeCommands = map[string][]string{
	"cursor":     {"cursor", "--version"},
	"qwen-code":  {"qwen", "--version"},
	"gemini-cli": {"gemini", "--version"},
	"opencode":   {"opencode", "--version"},
}

func runOptionalHarnessRuntimeSmoke(harness string, enabled bool) map[string]string {
	if !enabled {
		return map[string]string{"status": "not_requested"}
	}
	command, ok := harnessRuntimeSmokeCommands[harness]
	if !ok {
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
