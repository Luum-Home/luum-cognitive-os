package impl

import (
	"testing"

	"github.com/luum/cos-dispatch/internal/validator"
	"github.com/luum/cos-dispatch/pkg/hook"
)

func TestFactory_RegistersAllSix(t *testing.T) {
	dir := t.TempDir()
	reg := RegisterDefaults(nil, FactoryConfig{
		ProjectDir:           dir,
		Phase:                "stabilization",
		HourlyTokens:         5_000_000,
		AgentsPerHour:        30,
		RateLimiterStatePath: dir + "/rl.json",
		CostEventsPath:       dir + "/cost-events.jsonl",
		ContentPolicyPath:    dir + "/missing-policy.yaml",
	})

	// BeforeTool / Bash → rate-limiter only.
	bashCtx := &hook.Context{Event: hook.CanonicalEventBeforeTool, ToolName: hook.ToolBash}
	got := names(reg.FindValidators(bashCtx))
	want := []string{"rate-limiter"}
	if !sameSet(got, want) {
		t.Errorf("Bash before: got %v, want %v", got, want)
	}

	// BeforeTool / Agent → rate-limiter, rate-limit-protection, completeness, prompt-quality.
	agentCtx := &hook.Context{Event: hook.CanonicalEventBeforeTool, ToolName: hook.ToolAgent}
	got = names(reg.FindValidators(agentCtx))
	want = []string{"rate-limiter", "rate-limit-protection", "completeness-check", "prompt-quality"}
	if !sameSet(got, want) {
		t.Errorf("Agent before: got %v, want %v", got, want)
	}

	// AfterTool / Edit → secret-detector, content-policy.
	editCtx := &hook.Context{Event: hook.CanonicalEventAfterTool, ToolName: hook.ToolEdit}
	got = names(reg.FindValidators(editCtx))
	want = []string{"secret-detector", "content-policy"}
	if !sameSet(got, want) {
		t.Errorf("Edit after: got %v, want %v", got, want)
	}

	// AfterTool / Write → secret-detector, content-policy.
	writeCtx := &hook.Context{Event: hook.CanonicalEventAfterTool, ToolName: hook.ToolWrite}
	got = names(reg.FindValidators(writeCtx))
	want = []string{"secret-detector", "content-policy"}
	if !sameSet(got, want) {
		t.Errorf("Write after: got %v, want %v", got, want)
	}

	// BeforeTool / Read → no validators (Read isn't gated by any of the six).
	readCtx := &hook.Context{Event: hook.CanonicalEventBeforeTool, ToolName: hook.ToolRead}
	got = names(reg.FindValidators(readCtx))
	if len(got) != 0 {
		t.Errorf("Read before: got %v, want empty", got)
	}
}

func TestFactory_AcceptsExistingRegistry(t *testing.T) {
	reg := validator.NewRegistry()
	got := RegisterDefaults(reg, FactoryConfig{ProjectDir: t.TempDir()})
	if got != reg {
		t.Fatal("expected RegisterDefaults to return the supplied registry instance")
	}
}

func names(vs []validator.Validator) []string {
	out := make([]string, len(vs))
	for i, v := range vs {
		out[i] = v.Name()
	}
	return out
}

func sameSet(a, b []string) bool {
	if len(a) != len(b) {
		return false
	}
	seen := make(map[string]struct{}, len(a))
	for _, s := range a {
		seen[s] = struct{}{}
	}
	for _, s := range b {
		if _, ok := seen[s]; !ok {
			return false
		}
	}
	return true
}
