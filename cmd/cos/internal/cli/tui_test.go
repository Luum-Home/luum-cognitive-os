package cli

import (
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestE2E_TUISnapshotCommand(t *testing.T) {
	projectDir := createTestProject(t)

	out, exitCode := runCos(t, projectDir, "tui", "--snapshot", "--project-dir", projectDir)

	if exitCode != 0 {
		t.Fatalf("expected exit code 0, got %d. Output:\n%s", exitCode, out)
	}
	for _, want := range []string{"Surface 5 Read-Only Snapshot", "## Overview", "## cosd", "## Coverage", "## Release", "## Receipts"} {
		if !strings.Contains(out, want) {
			t.Fatalf("tui snapshot missing %q:\n%s", want, out)
		}
	}
}

func TestE2E_TUIOperateRequiresConfirm(t *testing.T) {
	projectDir := createTestProject(t)
	writeExecutableE2E(t, projectDir, "scripts/cos-coverage", "#!/usr/bin/env bash\necho refreshed\n")

	out, exitCode := runCos(t, projectDir, "tui", "--operate", "refresh-coverage", "--project-dir", projectDir)

	if exitCode == 0 {
		t.Fatalf("expected action without --confirm to fail. Output:\n%s", out)
	}
	if !strings.Contains(out, "--confirm") {
		t.Fatalf("expected confirm failure, got:\n%s", out)
	}
}

func TestE2E_TUIOperateConfirmedWritesReceipt(t *testing.T) {
	projectDir := createTestProject(t)
	writeExecutableE2E(t, projectDir, "scripts/cos-coverage", "#!/usr/bin/env bash\necho refreshed\n")

	out, exitCode := runCos(t, projectDir, "tui", "--operate", "refresh-coverage", "--confirm", "--json", "--project-dir", projectDir)

	if exitCode != 0 {
		t.Fatalf("expected exit code 0, got %d. Output:\n%s", exitCode, out)
	}
	if !strings.Contains(out, "\"outcome\": \"success\"") {
		t.Fatalf("expected success JSON, got:\n%s", out)
	}
	if _, err := os.Stat(filepath.Join(projectDir, ".cognitive-os", "metrics", "tui-actions.jsonl")); err != nil {
		t.Fatalf("expected receipt file: %v", err)
	}
}

func writeExecutableE2E(t *testing.T, dir, name, content string) {
	t.Helper()
	path := filepath.Join(dir, name)
	if err := os.MkdirAll(filepath.Dir(path), 0755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(path, []byte(content), 0755); err != nil {
		t.Fatal(err)
	}
}
