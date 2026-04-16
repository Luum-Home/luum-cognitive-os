package impl

import (
	"context"
	"fmt"
	"os"
	"path/filepath"
	"testing"
	"time"

	"github.com/luum/cos-dispatch/pkg/hook"
)

func writeCostEvents(t *testing.T, lines []string) string {
	t.Helper()
	dir := t.TempDir()
	path := filepath.Join(dir, "cost-events.jsonl")
	if err := os.WriteFile(path, []byte(joinLines(lines)), 0o644); err != nil {
		t.Fatalf("write cost events: %v", err)
	}
	return path
}

func joinLines(lines []string) string {
	out := ""
	for _, l := range lines {
		out += l + "\n"
	}
	return out
}

func TestRateLimitProtection_PassesUnderThreshold(t *testing.T) {
	now := time.Now()
	path := writeCostEvents(t, []string{
		`{"timestamp":"` + now.UTC().Format(time.RFC3339) + `","total_tokens":100000,"action":"agent_launch"}`,
	})
	v := NewRateLimitProtectionValidator(path, 5_000_000, 30)
	v.now = func() time.Time { return now }

	r := v.Validate(context.Background(), &hook.Context{ToolName: hook.ToolAgent})
	if !r.Passed {
		t.Fatalf("expected pass under threshold, got: %s", r.Message)
	}
}

func TestRateLimitProtection_BlocksAt95Percent(t *testing.T) {
	now := time.Now()
	path := writeCostEvents(t, []string{
		`{"timestamp":"` + now.UTC().Format(time.RFC3339) + `","total_tokens":4800000,"action":"agent_launch"}`,
	})
	v := NewRateLimitProtectionValidator(path, 5_000_000, 30)
	v.now = func() time.Time { return now }

	r := v.Validate(context.Background(), &hook.Context{ToolName: hook.ToolAgent})
	if r.Passed {
		t.Fatal("expected block at >=95% (4.8M of 5M)")
	}
	if !r.ShouldBlock {
		t.Fatal("expected ShouldBlock=true")
	}
	if r.Reference.Code != "COS-RATE-002" {
		t.Errorf("expected code COS-RATE-002, got %s", r.Reference.Code)
	}
}

func TestRateLimitProtection_BlocksAtAgentLimit(t *testing.T) {
	now := time.Now()
	var lines []string
	for i := 0; i < 30; i++ {
		lines = append(lines, fmt.Sprintf(`{"timestamp":"%s","total_tokens":1000,"action":"agent_launch"}`,
			now.UTC().Format(time.RFC3339)))
	}
	path := writeCostEvents(t, lines)
	v := NewRateLimitProtectionValidator(path, 5_000_000, 30)
	v.now = func() time.Time { return now }

	r := v.Validate(context.Background(), &hook.Context{ToolName: hook.ToolAgent})
	if r.Passed {
		t.Fatal("expected block at agent limit (30/30)")
	}
	if r.Reference.Code != "COS-RATE-003" {
		t.Errorf("expected code COS-RATE-003, got %s", r.Reference.Code)
	}
}

func TestRateLimitProtection_WarnsAt80Percent(t *testing.T) {
	now := time.Now()
	path := writeCostEvents(t, []string{
		`{"timestamp":"` + now.UTC().Format(time.RFC3339) + `","total_tokens":4100000,"action":"agent_launch"}`,
	})
	v := NewRateLimitProtectionValidator(path, 5_000_000, 30)
	v.now = func() time.Time { return now }

	r := v.Validate(context.Background(), &hook.Context{ToolName: hook.ToolAgent})
	if r.Passed {
		t.Fatal("expected warn at >=80%")
	}
	if r.ShouldBlock {
		t.Fatal("warn should not block")
	}
	if r.Reference.Code != "COS-RATE-004" {
		t.Errorf("expected code COS-RATE-004, got %s", r.Reference.Code)
	}
}

func TestRateLimitProtection_IgnoresOldEvents(t *testing.T) {
	now := time.Now()
	old := now.Add(-2 * time.Hour)
	path := writeCostEvents(t, []string{
		`{"timestamp":"` + old.UTC().Format(time.RFC3339) + `","total_tokens":4900000,"action":"agent_launch"}`,
	})
	v := NewRateLimitProtectionValidator(path, 5_000_000, 30)
	v.now = func() time.Time { return now }

	r := v.Validate(context.Background(), &hook.Context{ToolName: hook.ToolAgent})
	if !r.Passed {
		t.Fatalf("old events should be ignored, got: %s", r.Message)
	}
}

func TestRateLimitProtection_OverrideEnv(t *testing.T) {
	t.Setenv("RATE_LIMIT_OVERRIDE", "true")
	now := time.Now()
	path := writeCostEvents(t, []string{
		`{"timestamp":"` + now.UTC().Format(time.RFC3339) + `","total_tokens":10000000,"action":"agent_launch"}`,
	})
	v := NewRateLimitProtectionValidator(path, 5_000_000, 30)
	v.now = func() time.Time { return now }

	r := v.Validate(context.Background(), &hook.Context{ToolName: hook.ToolAgent})
	if !r.Passed {
		t.Fatal("override env should bypass all checks")
	}
}

func TestRateLimitProtection_MissingFile(t *testing.T) {
	v := NewRateLimitProtectionValidator(filepath.Join(t.TempDir(), "missing.jsonl"), 5_000_000, 30)
	r := v.Validate(context.Background(), &hook.Context{ToolName: hook.ToolAgent})
	if !r.Passed {
		t.Fatal("missing cost events file should pass")
	}
}
