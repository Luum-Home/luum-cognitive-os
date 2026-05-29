package cli

import (
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestDeriveCheckRunsDerivedArtifactGateFromProjectRoot(t *testing.T) {
	dir := createTestProject(t)
	subdir := filepath.Join(dir, "nested")
	if err := os.MkdirAll(subdir, 0755); err != nil {
		t.Fatal(err)
	}
	writeTestFileE2E(t, dir, "scripts/derived_artifact_gate.py", `#!/usr/bin/env python3
import os
from pathlib import Path

root = Path(os.environ["PROJECT_DIR"])
if Path.cwd() != root:
    raise SystemExit(f"wrong cwd: {Path.cwd()} != {root}")
(root / ".derive-log").write_text("gate\n", encoding="utf-8")
print("derived-artifact-gate: OK")
`)

	out, code := runCos(t, subdir, "derive", "--check")
	if code != 0 {
		t.Fatalf("expected exit 0, got %d\n%s", code, out)
	}
	if !strings.Contains(out, "derived-artifact-gate: OK") {
		t.Fatalf("expected gate output, got:\n%s", out)
	}
	assertDeriveLog(t, dir, "gate\n")
}

func TestDeriveSyncRunsSynchronizersThenGate(t *testing.T) {
	dir := createTestProject(t)
	writeTestFileE2E(t, dir, "scripts/hook_quality_audit.py", `#!/usr/bin/env python3
import os
import sys
from pathlib import Path

root = Path(os.environ["PROJECT_DIR"])
with (root / ".derive-log").open("a", encoding="utf-8") as fh:
    fh.write("hook_quality " + " ".join(sys.argv[1:]) + "\n")
print("hook-quality: wrote manifests/hook-quality.yaml")
`)
	writeTestFileE2E(t, dir, "scripts/_lib/settings-driver-claude-code.sh", `#!/usr/bin/env bash
set -euo pipefail
printf 'claude %s\n' "$*" >> "$PROJECT_DIR/.derive-log"
echo "settings-driver-claude-code: wrote $PROJECT_DIR/.claude/settings.json"
`)
	writeTestFileE2E(t, dir, "scripts/_lib/settings-driver-codex.sh", `#!/usr/bin/env bash
set -euo pipefail
printf 'codex %s\n' "$*" >> "$PROJECT_DIR/.derive-log"
echo "settings-driver-codex: wrote $PROJECT_DIR/.codex/hooks.json"
`)
	writeTestFileE2E(t, dir, "scripts/derived_artifact_gate.py", `#!/usr/bin/env python3
import os
from pathlib import Path

root = Path(os.environ["PROJECT_DIR"])
with (root / ".derive-log").open("a", encoding="utf-8") as fh:
    fh.write("gate\n")
print("derived-artifact-gate: OK")
`)

	out, code := runCos(t, dir, "derive", "--sync")
	if code != 0 {
		t.Fatalf("expected exit 0, got %d\n%s", code, out)
	}
	for _, want := range []string{
		"hook-quality: wrote",
		"settings-driver-claude-code: wrote",
		"settings-driver-codex: wrote",
		"derived-artifact-gate: OK",
	} {
		if !strings.Contains(out, want) {
			t.Fatalf("expected output to contain %q\n%s", want, out)
		}
	}
	assertDeriveLog(t, dir, "hook_quality --sync\nclaude \ncodex \ngate\n")
}

func TestDeriveRequiresExactlyOneMode(t *testing.T) {
	dir := createTestProject(t)

	out, code := runCos(t, dir, "derive")
	if code == 0 {
		t.Fatalf("expected non-zero for missing mode\n%s", out)
	}
	if !strings.Contains(out, "choose exactly one of check, sync, --check, or --sync") {
		t.Fatalf("expected mode selection error, got:\n%s", out)
	}

	out, code = runCos(t, dir, "derive", "--check", "--sync")
	if code == 0 {
		t.Fatalf("expected non-zero for conflicting modes\n%s", out)
	}
	if !strings.Contains(out, "choose exactly one of check, sync, --check, or --sync") {
		t.Fatalf("expected mode selection error, got:\n%s", out)
	}
}

func TestDeriveCheckSubcommandRunsDerivedArtifactGate(t *testing.T) {
	dir := createTestProject(t)
	writeTestFileE2E(t, dir, "scripts/derived_artifact_gate.py", `#!/usr/bin/env python3
from pathlib import Path
Path(".derive-log").write_text("gate-subcommand\n", encoding="utf-8")
print("derived-artifact-gate: OK")
`)

	out, code := runCos(t, dir, "derive", "check")
	if code != 0 {
		t.Fatalf("expected exit 0, got %d\n%s", code, out)
	}
	assertDeriveLog(t, dir, "gate-subcommand\n")
}

func TestDeriveCommandHasCheckAndSyncSubcommands(t *testing.T) {
	foundDerive := false
	for _, child := range rootCmd.Commands() {
		if child.Name() != "derive" {
			continue
		}
		foundDerive = true
		foundCheck := false
		foundSync := false
		for _, deriveChild := range child.Commands() {
			switch deriveChild.Name() {
			case "check":
				foundCheck = true
			case "sync":
				foundSync = true
			}
		}
		if !foundCheck || !foundSync {
			t.Fatalf("derive subcommands check=%v sync=%v", foundCheck, foundSync)
		}
	}
	if !foundDerive {
		t.Fatalf("derive command not registered")
	}
}

func assertDeriveLog(t *testing.T, dir string, want string) {
	t.Helper()
	data, err := os.ReadFile(filepath.Join(dir, ".derive-log"))
	if err != nil {
		t.Fatal(err)
	}
	if string(data) != want {
		t.Fatalf("unexpected derive log:\nwant %q\ngot  %q", want, string(data))
	}
}
