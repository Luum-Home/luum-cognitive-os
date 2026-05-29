package cli

import (
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"
)

func TestRunQuarantineAuditUsesManifest(t *testing.T) {
	manifest := filepath.Join(t.TempDir(), "test-quarantine.yaml")
	body := `schema_version: test-quarantine.v1
quarantines:
  - id: cli-valid
    nodeid: tests/unit/test_cli.py::test_valid
    owner: test-owner
    reason: proves cli audit path
    expires: 2026-06-01
`
	if err := os.WriteFile(manifest, []byte(body), 0o644); err != nil {
		t.Fatal(err)
	}
	today, err := time.Parse(time.DateOnly, "2026-05-29")
	if err != nil {
		t.Fatal(err)
	}
	if err := runQuarantineAudit(manifest, today, false); err != nil {
		t.Fatalf("runQuarantineAudit returned error: %v", err)
	}
}

func TestRunQuarantineAuditFailsExpired(t *testing.T) {
	manifest := filepath.Join(t.TempDir(), "test-quarantine.yaml")
	body := `schema_version: test-quarantine.v1
quarantines:
  - id: cli-expired
    nodeid: tests/unit/test_cli.py::test_expired
    owner: test-owner
    reason: proves cli audit failure
    expires: 2026-05-28
`
	if err := os.WriteFile(manifest, []byte(body), 0o644); err != nil {
		t.Fatal(err)
	}
	today, err := time.Parse(time.DateOnly, "2026-05-29")
	if err != nil {
		t.Fatal(err)
	}
	err = runQuarantineAudit(manifest, today, false)
	if err == nil || !strings.Contains(err.Error(), "audit failed") {
		t.Fatalf("expected audit failure, got %v", err)
	}
}
