package resourcepolicy

import (
	"strings"
	"testing"
)

const samplePolicy = `version: 1
defaults:
  workers: auto
  timeout_seconds: 300
  docker_policy: forbidden
  cost_policy: free_only
  artifact_policy: keep_summary
lanes:
  unit:
    timeout_seconds: 180
  integration:
    workers: 0
    timeout_seconds: 900
    docker_policy: allowed
  quality:
    cost_policy: cost_bearing
    artifact_policy: keep_full
`

func TestParseAndEffectivePolicy(t *testing.T) {
	p, err := Parse(strings.NewReader(samplePolicy))
	if err != nil {
		t.Fatal(err)
	}
	unit := p.Effective("unit")
	if unit.Workers != "auto" || unit.TimeoutSeconds != 180 || unit.DockerPolicy != "forbidden" {
		t.Fatalf("unit effective policy = %+v", unit)
	}
	integration := p.Effective("integration")
	if integration.Workers != "0" || integration.TimeoutSeconds != 900 || integration.DockerPolicy != "allowed" {
		t.Fatalf("integration effective policy = %+v", integration)
	}
	quality := p.Effective("quality")
	if quality.CostPolicy != "cost_bearing" || quality.ArtifactPolicy != "keep_full" {
		t.Fatalf("quality effective policy = %+v", quality)
	}
}

func TestValidateLaneNamesRejectsUnknownLane(t *testing.T) {
	p, err := Parse(strings.NewReader(samplePolicy))
	if err != nil {
		t.Fatal(err)
	}
	if err := p.ValidateLaneNames([]string{"unit", "integration"}); err == nil {
		t.Fatal("expected unknown quality lane to fail validation")
	}
}

func TestParseRejectsInvalidPolicyValues(t *testing.T) {
	bad := `version: 1
defaults:
  workers: auto
  timeout_seconds: 0
  docker_policy: sometimes
  cost_policy: free_only
  artifact_policy: keep_summary
`
	if _, err := Parse(strings.NewReader(bad)); err == nil {
		t.Fatal("expected invalid resource policy to fail")
	}
}
