package cli

import (
	"os"
	"path/filepath"
	"reflect"
	"testing"

	"luum-agent-os/cmd/cos-test/internal/lanes"
)

const broadYAML = `lanes:
  unit:
    paths: [tests/unit/]
    parallel: true
  audit:
    paths: [tests/audit/]
    parallel: true
  integration:
    paths: [tests/integration/]
    parallel: marker
    marker_serial: docker
  behavior:
    paths: [tests/behavior/]
    parallel: false
  e2e:
    paths: [tests/e2e/]
    parallel: false
`

func TestBroadOrder_ParallelMarkerSerial(t *testing.T) {
	root := t.TempDir()
	if err := os.MkdirAll(filepath.Join(root, ".cognitive-os"), 0o755); err != nil {
		t.Fatal(err)
	}
	regPath := filepath.Join(root, ".cognitive-os", "test-lanes.yaml")
	if err := os.WriteFile(regPath, []byte(broadYAML), 0o644); err != nil {
		t.Fatal(err)
	}
	reg, err := lanes.Load(regPath)
	if err != nil {
		t.Fatal(err)
	}
	got := reg.BroadOrder()
	want := []string{"unit", "audit", "integration", "behavior", "e2e"}
	if !reflect.DeepEqual(got, want) {
		t.Errorf("BroadOrder = %v, want %v", got, want)
	}
}

func TestLaneAllPaths(t *testing.T) {
	root := t.TempDir()
	if err := os.MkdirAll(filepath.Join(root, ".cognitive-os"), 0o755); err != nil {
		t.Fatal(err)
	}
	regPath := filepath.Join(root, ".cognitive-os", "test-lanes.yaml")
	if err := os.WriteFile(regPath, []byte(broadYAML), 0o644); err != nil {
		t.Fatal(err)
	}
	reg, err := lanes.Load(regPath)
	if err != nil {
		t.Fatal(err)
	}
	order := reg.BroadOrder()
	got := laneAllPaths(reg, order)
	if len(got) != 5 {
		t.Errorf("expected 5 paths, got %d (%v)", len(got), got)
	}
}

func TestLaneOutcomeFailedAggregation(t *testing.T) {
	// Pure-data check: if any outcome is Failed, the failed count > 0.
	outs := []laneOutcome{
		{Lane: "unit", Failed: false},
		{Lane: "behavior", Failed: true},
		{Lane: "e2e", Failed: false},
	}
	failed := 0
	for _, o := range outs {
		if o.Failed {
			failed++
		}
	}
	if failed != 1 {
		t.Errorf("expected 1 failed, got %d", failed)
	}
}

func TestShouldSkipForNoDocker(t *testing.T) {
	cases := []struct {
		policy   string
		noDocker bool
		want     bool
	}{
		{policy: "forbidden", noDocker: true, want: false},
		{policy: "allowed", noDocker: true, want: true},
		{policy: "required", noDocker: true, want: true},
		{policy: "required", noDocker: false, want: false},
	}
	for _, tc := range cases {
		if got := shouldSkipForNoDocker(tc.policy, tc.noDocker); got != tc.want {
			t.Fatalf("shouldSkipForNoDocker(%q, %v) = %v, want %v", tc.policy, tc.noDocker, got, tc.want)
		}
	}
}

func TestCapWorkers(t *testing.T) {
	t.Setenv("COS_TEST_WORKERS_MAX", "2")
	cases := []struct {
		in   string
		want string
	}{
		{in: "auto", want: "2"},
		{in: "4", want: "2"},
		{in: "2", want: "2"},
		{in: "1", want: "1"},
		{in: "0", want: "0"},
	}
	for _, tc := range cases {
		if got := capWorkers(tc.in); got != tc.want {
			t.Fatalf("capWorkers(%q) = %q, want %q", tc.in, got, tc.want)
		}
	}
}

func TestCapWorkersInvalidEnvIsIgnored(t *testing.T) {
	t.Setenv("COS_TEST_WORKERS_MAX", "not-a-number")
	if got := capWorkers("4"); got != "4" {
		t.Fatalf("capWorkers with invalid env = %q, want 4", got)
	}
}

func TestLaneOutcomeSkippedAggregation(t *testing.T) {
	outs := []laneOutcome{
		{Lane: "unit", Failed: false},
		{Lane: "e2e", Skipped: true, Reason: "blocked by resource policy"},
	}
	failed := 0
	for _, o := range outs {
		if o.Failed {
			failed++
		}
	}
	if failed != 0 {
		t.Errorf("expected skipped lanes not to count as failed, got %d", failed)
	}
}

func TestPrintBroadSummaryOnlyBlocksBlockingPolicies(t *testing.T) {
	outs := []laneOutcome{
		{Lane: "unit", Failed: true, GateClass: lanes.GateReleaseBlocking, FailurePolicy: lanes.FailureBlock},
		{Lane: "integration", Failed: true, GateClass: lanes.GateEnvironmental, FailurePolicy: lanes.FailureWarn},
		{Lane: "quality", Skipped: true, GateClass: lanes.GateCostBearing, FailurePolicy: lanes.FailureWarn, Reason: "cost_policy=cost_bearing"},
	}
	if got := printBroadSummary(outs); got != 1 {
		t.Fatalf("blocking failures = %d, want 1", got)
	}
}
