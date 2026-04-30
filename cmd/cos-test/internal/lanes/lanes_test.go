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

// --- Optional lane semantics (regression for broad-default bug) -------------

const optionalSampleYAML = `lanes:
  unit:
    paths: [tests/unit/]
    parallel: true
  audit:
    paths: [tests/audit/]
    parallel: true
  behavior:
    paths: [tests/behavior/]
    parallel: false
  arena:
    paths: [tests/arena/]
    parallel: false
    optional: true
  benchmark:
    paths: [tests/benchmark/]
    parallel: false
    optional: true
  quality:
    paths: [tests/quality/]
    parallel: false
    optional: true
`

func TestParse_OptionalField(t *testing.T) {
	reg, err := Parse(strings.NewReader(optionalSampleYAML))
	if err != nil {
		t.Fatalf("parse: %v", err)
	}
	if l, _ := reg.Get("arena"); !l.Optional {
		t.Errorf("arena.Optional = false, want true")
	}
	if l, _ := reg.Get("unit"); l.Optional {
		t.Errorf("unit.Optional = true, want false (no field set)")
	}
}

func TestBroadOrder_ExcludesOptionalByDefault(t *testing.T) {
	reg, err := Parse(strings.NewReader(optionalSampleYAML))
	if err != nil {
		t.Fatal(err)
	}
	got := reg.BroadOrder()
	for _, name := range got {
		if name == "arena" || name == "benchmark" || name == "quality" {
			t.Errorf("BroadOrder() returned optional lane %q (got %v)", name, got)
		}
	}
	if len(got) != 3 {
		t.Errorf("BroadOrder() = %v (len %d), want 3 non-optional lanes", got, len(got))
	}
}

func TestBroadOrderWith_IncludesOptionalWhenAsked(t *testing.T) {
	reg, err := Parse(strings.NewReader(optionalSampleYAML))
	if err != nil {
		t.Fatal(err)
	}
	got := reg.BroadOrderWith(true)
	if len(got) != 6 {
		t.Errorf("BroadOrderWith(true) = %v (len %d), want all 6 lanes", got, len(got))
	}
	// Spot-check arena present.
	found := false
	for _, name := range got {
		if name == "arena" {
			found = true
			break
		}
	}
	if !found {
		t.Errorf("arena missing from includeOptional run: %v", got)
	}
}

func TestOptionalNames(t *testing.T) {
	reg, err := Parse(strings.NewReader(optionalSampleYAML))
	if err != nil {
		t.Fatal(err)
	}
	got := reg.OptionalNames()
	want := []string{"arena", "benchmark", "quality"}
	if len(got) != len(want) {
		t.Fatalf("OptionalNames() = %v, want %v", got, want)
	}
	for i, n := range want {
		if got[i] != n {
			t.Errorf("OptionalNames()[%d] = %q, want %q", i, got[i], n)
		}
	}
}

func TestParse_OptionalInvalidValue(t *testing.T) {
	bad := `lanes:
  unit:
    paths: [tests/unit/]
    parallel: true
    optional: maybe
`
	if _, err := Parse(strings.NewReader(bad)); err == nil {
		t.Error("expected error for invalid optional value")
	}
}
