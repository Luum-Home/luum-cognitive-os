package runner

import (
	"encoding/json"
	"os"
	"path/filepath"
	"reflect"
	"strings"
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

func TestPytestArgsWithOptionsPassesResourceMetadataScalars(t *testing.T) {
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

	got := r.PytestArgsWithOptions(
		[]string{"tests/unit/", "-m", "not benchmark"},
		InvocationOptions{
			Workers:        "0",
			Lane:           "unit",
			TimeoutSeconds: 180,
			DockerPolicy:   "forbidden",
			CostPolicy:     "free_only",
			ArtifactPolicy: "keep_summary",
		},
	)
	want := []string{
		"bash", "scripts/pytest-with-summary.sh",
		"--workers", "0",
		"--lane", "unit",
		"--timeout-seconds", "180",
		"--docker-policy", "forbidden",
		"--cost-policy", "free_only",
		"--artifact-policy", "keep_summary",
		"--",
		"tests/unit/", "-m", "not benchmark",
	}
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

func TestRawInvocationWithOptionsEnforcesTimeout(t *testing.T) {
	root := t.TempDir()
	scripts := filepath.Join(root, "scripts")
	if err := os.MkdirAll(scripts, 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(scripts, "pytest-with-summary.sh"), []byte("#!/usr/bin/env bash\nsleep 2\n"), 0o755); err != nil {
		t.Fatal(err)
	}
	cfg := config.DefaultConfig()
	cfg.ProjectRoot = root
	r := NewPytestRunner(cfg)
	reports := t.TempDir()
	t.Setenv("COS_TEST_REPORT_DIR", reports)

	err := r.RawInvocationWithOptions(
		[]string{"tests/unit/"},
		InvocationOptions{
			Lane:           "timeout-test",
			Workers:        "0",
			TimeoutSeconds: 1,
			DockerPolicy:   "forbidden",
			CostPolicy:     "free_only",
			ArtifactPolicy: "keep_summary",
		},
	)
	if err == nil {
		t.Fatal("expected timeout error")
	}
	if !strings.Contains(err.Error(), "RESOURCE_EXHAUSTED") {
		t.Fatalf("expected RESOURCE_EXHAUSTED error, got %v", err)
	}
	raw, readErr := os.ReadFile(filepath.Join(reports, "latest", "resource-policy.json"))
	if readErr != nil {
		t.Fatalf("expected timeout resource-policy artifact: %v", readErr)
	}
	var artifact map[string]any
	if err := json.Unmarshal(raw, &artifact); err != nil {
		t.Fatal(err)
	}
	if artifact["outcome"] != "resource_exhausted" {
		t.Fatalf("outcome = %#v, want resource_exhausted", artifact["outcome"])
	}
}
