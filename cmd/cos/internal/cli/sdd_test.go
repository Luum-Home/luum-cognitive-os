package cli

import (
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestE2E_SDDLocalLaneHappyPath(t *testing.T) {
	projectDir := createTestProject(t)

	out, exitCode := runCos(t, projectDir, "sdd", "next", "--feature", "cli_recent", "--title", "CLI recent", "--work-class", "medium")
	if exitCode != 0 {
		t.Fatalf("expected next to pass, got %d\n%s", exitCode, out)
	}
	if !strings.Contains(out, "status=spec_ready") {
		t.Fatalf("expected spec_ready output, got:\n%s", out)
	}
	for _, rel := range []string{
		".cognitive-os/workflows/sdd/state.json",
		".cognitive-os/workflows/sdd/cli_recent/requirements.md",
		".cognitive-os/workflows/sdd/cli_recent/design.md",
		".cognitive-os/workflows/sdd/cli_recent/tasks.md",
		".cognitive-os/workflows/sdd/cli_recent/traceability.md",
		".cognitive-os/workflows/sdd/progress/current.md",
	} {
		assertFileExists(t, filepath.Join(projectDir, rel))
	}

	out, exitCode = runCos(t, projectDir, "sdd", "approve", "cli_recent")
	if exitCode != 0 {
		t.Fatalf("expected approve to pass, got %d\n%s", exitCode, out)
	}
	out, exitCode = runCos(t, projectDir, "sdd", "apply", "cli_recent")
	if exitCode != 0 {
		t.Fatalf("expected apply to pass, got %d\n%s", exitCode, out)
	}

	writeTestFileE2E(t, projectDir, ".cognitive-os/workflows/sdd/cli_recent/tasks.md", "# Tasks\n\n- [x] Implement R1.\n- [x] Add evidence for R2.\n")
	out, exitCode = runCos(t, projectDir, "sdd", "review", "cli_recent")
	if exitCode != 0 {
		t.Fatalf("expected review to pass, got %d\n%s", exitCode, out)
	}
	if !strings.Contains(out, "verdict=PASS") {
		t.Fatalf("expected PASS review, got:\n%s", out)
	}
	assertFileExists(t, filepath.Join(projectDir, ".cognitive-os/workflows/sdd/progress/history.md"))

	state := readSDDTestState(t, projectDir)
	features := state["features"].(map[string]any)
	feature := features["cli_recent"].(map[string]any)
	if got := feature["status"]; got != "done" {
		t.Fatalf("expected done status, got %v", got)
	}
}

func TestE2E_SDDReviewFailsMissingTraceability(t *testing.T) {
	projectDir := createTestProject(t)
	if out, exitCode := runCos(t, projectDir, "sdd", "next", "--feature", "missing_trace"); exitCode != 0 {
		t.Fatalf("next failed: %d\n%s", exitCode, out)
	}
	if out, exitCode := runCos(t, projectDir, "sdd", "approve", "missing_trace"); exitCode != 0 {
		t.Fatalf("approve failed: %d\n%s", exitCode, out)
	}
	if out, exitCode := runCos(t, projectDir, "sdd", "apply", "missing_trace"); exitCode != 0 {
		t.Fatalf("apply failed: %d\n%s", exitCode, out)
	}
	writeTestFileE2E(t, projectDir, ".cognitive-os/workflows/sdd/missing_trace/tasks.md", "# Tasks\n\n- [x] Implement R1.\n- [x] Add evidence for R2.\n")
	writeTestFileE2E(t, projectDir, ".cognitive-os/workflows/sdd/missing_trace/traceability.md", "# Traceability\n\n| Requirement | Evidence | Status | Notes |\n|---|---|---|---|\n| R1 | tests/test_cli.py::test_recent | PASS | ok |\n")

	out, exitCode := runCos(t, projectDir, "sdd", "review", "missing_trace")
	if exitCode == 0 {
		t.Fatalf("expected review failure, got success:\n%s", out)
	}
	if !strings.Contains(out, "verdict=FAIL") || !strings.Contains(out, "SDD review failed") {
		t.Fatalf("expected FAIL diagnosis, got:\n%s", out)
	}
	review, err := os.ReadFile(filepath.Join(projectDir, ".cognitive-os/workflows/sdd/missing_trace/review.md"))
	if err != nil {
		t.Fatal(err)
	}
	if !strings.Contains(string(review), "R2 lacks test or accepted proof mapping") {
		t.Fatalf("expected R2 finding, got:\n%s", review)
	}
}

func TestE2E_SDDRejectsSecondActiveFeature(t *testing.T) {
	projectDir := createTestProject(t)
	if out, exitCode := runCos(t, projectDir, "sdd", "next", "--feature", "one"); exitCode != 0 {
		t.Fatalf("next one failed: %d\n%s", exitCode, out)
	}
	out, exitCode := runCos(t, projectDir, "sdd", "next", "--feature", "two")
	if exitCode == 0 {
		t.Fatalf("expected second active feature to fail, got success:\n%s", out)
	}
	if !strings.Contains(out, "one active feature") {
		t.Fatalf("expected one-active-feature diagnosis, got:\n%s", out)
	}
}

func readSDDTestState(t *testing.T, projectDir string) map[string]any {
	t.Helper()
	data, err := os.ReadFile(filepath.Join(projectDir, ".cognitive-os/workflows/sdd/state.json"))
	if err != nil {
		t.Fatal(err)
	}
	var state map[string]any
	if err := json.Unmarshal(data, &state); err != nil {
		t.Fatal(err)
	}
	return state
}
