package banner

import (
	"bytes"
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"
)

func TestRender_FiveLinesAndPrefix(t *testing.T) {
	info := Info{
		Subcommand: "cluster",
		Lane:       "audit",
		Paths:      []string{"tests/audit/"},
		TestCount:  87,
		Workers:    "auto:8 (parallel-safe per registry)",
		Reason:     "lane parallel=true",
		ETA:        "~18s (p50 of last 10 audit runs, +/- 4s)",
		KillSwitch: "COS_FORCE_SERIAL_LANES=audit",
	}
	out := Render(info)
	lines := strings.Split(strings.TrimRight(out, "\n"), "\n")
	if got := len(lines); got != 5 {
		t.Fatalf("expected 5 lines, got %d:\n%s", got, out)
	}
	for i, ln := range lines {
		if !strings.HasPrefix(ln, "[cos-test cluster]") {
			t.Errorf("line %d missing prefix: %q", i, ln)
		}
	}
	if !strings.Contains(out, "lane=audit") || !strings.Contains(out, "tests=87") {
		t.Errorf("missing lane/tests headline: %s", out)
	}
	if !strings.Contains(out, "tests/audit/") {
		t.Errorf("missing path: %s", out)
	}
	if !strings.Contains(out, "kill-switch: COS_FORCE_SERIAL_LANES=audit") {
		t.Errorf("missing kill-switch: %s", out)
	}
}

func TestRender_EmptyDefaults(t *testing.T) {
	out := Render(Info{Subcommand: "broad", TestCount: 0, Workers: "n/a"})
	if !strings.Contains(out, "lane=(unset)") {
		t.Errorf("expected (unset) lane fallback: %s", out)
	}
	if !strings.Contains(out, "paths: (none)") {
		t.Errorf("expected (none) paths fallback: %s", out)
	}
	if !strings.Contains(out, "eta: unknown (no history)") {
		t.Errorf("expected unknown ETA fallback: %s", out)
	}
}

func TestPrint_WritesToWriter(t *testing.T) {
	var buf bytes.Buffer
	Print(&buf, Info{Subcommand: "focused", Lane: "auto", TestCount: 3, Workers: "auto:8"})
	if !strings.Contains(buf.String(), "[cos-test focused]") {
		t.Errorf("Print missing prefix: %s", buf.String())
	}
}

func TestFormatETA_Empty(t *testing.T) {
	if got := FormatETA("audit", nil); got != "unknown (no history)" {
		t.Errorf("expected unknown for empty, got %q", got)
	}
}

func TestFormatETA_Median(t *testing.T) {
	durations := []float64{10, 12, 14, 18, 20}
	got := FormatETA("audit", durations)
	if !strings.Contains(got, "~14s") {
		t.Errorf("expected p50=14, got %q", got)
	}
	if !strings.Contains(got, "of last 5 audit runs") {
		t.Errorf("expected count=5 in %q", got)
	}
	if !strings.Contains(got, "+/- ") {
		t.Errorf("expected spread suffix in %q", got)
	}
}

func TestFormatETA_SingleSample(t *testing.T) {
	got := FormatETA("unit", []float64{7})
	if !strings.Contains(got, "~7s") {
		t.Errorf("expected ~7s, got %q", got)
	}
}

func TestPercentile_LinearInterpolation(t *testing.T) {
	cases := []struct {
		in   []float64
		p    float64
		want float64
	}{
		{[]float64{1, 2, 3, 4, 5}, 50, 3},
		{[]float64{1, 2}, 50, 1.5},
		{[]float64{}, 50, 0},
		{[]float64{42}, 99, 42},
	}
	for _, c := range cases {
		got := percentile(c.in, c.p)
		if got != c.want {
			t.Errorf("percentile(%v, %v) = %v, want %v", c.in, c.p, got, c.want)
		}
	}
}

func TestAggregateETA_MissingDir(t *testing.T) {
	got := AggregateETA(filepath.Join(t.TempDir(), "does-not-exist"), "audit", 5)
	if got != "unknown (no history)" {
		t.Errorf("expected unknown for missing dir, got %q", got)
	}
}

func TestAggregateETA_AttributesByDirName(t *testing.T) {
	root := t.TempDir()
	// Create two run dirs with synthetic timing for the "audit" lane and one
	// unrelated dir; the unrelated one must be ignored.
	mustMakeRun(t, root, "20260429T120000Z-tests-audit-q-ra", 12*time.Second)
	mustMakeRun(t, root, "20260429T130000Z-tests-audit-q-ra", 18*time.Second)
	mustMakeRun(t, root, "20260429T140000Z-tests-unit-q-ra", 5*time.Second)

	got := AggregateETA(root, "audit", 5)
	if !strings.Contains(got, "of last 2 audit runs") {
		t.Errorf("expected 2 audit runs, got %q", got)
	}
}

func TestAggregateETA_AttributesByMetadata(t *testing.T) {
	root := t.TempDir()
	dir := filepath.Join(root, "20260429T150000Z-misc-slug")
	if err := os.MkdirAll(dir, 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(dir, "metadata.txt"),
		[]byte("args=tests/audit/ -m not docker\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	// Touch a file so duration > 0.
	out := filepath.Join(dir, "summary.txt")
	if err := os.WriteFile(out, []byte("ok"), 0o644); err != nil {
		t.Fatal(err)
	}
	mtime := time.Now().Add(2 * time.Second)
	if err := os.Chtimes(out, mtime, mtime); err != nil {
		t.Fatal(err)
	}

	got := AggregateETA(root, "audit", 5)
	if got == "unknown (no history)" {
		t.Errorf("expected metadata-based attribution, got %q", got)
	}
}

// mustMakeRun creates a run directory with one summary file whose mtime is
// `dur` after the directory mtime, so durationFromRunDir returns ~dur.
func mustMakeRun(t *testing.T, root, name string, dur time.Duration) {
	t.Helper()
	dir := filepath.Join(root, name)
	if err := os.MkdirAll(dir, 0o755); err != nil {
		t.Fatal(err)
	}
	dirInfo, err := os.Stat(dir)
	if err != nil {
		t.Fatal(err)
	}
	out := filepath.Join(dir, "summary.txt")
	if err := os.WriteFile(out, []byte("ok"), 0o644); err != nil {
		t.Fatal(err)
	}
	mtime := dirInfo.ModTime().Add(dur)
	if err := os.Chtimes(out, mtime, mtime); err != nil {
		t.Fatal(err)
	}
}
