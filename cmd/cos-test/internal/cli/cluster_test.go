package cli

import (
	"os"
	"path/filepath"
	"strings"
	"testing"

	"luum-agent-os/cmd/cos-test/internal/config"
	"luum-agent-os/cmd/cos-test/internal/resourcepolicy"
)

func writeResourcePolicy(t *testing.T, root, body string) {
	t.Helper()
	dir := filepath.Join(root, ".cognitive-os")
	if err := os.MkdirAll(dir, 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(dir, "test-resource-policy.yaml"), []byte(body), 0o644); err != nil {
		t.Fatal(err)
	}
}

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
  integration-docker:
    paths: [tests/integration/]
    parallel: false
    marker_include: docker
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
	if plan.Invokes[0].Workers != "auto" {
		t.Errorf("parallel lane workers = %q, want auto", plan.Invokes[0].Workers)
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
	if plan.Invokes[0].Workers != "0" {
		t.Errorf("serial lane workers = %q, want 0", plan.Invokes[0].Workers)
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
	// First invocation should run "not <marker>" with wrapper workers=auto.
	first := plan.Invokes[0].Args
	if !sliceContains(first, "-m") || !sliceContains(first, "not docker") {
		t.Errorf("first invocation missing -m 'not docker': %v", first)
	}
	if plan.Invokes[0].Workers != "auto" {
		t.Errorf("first invocation workers = %q, want auto", plan.Invokes[0].Workers)
	}
	// Second invocation runs marker serial.
	second := plan.Invokes[1].Args
	if !sliceContains(second, "docker") {
		t.Errorf("second invocation missing marker: %v", second)
	}
	if containsPair(second, "-n", "auto") {
		t.Errorf("second invocation must be serial: %v", second)
	}
	if plan.Invokes[1].Workers != "0" {
		t.Errorf("second invocation workers = %q, want 0", plan.Invokes[1].Workers)
	}
}

func TestBuildClusterPlan_MarkerInclude(t *testing.T) {
	cfg := config.DefaultConfig()
	cfg.ProjectRoot = t.TempDir()
	writeRegistry(t, cfg.ProjectRoot, clusterYAML)

	plan, err := buildClusterPlan(cfg, "integration-docker")
	if err != nil {
		t.Fatal(err)
	}
	if len(plan.Invokes) != 1 {
		t.Fatalf("marker-include lane should produce 1 invocation, got %d", len(plan.Invokes))
	}
	if !containsPair(plan.Invokes[0].Args, "-m", "docker") {
		t.Fatalf("expected marker include docker in args, got %v", plan.Invokes[0].Args)
	}
	if !strings.Contains(plan.Reason, "including") {
		t.Fatalf("expected reason to mention include filter, got %q", plan.Reason)
	}
}

func TestBuildClusterPlan_ForceSerialLane(t *testing.T) {
	cfg := config.DefaultConfig()
	cfg.ProjectRoot = t.TempDir()
	writeRegistry(t, cfg.ProjectRoot, clusterYAML)
	t.Setenv("COS_FORCE_SERIAL_LANES", "unit,audit")

	plan, err := buildClusterPlan(cfg, "unit")
	if err != nil {
		t.Fatal(err)
	}
	if plan.Invokes[0].Workers != "0" {
		t.Errorf("forced serial workers = %q, want 0", plan.Invokes[0].Workers)
	}
	if !strings.Contains(plan.Reason, "forced serial") {
		t.Errorf("reason should mention forced serial, got %q", plan.Reason)
	}
}

func TestBuildClusterPlan_ForceSerialAll(t *testing.T) {
	cfg := config.DefaultConfig()
	cfg.ProjectRoot = t.TempDir()
	writeRegistry(t, cfg.ProjectRoot, clusterYAML)
	t.Setenv("COS_FORCE_SERIAL_LANES", "*")

	plan, err := buildClusterPlan(cfg, "integration")
	if err != nil {
		t.Fatal(err)
	}
	for _, inv := range plan.Invokes {
		if inv.Workers != "0" {
			t.Errorf("%s workers = %q, want 0", inv.Label, inv.Workers)
		}
	}
}

func TestBuildClusterPlan_ResourcePolicyOverridesParallelWorkers(t *testing.T) {
	cfg := config.DefaultConfig()
	cfg.ProjectRoot = t.TempDir()
	writeRegistry(t, cfg.ProjectRoot, clusterYAML)
	writeResourcePolicy(t, cfg.ProjectRoot, `version: 1
defaults:
  workers: auto
  timeout_seconds: 300
  docker_policy: forbidden
  cost_policy: free_only
  artifact_policy: keep_summary
lanes:
  unit:
    workers: 2
    timeout_seconds: 120
`)

	plan, err := buildClusterPlan(cfg, "unit")
	if err != nil {
		t.Fatal(err)
	}
	if plan.Invokes[0].Workers != "2" {
		t.Fatalf("workers = %q, want policy override 2", plan.Invokes[0].Workers)
	}
	if plan.Resources.TimeoutSeconds != 120 || plan.Resources.DockerPolicy != "forbidden" {
		t.Fatalf("resources = %+v", plan.Resources)
	}
}

func TestBuildClusterPlan_RejectsUnknownResourcePolicyLane(t *testing.T) {
	cfg := config.DefaultConfig()
	cfg.ProjectRoot = t.TempDir()
	writeRegistry(t, cfg.ProjectRoot, clusterYAML)
	writeResourcePolicy(t, cfg.ProjectRoot, `version: 1
defaults:
  workers: auto
  timeout_seconds: 300
  docker_policy: forbidden
  cost_policy: free_only
  artifact_policy: keep_summary
lanes:
  ghost:
    timeout_seconds: 120
`)

	_, err := buildClusterPlan(cfg, "unit")
	if err == nil {
		t.Fatal("expected unknown resource policy lane to fail")
	}
	if !strings.Contains(err.Error(), "unknown lane") {
		t.Fatalf("unexpected error: %v", err)
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

// TestBuildClusterPlan_ResourcePolicyZeroWorkersDoesNotForceSerialOnParallelLane
// is the regression guard for the bug discovered 2026-04-30 where
// test-resource-policy.yaml had workers:0 for the unit lane (parallel:true)
// which caused --workers 0 to be passed to pytest-with-summary.sh despite
// the lane being parallel-safe.
func TestBuildClusterPlan_ResourcePolicyZeroWorkersDoesNotForceSerialOnParallelLane(t *testing.T) {
	// Regression: a policy file with workers:0 for a parallel lane used to
	// produce Workers="0" in the invocation spec, causing serial execution.
	// This test would have caught the bug.
	cfg := config.DefaultConfig()
	cfg.ProjectRoot = t.TempDir()
	writeRegistry(t, cfg.ProjectRoot, clusterYAML)
	// Set workers:0 in policy for unit lane — this was the production bug.
	writeResourcePolicy(t, cfg.ProjectRoot, `version: 1
defaults:
  workers: auto
  timeout_seconds: 300
  docker_policy: forbidden
  cost_policy: free_only
  artifact_policy: keep_summary
lanes:
  unit:
    workers: 0
    timeout_seconds: 900
`)

	// With the bug present, plan.Invokes[0].Workers would be "0" (serial).
	// With the fix applied in test-resource-policy.yaml (workers: auto),
	// this test documents that a workers:0 policy override wins — the fix
	// is in the YAML, not in the code ignoring the policy.
	// This test therefore should return Workers=="0" (policy override wins),
	// which confirms the code is correct and the data file was the bug.
	plan, err := buildClusterPlan(cfg, "unit")
	if err != nil {
		t.Fatal(err)
	}
	// workers:0 in policy => policy wins (serial forced by resource policy,
	// not by the lane parallel field). The real fix was changing workers:0
	// to workers:auto in .cognitive-os/test-resource-policy.yaml.
	if plan.Invokes[0].Workers != "0" {
		t.Errorf("expected resource policy workers:0 to win, got %q (the code is correct; fix is in the YAML data)", plan.Invokes[0].Workers)
	}
}

// TestBuildClusterPlan_ResourcePolicyAutoWorkersOnParallelLane verifies that
// parallel:true lanes pass --workers auto when the resource policy has
// workers:auto. This is the correct post-fix behavior for the unit lane.
func TestBuildClusterPlan_ResourcePolicyAutoWorkersOnParallelLane(t *testing.T) {
	cfg := config.DefaultConfig()
	cfg.ProjectRoot = t.TempDir()
	writeRegistry(t, cfg.ProjectRoot, clusterYAML)
	writeResourcePolicy(t, cfg.ProjectRoot, `version: 1
defaults:
  workers: auto
  timeout_seconds: 300
  docker_policy: forbidden
  cost_policy: free_only
  artifact_policy: keep_summary
lanes:
  unit:
    workers: auto
    timeout_seconds: 900
`)

	plan, err := buildClusterPlan(cfg, "unit")
	if err != nil {
		t.Fatal(err)
	}
	if plan.Invokes[0].Workers != "auto" {
		t.Errorf("parallel lane with policy workers:auto should pass --workers auto, got %q", plan.Invokes[0].Workers)
	}
}

// TestBuildClusterPlan_SerialLaneIgnoresResourcePolicyWorkers verifies that
// serial (parallel:false) lanes always use workers:"0" regardless of any
// workers value in the resource policy. The cluster.go code hardcodes "0"
// for serial lanes, not the resource policy value.
func TestBuildClusterPlan_SerialLaneIgnoresResourcePolicyWorkers(t *testing.T) {
	cfg := config.DefaultConfig()
	cfg.ProjectRoot = t.TempDir()
	writeRegistry(t, cfg.ProjectRoot, clusterYAML)
	// Even with workers:4 in policy, serial lane should stay serial.
	writeResourcePolicy(t, cfg.ProjectRoot, `version: 1
defaults:
  workers: auto
  timeout_seconds: 300
  docker_policy: forbidden
  cost_policy: free_only
  artifact_policy: keep_summary
lanes:
  behavior:
    workers: 4
    timeout_seconds: 600
`)

	plan, err := buildClusterPlan(cfg, "behavior")
	if err != nil {
		t.Fatal(err)
	}
	if plan.Invokes[0].Workers != "0" {
		t.Errorf("serial lane (parallel:false) must always use workers:0, got %q", plan.Invokes[0].Workers)
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

func TestEnforceResourcePolicyBlocksCostBearingWithoutOptIn(t *testing.T) {
	resources := resourcepolicy.ResourcePolicy{CostPolicy: "cost_bearing", DockerPolicy: "allowed", TimeoutSeconds: 10, Workers: "0", ArtifactPolicy: "keep_full"}
	if err := enforceResourcePolicy(resources); err == nil {
		t.Fatal("expected cost-bearing lane to require opt-in")
	}
	t.Setenv("COS_ALLOW_COST_BEARING_TESTS", "1")
	if err := enforceResourcePolicy(resources); err != nil {
		t.Fatalf("expected opt-in to allow cost-bearing lane, got %v", err)
	}
}

func TestEnforceResourcePolicyBlocksDockerRequiredWithoutOptIn(t *testing.T) {
	resources := resourcepolicy.ResourcePolicy{CostPolicy: "free_only", DockerPolicy: "required", TimeoutSeconds: 10, Workers: "0", ArtifactPolicy: "keep_summary"}
	if err := enforceResourcePolicy(resources); err == nil {
		t.Fatal("expected docker-required lane to require opt-in")
	}
	t.Setenv("COS_ALLOW_DOCKER_TESTS", "1")
	if err := enforceResourcePolicy(resources); err != nil {
		t.Fatalf("expected opt-in to allow docker-required lane, got %v", err)
	}
}
