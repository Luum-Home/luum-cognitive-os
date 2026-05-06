package tui

import (
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestRunActionRequiresAllowlistAndConfirmation(t *testing.T) {
	root := t.TempDir()
	fakeExecutable(t, root, "scripts/cos-coverage", "#!/usr/bin/env bash\necho refreshed\n")

	unknown := RunAction(root, "shell", ActionOptions{Confirm: true})
	if unknown.OK || unknown.Outcome != "rejected" || !strings.Contains(unknown.Reason, "not allowlisted") {
		t.Fatalf("unexpected unknown action result: %#v", unknown)
	}

	unconfirmed := RunAction(root, "refresh-coverage", ActionOptions{})
	if unconfirmed.OK || unconfirmed.Outcome != "rejected" || !strings.Contains(unconfirmed.Reason, "--confirm") {
		t.Fatalf("unexpected unconfirmed result: %#v", unconfirmed)
	}
	if fileExists(filepath.Join(root, ".cognitive-os", "metrics", "tui-actions.jsonl")) {
		t.Fatalf("unconfirmed action wrote a receipt")
	}
}

func TestRunActionWritesReceiptForConfirmedRefresh(t *testing.T) {
	root := t.TempDir()
	fakeExecutable(t, root, "scripts/cos-coverage", "#!/usr/bin/env bash\necho '{\"ok\":true}'\n")

	result := RunAction(root, "refresh-coverage", ActionOptions{Confirm: true})

	if !result.OK || result.Outcome != "success" {
		t.Fatalf("unexpected action result: %#v", result)
	}
	if result.Receipt == "" {
		t.Fatalf("receipt path was not recorded")
	}
	data, err := os.ReadFile(result.Receipt)
	if err != nil {
		t.Fatal(err)
	}
	var row map[string]any
	if err := json.Unmarshal([]byte(strings.TrimSpace(string(data))), &row); err != nil {
		t.Fatal(err)
	}
	if row["schema_version"] != "cos-tui-action-receipt.v1" || row["surface_id"] != "tui" || row["mode"] != "operable" {
		t.Fatalf("unexpected receipt row: %#v", row)
	}
}

func TestInboxAckRequiresMessageID(t *testing.T) {
	root := t.TempDir()
	result := RunAction(root, "inbox-ack", ActionOptions{Confirm: true})
	if result.OK || result.Outcome != "rejected" || !strings.Contains(result.Reason, "--message-id") {
		t.Fatalf("unexpected inbox ack result: %#v", result)
	}
}

func fakeExecutable(t *testing.T, root, rel, content string) {
	t.Helper()
	path := filepath.Join(root, rel)
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(path, []byte(content), 0o755); err != nil {
		t.Fatal(err)
	}
}
