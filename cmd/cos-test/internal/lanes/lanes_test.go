package lanes

import (
	"strings"
	"testing"
)

const sampleYAML = `# header comment
lanes:
  unit:
    paths: [tests/unit/]
    parallel: true
    stateful_reason: ""
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
    stateful_reason: "hook chain state"
`

func TestParse_BasicSchema(t *testing.T) {
	reg, err := Parse(strings.NewReader(sampleYAML))
	if err != nil {
		t.Fatalf("parse: %v", err)
	}
	if got := reg.Names(); len(got) != 4 {
		t.Fatalf("expected 4 lanes, got %v", got)
	}
	unit, ok := reg.Get("unit")
	if !ok {
		t.Fatal("unit lane missing")
	}
	if unit.Parallel != ParallelTrue {
		t.Errorf("unit parallel = %v, want true", unit.Parallel)
	}
	if len(unit.Paths) != 1 || unit.Paths[0] != "tests/unit/" {
		t.Errorf("unit paths = %v", unit.Paths)
	}

	integ, _ := reg.Get("integration")
	if integ.Parallel != ParallelMarker {
		t.Errorf("integration parallel = %v, want marker", integ.Parallel)
	}
	if integ.MarkerSerial != "docker" {
		t.Errorf("integration marker_serial = %q", integ.MarkerSerial)
	}

	beh, _ := reg.Get("behavior")
	if beh.Parallel != ParallelFalse {
		t.Errorf("behavior parallel = %v, want false", beh.Parallel)
	}
	if beh.StatefulReason != "hook chain state" {
		t.Errorf("behavior stateful_reason = %q", beh.StatefulReason)
	}
}

func TestParse_BroadOrder(t *testing.T) {
	reg, err := Parse(strings.NewReader(sampleYAML))
	if err != nil {
		t.Fatal(err)
	}
	got := reg.BroadOrder()
	want := []string{"unit", "audit", "integration", "behavior"}
	if len(got) != len(want) {
		t.Fatalf("BroadOrder len: got %v want %v", got, want)
	}
	for i := range want {
		if got[i] != want[i] {
			t.Errorf("BroadOrder[%d] = %s, want %s (full: %v)", i, got[i], want[i], got)
		}
	}
}

func TestParse_UnknownParallel_Errors(t *testing.T) {
	bad := `lanes:
  weird:
    paths: [tests/x/]
    parallel: maybe
`
	_, err := Parse(strings.NewReader(bad))
	if err == nil {
		t.Error("expected error for unknown parallel value")
	}
}

func TestParse_NoLanes_Errors(t *testing.T) {
	_, err := Parse(strings.NewReader("# nothing here\n"))
	if err == nil {
		t.Error("expected error when registry is empty")
	}
}

func TestParse_IgnoresUnknownTopLevel(t *testing.T) {
	yaml := `version: 1
lanes:
  unit:
    paths: [tests/unit/]
    parallel: true
extra:
  ignored: yes
`
	_, err := Parse(strings.NewReader(yaml))
	if err != nil {
		t.Errorf("did not tolerate unknown top-level keys: %v", err)
	}
}

func TestParse_StripsTrailingComment(t *testing.T) {
	yaml := `lanes:
  unit:
    paths: [tests/unit/]   # path list
    parallel: true         # safe
`
	reg, err := Parse(strings.NewReader(yaml))
	if err != nil {
		t.Fatal(err)
	}
	u, _ := reg.Get("unit")
	if u.Parallel != ParallelTrue {
		t.Errorf("comment leaked into value: %+v", u)
	}
	if len(u.Paths) != 1 || u.Paths[0] != "tests/unit/" {
		t.Errorf("paths = %v", u.Paths)
	}
}
