package runner

import (
	"os"
	"path/filepath"
	"reflect"
	"testing"

	"luum-agent-os/cmd/cos-test/internal/config"
)

func TestPytestArgsWithOptionsUsesWrapperScalars(t *testing.T) {
	root := t.TempDir()
	scripts := filepath.Join(root, "scripts")
	if err := os.MkdirAll(scripts, 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(scripts, "pytest-with-summary.sh"), []byte("#!/usr/bin/env bash\n"), 0o755); err != nil {
		t.Fatal(err)
	}
	cfg := config.DefaultConfig()
	cfg.ProjectRoot = root
	r := NewPytestRunner(cfg)

	got := r.PytestArgsWithOptions([]string{"tests/unit/", "-m", "not benchmark"}, InvocationOptions{Workers: "auto", Lane: "unit"})
	want := []string{"bash", "scripts/pytest-with-summary.sh", "--workers", "auto", "--lane", "unit", "--", "tests/unit/", "-m", "not benchmark"}
	if !reflect.DeepEqual(got, want) {
		t.Fatalf("PytestArgsWithOptions() = %#v, want %#v", got, want)
	}
}

func TestPytestArgsWithOptionsFallsBackToPythonWhenWrapperMissing(t *testing.T) {
	cfg := config.DefaultConfig()
	cfg.ProjectRoot = t.TempDir()
	r := NewPytestRunner(cfg)

	got := r.PytestArgsWithOptions([]string{"tests/unit/"}, InvocationOptions{Workers: "auto", Lane: "unit"})
	want := []string{"python", "-m", "pytest", "tests/unit/"}
	if !reflect.DeepEqual(got, want) {
		t.Fatalf("fallback args = %#v, want %#v", got, want)
	}
}
