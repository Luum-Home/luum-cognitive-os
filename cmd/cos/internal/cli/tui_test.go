package cli

import (
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
