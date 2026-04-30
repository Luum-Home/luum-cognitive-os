package cli

import (
	"os"
	"path/filepath"
	"reflect"
	"sort"
	"testing"

	"luum-agent-os/cmd/cos-test/internal/config"
)

func newTestCfg(t *testing.T) *config.Config {
	t.Helper()
	root := t.TempDir()
	if err := os.MkdirAll(filepath.Join(root, "tests", "unit"), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.MkdirAll(filepath.Join(root, "tests", "integration"), 0o755); err != nil {
		t.Fatal(err)
	}
	cfg := config.DefaultConfig()
	cfg.ProjectRoot = root
	cfg.TestsDir = filepath.Join(root, "tests")
	return cfg
}

func writeFile(t *testing.T, p string) {
	t.Helper()
	if err := os.MkdirAll(filepath.Dir(p), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(p, []byte("x"), 0o644); err != nil {
		t.Fatal(err)
	}
}

func TestIsTestFile(t *testing.T) {
	cases := map[string]bool{
		"tests/unit/test_foo.py":        true,
		"tests/integration/test_x_y.py": true,
		"tests/unit/foo_test.py":        true,
		"scripts/foo.py":                false,
		"tests/unit/conftest.py":        false,
		"tests/unit/helpers.py":         false,
		"foo/test_bar.py":               false, // not under tests/
	}
	for in, want := range cases {
		if got := isTestFile(in); got != want {
			t.Errorf("isTestFile(%q) = %v, want %v", in, got, want)
		}
	}
}

func TestMapChangedToTests_SameNameHeuristic(t *testing.T) {
	cfg := newTestCfg(t)
	writeFile(t, filepath.Join(cfg.TestsDir, "unit", "test_foo.py"))
	writeFile(t, filepath.Join(cfg.TestsDir, "unit", "test_foo_extra.py"))
	writeFile(t, filepath.Join(cfg.TestsDir, "integration", "test_foo.py"))
	writeFile(t, filepath.Join(cfg.TestsDir, "unit", "test_bar.py"))

	got := mapChangedToTests(cfg, []string{"scripts/foo.py"})
	sort.Strings(got)
	want := []string{
		"tests/integration/test_foo.py",
		"tests/unit/test_foo.py",
		"tests/unit/test_foo_extra.py",
	}
	if !reflect.DeepEqual(got, want) {
		t.Errorf("mapChangedToTests = %v, want %v", got, want)
	}
}

func TestMapChangedToTests_TestFilePassesThrough(t *testing.T) {
	cfg := newTestCfg(t)
	writeFile(t, filepath.Join(cfg.TestsDir, "unit", "test_explicit.py"))

	got := mapChangedToTests(cfg, []string{"tests/unit/test_explicit.py"})
	if !reflect.DeepEqual(got, []string{"tests/unit/test_explicit.py"}) {
		t.Errorf("got %v", got)
	}
}

func TestMapChangedToTests_IgnoresNonPython(t *testing.T) {
	cfg := newTestCfg(t)
	got := mapChangedToTests(cfg, []string{"README.md", "docs/foo.txt"})
	if len(got) != 0 {
		t.Errorf("expected empty, got %v", got)
	}
}

func TestBuildFocusedPlan_Explicit(t *testing.T) {
	cfg := newTestCfg(t)
	plan, err := buildFocusedPlan(cfg, []string{"tests/unit/test_a.py"}, func(string) ([]string, error) {
		t.Fatal("diffFn must not be called for explicit paths")
		return nil, nil
	})
	if err != nil {
		t.Fatal(err)
	}
	if plan.Mode != "explicit" {
		t.Errorf("mode = %s", plan.Mode)
	}
	if !reflect.DeepEqual(plan.TestPaths, []string{"tests/unit/test_a.py"}) {
		t.Errorf("paths = %v", plan.TestPaths)
	}
	if plan.Workers != "auto" {
		t.Errorf("expected workers auto, got %q", plan.Workers)
	}
}

func TestBuildFocusedPlan_ForceSerialFocused(t *testing.T) {
	t.Setenv("COS_FORCE_SERIAL_LANES", "focused")
	cfg := newTestCfg(t)
	plan, err := buildFocusedPlan(cfg, []string{"tests/unit/test_a.py"}, func(string) ([]string, error) {
		t.Fatal("diffFn must not be called for explicit paths")
		return nil, nil
	})
	if err != nil {
		t.Fatal(err)
	}
	if plan.Workers != "0" {
		t.Errorf("expected forced serial workers 0, got %q", plan.Workers)
	}
}

func TestBuildFocusedPlan_FallbackOnDiffError(t *testing.T) {
	cfg := newTestCfg(t)
	plan, err := buildFocusedPlan(cfg, nil, func(string) ([]string, error) {
		return nil, errFake
	})
	if err != nil {
		t.Fatal(err)
	}
	if plan.Mode != "fallback" {
		t.Errorf("mode = %s", plan.Mode)
	}
	wantArgs := []string{"--lf", "--ff", "-x"}
	if !reflect.DeepEqual(plan.ExtraArgs, wantArgs) {
		t.Errorf("ExtraArgs = %v, want %v", plan.ExtraArgs, wantArgs)
	}
}

func TestBuildFocusedPlan_FallbackOnNoMatches(t *testing.T) {
	cfg := newTestCfg(t)
	plan, err := buildFocusedPlan(cfg, nil, func(string) ([]string, error) {
		return []string{"docs/random.md"}, nil
	})
	if err != nil {
		t.Fatal(err)
	}
	if plan.Mode != "fallback" {
		t.Errorf("mode = %s", plan.Mode)
	}
}

func TestBuildFocusedPlan_TestmonPreferred(t *testing.T) {
	cfg := newTestCfg(t)
	tm := filepath.Join(cfg.ProjectRoot, ".cognitive-os", "cache", "testmon")
	if err := os.MkdirAll(tm, 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(tm, ".testmondata"), []byte("x"), 0o644); err != nil {
		t.Fatal(err)
	}
	writeFile(t, filepath.Join(cfg.TestsDir, "unit", "test_foo.py"))

	plan, err := buildFocusedPlan(cfg, nil, func(string) ([]string, error) {
		return []string{"scripts/foo.py"}, nil
	})
	if err != nil {
		t.Fatal(err)
	}
	if plan.Mode != "testmon" {
		t.Errorf("mode = %s, want testmon", plan.Mode)
	}
	if plan.Workers != "auto" || !containsString(plan.ExtraArgs, "--testmon") {
		t.Errorf("expected workers auto + --testmon, got workers=%q args=%v", plan.Workers, plan.ExtraArgs)
	}
}

func TestBuildFocusedPlan_MappedHappy(t *testing.T) {
	cfg := newTestCfg(t)
	writeFile(t, filepath.Join(cfg.TestsDir, "unit", "test_foo.py"))

	plan, err := buildFocusedPlan(cfg, nil, func(string) ([]string, error) {
		return []string{"scripts/foo.py"}, nil
	})
	if err != nil {
		t.Fatal(err)
	}
	if plan.Mode != "mapped" {
		t.Errorf("mode = %s", plan.Mode)
	}
	if !reflect.DeepEqual(plan.TestPaths, []string{"tests/unit/test_foo.py"}) {
		t.Errorf("paths = %v", plan.TestPaths)
	}
}

func TestBuildFocusedPlan_ChangedFilesOverrideNoTestmon(t *testing.T) {
	cfg := newTestCfg(t)
	writeFile(t, filepath.Join(cfg.TestsDir, "unit", "test_foo.py"))
	tm := filepath.Join(cfg.ProjectRoot, ".cognitive-os", "cache", "testmon")
	if err := os.MkdirAll(tm, 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(tm, ".testmondata"), []byte("x"), 0o644); err != nil {
		t.Fatal(err)
	}

	plan, err := buildFocusedPlanWithOptions(
		cfg,
		nil,
		func(string) ([]string, error) {
			t.Fatal("diffFn must not be called when changed files are provided")
			return nil, nil
		},
		focusedPlanBuildOptions{UseTestmon: false, ChangedFiles: []string{"lib/foo.py"}},
	)
	if err != nil {
		t.Fatal(err)
	}
	if plan.Mode != "mapped" {
		t.Fatalf("mode = %s, want mapped", plan.Mode)
	}
	if !reflect.DeepEqual(plan.TestPaths, []string{"tests/unit/test_foo.py"}) {
		t.Fatalf("paths = %v", plan.TestPaths)
	}
}

// --- helpers ---

var errFake = errFakeT{}

type errFakeT struct{}

func (errFakeT) Error() string { return "fake diff error" }

func containsPair(xs []string, a, b string) bool {
	for i := 0; i+1 < len(xs); i++ {
		if xs[i] == a && xs[i+1] == b {
			return true
		}
	}
	return false
}

func containsString(xs []string, s string) bool {
	for _, x := range xs {
		if x == s {
			return true
		}
	}
	return false
}
