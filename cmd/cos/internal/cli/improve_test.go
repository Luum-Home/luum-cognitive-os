package cli

import (
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestImproveCommandHasRunFeedbackAndContextSubcommands(t *testing.T) {
	foundImprove := false
	for _, child := range rootCmd.Commands() {
		if child.Name() != "improve" {
			continue
		}
		foundImprove = true
		found := map[string]bool{}
		for _, improveChild := range child.Commands() {
			found[improveChild.Name()] = true
		}
		for _, want := range []string{"run", "feedback", "context"} {
			if !found[want] {
				t.Fatalf("improve missing %s subcommand", want)
			}
		}
	}
	if !foundImprove {
		t.Fatalf("improve command not registered")
	}
}

func TestImproveRunDelegatesToProjectScript(t *testing.T) {
	dir := createTestProject(t)
	writeTestFileE2E(t, dir, "scripts/cos_improve.py", `#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path
root = Path(sys.argv[sys.argv.index("--project-dir") + 1])
(root / ".improve-argv").write_text(" ".join(sys.argv[1:]), encoding="utf-8")
print(json.dumps({"argv": sys.argv[1:]}))
`)
	if err := os.Chmod(filepath.Join(dir, "scripts", "cos_improve.py"), 0755); err != nil {
		t.Fatal(err)
	}

	out, code := runCos(t, dir, "improve", "run", "--task-dir", "bench", "--run-id", "cli-smoke")
	if code != 0 {
		t.Fatalf("expected exit 0, got %d\n%s", code, out)
	}
	data, err := os.ReadFile(filepath.Join(dir, ".improve-argv"))
	if err != nil {
		t.Fatal(err)
	}
	got := string(data)
	for _, want := range []string{"run", "--project-dir", "--task-dir bench", "--run-id cli-smoke"} {
		if !strings.Contains(got, want) {
			t.Fatalf("expected argv to contain %q, got %q", want, got)
		}
	}
}
