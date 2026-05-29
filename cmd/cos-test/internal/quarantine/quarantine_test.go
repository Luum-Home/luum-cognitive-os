package quarantine

import (
	"strings"
	"testing"
	"time"
)

func auditManifest(t *testing.T, body string, today string) []Finding {
	t.Helper()
	m, err := Parse(strings.NewReader(body))
	if err != nil {
		t.Fatalf("Parse returned error: %v", err)
	}
	parsedToday, err := time.Parse(time.DateOnly, today)
	if err != nil {
		t.Fatal(err)
	}
	return Audit(m, parsedToday)
}

func TestAuditValidManifestPasses(t *testing.T) {
	findings := auditManifest(t, `schema_version: test-quarantine.v1
quarantines:
  - id: flaky-network-001
    nodeid: tests/integration/test_network.py::test_retries
    owner: sre-platform
    reason: "intermittent upstream sandbox timeout"
    expires: 2026-06-30
    issue: https://example.invalid/issues/1
`, "2026-05-29")
	if len(findings) != 0 {
		t.Fatalf("expected no findings, got %#v", findings)
	}
}

func TestAuditEmptyManifestPasses(t *testing.T) {
	findings := auditManifest(t, `schema_version: test-quarantine.v1
quarantines: []
`, "2026-05-29")
	if len(findings) != 0 {
		t.Fatalf("expected no findings, got %#v", findings)
	}
}

func TestAuditRequiresOwnerReasonAndExpiration(t *testing.T) {
	findings := auditManifest(t, `schema_version: test-quarantine.v1
quarantines:
  - id: missing-metadata
    nodeid: tests/unit/test_example.py::test_case
`, "2026-05-29")
	wantFields := map[string]bool{"owner": true, "reason": true, "expires": true}
	for _, finding := range findings {
		delete(wantFields, finding.Field)
	}
	if len(wantFields) != 0 {
		t.Fatalf("missing required-field findings: %v; got %#v", wantFields, findings)
	}
}

func TestAuditFailsExpiredQuarantine(t *testing.T) {
	findings := auditManifest(t, `schema_version: test-quarantine.v1
quarantines:
  - id: expired-entry
    nodeid: tests/unit/test_example.py::test_case
    owner: sre-platform
    reason: deterministic reproduction pending
    expires: 2026-05-28
`, "2026-05-29")
	if len(findings) != 1 {
		t.Fatalf("expected one finding, got %#v", findings)
	}
	if findings[0].Field != "expires" || !strings.Contains(findings[0].Message, "expired on 2026-05-28") {
		t.Fatalf("unexpected finding: %#v", findings[0])
	}
}

func TestAuditFailsMalformedExpiration(t *testing.T) {
	findings := auditManifest(t, `schema_version: test-quarantine.v1
quarantines:
  - id: malformed-date
    nodeid: tests/unit/test_example.py::test_case
    owner: sre-platform
    reason: deterministic reproduction pending
    expires: 2026/06/01
`, "2026-05-29")
	if len(findings) != 1 {
		t.Fatalf("expected one finding, got %#v", findings)
	}
	if findings[0].Field != "expires" || !strings.Contains(findings[0].Message, "YYYY-MM-DD") {
		t.Fatalf("unexpected finding: %#v", findings[0])
	}
}

func TestParseRejectsMalformedYAML(t *testing.T) {
	_, err := Parse(strings.NewReader(`schema_version: test-quarantine.v1
quarantines:
   - id: bad-indent
`))
	if err == nil {
		t.Fatal("expected parse error")
	}
}
