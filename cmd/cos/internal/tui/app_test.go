package tui

import (
	"os"
	"path/filepath"
	"strings"
	"testing"

	tea "github.com/charmbracelet/bubbletea"
)

func TestLoadSnapshotReadsOperatorArtifacts(t *testing.T) {
	root := t.TempDir()
	writeFile(t, root, ".goreleaser.yaml", "project_name: cos\n")
	writeFile(t, root, ".github/workflows/cos-binary-release.yml", "name: release\n")
	writeFile(t, root, "scripts/install-goreleaser.sh", "#!/usr/bin/env bash\n")
	writeFile(t, root, "Formula/cognitive-os.rb", "class CognitiveOs < Formula\nend\n")
	writeFile(t, root, ".cognitive-os/cosd/runtime/cosd.pid", "12345\n")
	writeFile(t, root, ".cognitive-os/cosd/intents/one.json", "{}\n")
	writeFile(t, root, ".cognitive-os/cosd/intents/two.json", "{}\n")
	writeFile(t, root, ".cognitive-os/cosd/results/one.json", "{}\n")
	writeFile(t, root, "docs/reports/primitive-harness-coverage-latest.json", `{
  "summary": {
    "total_primitives": 12,
    "gaps": 3,
    "gaps_by_status": {"partial": 2},
    "surface_projected_or_wired": {"cli": 8, "tui": 1}
  }
}`)
	writeFile(t, root, ".cognitive-os/metrics/tui-actions.jsonl", `{"schema_version":"cos-tui-action-receipt.v1","action":"refresh","outcome":"ok"}`+"\n")

	snapshot := LoadSnapshot(root)

	if !snapshot.ReleaseReady {
		t.Fatalf("expected release readiness evidence to be complete: %#v", snapshot)
	}
	if snapshot.CosdStatus != "running-metadata-present" {
		t.Fatalf("cosd status = %q", snapshot.CosdStatus)
	}
	if snapshot.CosdQueueDepth != 1 {
		t.Fatalf("queue depth = %d, want 1", snapshot.CosdQueueDepth)
	}
	if snapshot.CoverageTotal != 12 || snapshot.CoverageGaps != 3 || snapshot.CoveragePartial != 2 {
		t.Fatalf("unexpected coverage summary: %#v", snapshot)
	}
	if strings.Join(snapshot.CoverageSurfaces, ",") != "cli,tui" {
		t.Fatalf("coverage surfaces = %#v", snapshot.CoverageSurfaces)
	}
	if snapshot.ReceiptTotal != 1 || snapshot.ReceiptLast != "refresh ok" {
		t.Fatalf("unexpected receipts summary: %#v", snapshot)
	}
}

func TestSnapshotTextIsReadOnlyOperatorSummary(t *testing.T) {
	root := t.TempDir()
	text := SnapshotText(root)

	for _, want := range []string{
		"Surface 5 Read-Only Snapshot",
		"## Overview",
		"## cosd",
		"## Coverage",
		"## Release",
		"## Receipts",
		"primitive coverage report missing",
	} {
		if !strings.Contains(text, want) {
			t.Fatalf("snapshot text missing %q:\n%s", want, text)
		}
	}
}

func TestModelSwitchesTabsAndQuits(t *testing.T) {
	model := NewModel(Snapshot{ProjectDir: "/example"})
	updated, cmd := model.Update(tea.KeyMsg{Type: tea.KeyRight})
	if cmd != nil {
		t.Fatalf("tab switch returned unexpected command")
	}
	m, ok := updated.(Model)
	if !ok {
		t.Fatalf("updated model type = %T", updated)
	}
	if m.Tab != 1 {
		t.Fatalf("tab = %d, want 1", m.Tab)
	}
	updated, cmd = m.Update(tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune{'q'}})
	if cmd == nil {
		t.Fatalf("quit key did not return a command")
	}
	if _, ok := updated.(Model); !ok {
		t.Fatalf("quit update type = %T", updated)
	}
}

func writeFile(t *testing.T, root, rel, content string) {
	t.Helper()
	path := filepath.Join(root, rel)
	if err := os.MkdirAll(filepath.Dir(path), 0755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(path, []byte(content), 0644); err != nil {
		t.Fatal(err)
	}
}

func TestModelQueuesCancelsAndConfirmsInteractiveAction(t *testing.T) {
	root := t.TempDir()
	writeFile(t, root, "scripts/cos-coverage", "#!/usr/bin/env bash\necho refreshed\n")
	if err := os.Chmod(filepath.Join(root, "scripts", "cos-coverage"), 0755); err != nil {
		t.Fatal(err)
	}
	model := NewModel(Snapshot{ProjectDir: root})

	updated, cmd := model.Update(tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune{'r'}})
	if cmd != nil {
		t.Fatalf("queueing action returned command")
	}
	queued := updated.(Model)
	if queued.PendingAction != "refresh-coverage" {
		t.Fatalf("pending action = %q", queued.PendingAction)
	}
	if !strings.Contains(queued.View(), "press c to confirm") {
		t.Fatalf("view did not render confirmation prompt:\n%s", queued.View())
	}

	updated, cmd = queued.Update(tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune{'x'}})
	if cmd != nil {
		t.Fatalf("cancel returned command")
	}
	cancelled := updated.(Model)
	if cancelled.PendingAction != "" {
		t.Fatalf("cancel did not clear pending action")
	}

	updated, cmd = queued.Update(tea.KeyMsg{Type: tea.KeyRunes, Runes: []rune{'c'}})
	running := updated.(Model)
	if running.RunningAction != "refresh-coverage" || cmd == nil {
		t.Fatalf("confirm did not start action: model=%#v cmd=%v", running, cmd)
	}
	msg := cmd()
	finished, ok := msg.(actionFinishedMsg)
	if !ok {
		t.Fatalf("command message type = %T", msg)
	}
	if !finished.Result.OK || finished.Result.Action != "refresh-coverage" {
		t.Fatalf("unexpected action result: %#v", finished.Result)
	}

	updated, cmd = running.Update(finished)
	if cmd != nil {
		t.Fatalf("finish returned command")
	}
	complete := updated.(Model)
	if complete.RunningAction != "" || complete.PendingAction != "" || complete.LastActionResult == nil {
		t.Fatalf("finish did not clear action state: %#v", complete)
	}
}
