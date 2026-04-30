package cli

import (
	"os"
	"path/filepath"
	"strings"
	"testing"

	"luum-agent-os/cmd/cos-test/internal/config"
)

func writeRegistry(t *testing.T, root, body string) {
	t.Helper()
	dir := filepath.Join(root, ".cognitive-os")
	if err := os.MkdirAll(dir, 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(dir, "test-lanes.yaml"), []byte(body), 0o644); err != nil {
		t.Fatal(err)
	}
}

const clusterYAML = `lanes:
  unit:
    paths: [tests/unit/]
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

func TestBuildClusterPlan_Parallel(t *testing.T) {
	cfg := config.DefaultConfig()
	cfg.ProjectRoot = t.TempDir()
	writeRegistry(t, cfg.ProjectRoot, clusterYAML)

	plan, err := buildClusterPlan(cfg, "unit")
	if err != nil {
		t.Fatal(err)
	}
	if len(plan.Invokes) != 1 {
		t.Fatalf("parallel lane should produce 1 invocation, got %d", len(plan.Invokes))
	}
	if !containsPair(plan.Invokes[0].Args, "-n", "auto") {
		t.Errorf("missing -n auto: %v", plan.Invokes[0].Args)
	}
	if !strings.Contains(plan.Workers, "parallel-safe") {
		t.Errorf("workers = %s", plan.Workers)
	}
}

func TestBuildClusterPlan_Serial(t *testing.T) {
	cfg := config.DefaultConfig()
	cfg.ProjectRoot = t.TempDir()
	writeRegistry(t, cfg.ProjectRoot, clusterYAML)

	plan, err := buildClusterPlan(cfg, "behavior")
	if err != nil {
		t.Fatal(err)
	}
	if len(plan.Invokes) != 1 {
		t.Fatalf("serial lane should produce 1 invocation, got %d", len(plan.Invokes))
	}
	if containsPair(plan.Invokes[0].Args, "-n", "auto") {
		t.Errorf("serial lane must not pass -n auto: %v", plan.Invokes[0].Args)
	}
	if !strings.Contains(plan.Reason, "hook chain state") {
		t.Errorf("expected stateful reason, got %s", plan.Reason)
	}
}

func TestBuildClusterPlan_MarkerSplit(t *testing.T) {
	cfg := config.DefaultConfig()
	cfg.ProjectRoot = t.TempDir()
	writeRegistry(t, cfg.ProjectRoot, clusterYAML)

	plan, err := buildClusterPlan(cfg, "integration")
	if err != nil {
		t.Fatal(err)
	}
	if len(plan.Invokes) != 2 {
		t.Fatalf("marker lane should produce 2 invocations, got %d", len(plan.Invokes))
	}
	// First invocation should run "not <marker>" with -n auto.
	first := plan.Invokes[0].Args
	if !sliceContains(first, "-m") || !sliceContains(first, "not docker") {
		t.Errorf("first invocation missing -m 'not docker': %v", first)
	}
	if !containsPair(first, "-n", "auto") {
		t.Errorf("first invocation missing -n auto: %v", first)
	}
	// Second invocation runs marker serial.
	second := plan.Invokes[1].Args
	if !sliceContains(second, "docker") {
		t.Errorf("second invocation missing marker: %v", second)
	}
	if containsPair(second, "-n", "auto") {
		t.Errorf("second invocation must be serial: %v", second)
	}
}

func TestBuildClusterPlan_UnknownLane(t *testing.T) {
	cfg := config.DefaultConfig()
	cfg.ProjectRoot = t.TempDir()
	writeRegistry(t, cfg.ProjectRoot, clusterYAML)

	_, err := buildClusterPlan(cfg, "ghost")
	if err == nil {
		t.Fatal("expected error for unknown lane")
	}
	if !strings.Contains(err.Error(), "unknown lane") {
		t.Errorf("unexpected error: %v", err)
	}
}

func TestBuildClusterPlan_MissingRegistry(t *testing.T) {
	cfg := config.DefaultConfig()
	cfg.ProjectRoot = t.TempDir()
	_, err := buildClusterPlan(cfg, "unit")
	if err == nil {
		t.Fatal("expected error when registry missing")
	}
}

func sliceContains(xs []string, target string) bool {
	for _, x := range xs {
		if x == target {
			return true
		}
	}
	return false
}
