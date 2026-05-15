package cli

import (
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestInstallPrimitiveDryRunSkillForCursor(t *testing.T) {
	dir := createTestProject(t)
	writeTestFileE2E(t, dir, ".cognitive-os/skills/cos/cos-status/SKILL.md", "---\nname: cos-status\n---\n")

	out, code := runCos(t, dir, "install", "primitive", "skill/cos-status", "--harness", "cursor", "--dry-run")
	if code != 0 {
		t.Fatalf("expected exit 0, got %d\n%s", code, out)
	}
	for _, want := range []string{
		"Primitive projection plan",
		"primitive:        skill/cos-status",
		"harness:          cursor",
		"projection_path:  .cursor/rules/cognitive-os.mdc",
		"proof_level:      structural",
	} {
		if !strings.Contains(out, want) {
			t.Fatalf("expected output to contain %q\n%s", want, out)
		}
	}
}

func TestInstallPrimitiveApplyWritesTargetBackupAndReceipt(t *testing.T) {
	dir := createTestProject(t)
	writeTestFileE2E(t, dir, "skills/cos-status/SKILL.md", "---\nname: cos-status\n---\nnew\n")
	writeTestFileE2E(t, dir, ".cognitive-os/skills/cos/cos-status/SKILL.md", "old\n")
	writeTestFileE2E(t, dir, ".cursor/rules/cognitive-os.mdc", "existing cursor rules\n")

	out, code := runCos(t, dir, "install", "primitive", "skill/cos-status", "--harness", "cursor")
	if code != 0 {
		t.Fatalf("expected exit 0, got %d\n%s", code, out)
	}
	for _, want := range []string{"Primitive projection applied", "target:           .cognitive-os/skills/cos/cos-status/SKILL.md", "backups:          2", "runtime_smoke:    not_requested"} {
		if !strings.Contains(out, want) {
			t.Fatalf("expected output to contain %q\n%s", want, out)
		}
	}
	installed := filepath.Join(dir, ".cognitive-os", "skills", "cos", "cos-status", "SKILL.md")
	data, err := os.ReadFile(installed)
	if err != nil {
		t.Fatal(err)
	}
	if !strings.Contains(string(data), "new") {
		t.Fatalf("expected installed primitive to be copied, got %q", string(data))
	}
	assertProjectionReceipt(t, dir, "primitive-projection", "cursor")
}

func TestInstallProfilePlanShowsUnregisteredProfile(t *testing.T) {
	dir := createTestProject(t)

	out, code := runCos(t, dir, "install", "profile", "sre", "--harness", "claude")
	if code != 0 {
		t.Fatalf("expected exit 0 for unregistered profile plan, got %d\n%s", code, out)
	}
	if !strings.Contains(out, "registered:      false") {
		t.Fatalf("expected unregistered profile plan\n%s", out)
	}
	if !strings.Contains(out, "manifests/primitive-projection-profiles.yaml") {
		t.Fatalf("expected manifest guidance\n%s", out)
	}
}

func TestProjectRejectsPlannedButUnsupportedWindsurf(t *testing.T) {
	dir := createTestProject(t)

	out, code := runCos(t, dir, "project", "--harness", "windsurf")
	if code == 0 {
		t.Fatalf("expected non-zero for unsupported windsurf\n%s", out)
	}
	if !strings.Contains(out, "unsupported harness \"windsurf\"") || !strings.Contains(out, "planned") {
		t.Fatalf("expected planned unsupported harness message\n%s", out)
	}
}

func TestProjectDryRunForCursor(t *testing.T) {
	dir := createTestProject(t)

	out, code := runCos(t, dir, "project", "--harness", "cursor", "--dry-run")
	if code != 0 {
		t.Fatalf("expected exit 0, got %d\n%s", code, out)
	}
	for _, want := range []string{
		"Project projection plan",
		"profile:         default",
		"harness:         cursor",
		"command:         python3 scripts/cos_init.py --default --harness cursor",
	} {
		if !strings.Contains(out, want) {
			t.Fatalf("expected output to contain %q\n%s", want, out)
		}
	}
}

func TestProjectApplyForCursorWritesProjectionReceiptAndMergesJSON(t *testing.T) {
	dir := createTestProject(t)
	writeTestFileE2E(t, dir, ".cursor/mcp.json", `{
  "existing": true,
  "mcpServers": {
    "custom": {"command": "custom-cli"}
  }
}
`)

	out, code := runCos(t, dir, "project", "--harness", "cursor")
	if code != 0 {
		t.Fatalf("expected exit 0, got %d\n%s", code, out)
	}
	for _, want := range []string{"Project projection applied", "harness:         cursor", "runtime_smoke:   not_requested"} {
		if !strings.Contains(out, want) {
			t.Fatalf("expected output to contain %q\n%s", want, out)
		}
	}
	if _, err := os.Stat(filepath.Join(dir, ".cursor", "rules", "cognitive-os.mdc")); err != nil {
		t.Fatalf("expected cursor projection file: %v", err)
	}
	mcpData, err := os.ReadFile(filepath.Join(dir, ".cursor", "mcp.json"))
	if err != nil {
		t.Fatal(err)
	}
	var mcp map[string]any
	if err := json.Unmarshal(mcpData, &mcp); err != nil {
		t.Fatal(err)
	}
	if mcp["existing"] != true {
		t.Fatalf("expected JSON merge to preserve existing settings: %s", mcpData)
	}
	assertProjectionReceipt(t, dir, "profile-projection", "cursor")
}

func TestDoctorHarnessReportsReceiptsAndProofLevel(t *testing.T) {
	dir := createTestProject(t)
	out, code := runCos(t, dir, "project", "--harness", "cursor")
	if code != 0 {
		t.Fatalf("expected projection apply to pass, got %d\n%s", code, out)
	}

	out, code = runCos(t, dir, "doctor", "harness", "--harness", "cursor", "--json")
	if code != 0 {
		t.Fatalf("expected doctor to pass, got %d\n%s", code, out)
	}
	var payload map[string]any
	if err := json.Unmarshal([]byte(out), &payload); err != nil {
		t.Fatal(err)
	}
	if payload["harness"] != "cursor" || payload["proof_level"] != "structural" {
		t.Fatalf("unexpected doctor payload: %s", out)
	}
	receipts := payload["receipts"].(map[string]any)
	if receipts["total"].(float64) < 1 {
		t.Fatalf("expected at least one receipt: %s", out)
	}
}

func assertProjectionReceipt(t *testing.T, dir, kind, harness string) {
	t.Helper()
	receipts, err := filepath.Glob(filepath.Join(dir, ".cognitive-os", "receipts", "projection-*.json"))
	if err != nil || len(receipts) == 0 {
		t.Fatalf("expected projection receipt, err=%v receipts=%v", err, receipts)
	}
	data, err := os.ReadFile(receipts[len(receipts)-1])
	if err != nil {
		t.Fatal(err)
	}
	var payload map[string]any
	if err := json.Unmarshal(data, &payload); err != nil {
		t.Fatal(err)
	}
	if payload["kind"] != kind || payload["harness"] != harness {
		t.Fatalf("unexpected receipt: %s", data)
	}
}
