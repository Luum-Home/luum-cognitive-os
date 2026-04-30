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
