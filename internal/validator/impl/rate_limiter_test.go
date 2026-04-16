package impl

import (
	"context"
	"path/filepath"
	"testing"
	"time"

	"github.com/luum/cos-dispatch/pkg/hook"
)

func newTestRateLimiter(t *testing.T, phase string, now time.Time) *RateLimiterValidator {
	t.Helper()
	dir := t.TempDir()
	v := NewRateLimiterValidator(filepath.Join(dir, "rl.json"), phase)
	v.now = func() time.Time { return now }
	return v
}

func TestRateLimiter_PassesUnderLimit(t *testing.T) {
	v := newTestRateLimiter(t, "stabilization", time.Unix(1000, 0))
	ctx := &hook.Context{ToolName: hook.ToolBash, Event: hook.CanonicalEventBeforeTool}

	for i := 0; i < 10; i++ {
		r := v.Validate(context.Background(), ctx)
		if !r.Passed {
			t.Fatalf("call %d: expected pass, got block: %s", i, r.Message)
		}
	}
}

func TestRateLimiter_BlocksOverLimit(t *testing.T) {
	v := newTestRateLimiter(t, "stabilization", time.Unix(1000, 0))
	ctx := &hook.Context{ToolName: hook.ToolBash, Event: hook.CanonicalEventBeforeTool}

	// Bash limit at stabilization (1.0x) = 15 per minute. 16th call should block.
	var blocked bool
	for i := 0; i < 16; i++ {
		r := v.Validate(context.Background(), ctx)
		if !r.Passed {
			blocked = true
			if !r.ShouldBlock {
				t.Fatalf("expected ShouldBlock=true on rate limit failure")
			}
			if r.Reference.Code != "COS-RATE-001" {
				t.Fatalf("expected reference COS-RATE-001, got %s", r.Reference.Code)
			}
			break
		}
	}
	if !blocked {
		t.Fatal("expected to block within 16 calls at limit 15")
	}
}

func TestRateLimiter_PhaseModifierIncreasesLimit(t *testing.T) {
	now := time.Unix(2000, 0)
	v := newTestRateLimiter(t, "reconstruction", now) // 1.5x => 22
	ctx := &hook.Context{ToolName: hook.ToolBash, Event: hook.CanonicalEventBeforeTool}

	for i := 0; i < 22; i++ {
		r := v.Validate(context.Background(), ctx)
		if !r.Passed {
			t.Fatalf("call %d should pass under reconstruction phase: %s", i, r.Message)
		}
	}
	r := v.Validate(context.Background(), ctx)
	if r.Passed {
		t.Fatal("23rd call should block at reconstruction limit (22)")
	}
}

func TestRateLimiter_SlidingWindowExpires(t *testing.T) {
	now := time.Unix(3000, 0)
	v := newTestRateLimiter(t, "stabilization", now)
	ctx := &hook.Context{ToolName: hook.ToolBash, Event: hook.CanonicalEventBeforeTool}

	// Saturate the window.
	for i := 0; i < 15; i++ {
		_ = v.Validate(context.Background(), ctx)
	}
	// Next call should block.
	if r := v.Validate(context.Background(), ctx); r.Passed {
		t.Fatal("expected block at limit")
	}

	// Advance time by 61s — window should be empty again.
	v.now = func() time.Time { return time.Unix(3061, 0) }
	if r := v.Validate(context.Background(), ctx); !r.Passed {
		t.Fatalf("expected pass after window expiry: %s", r.Message)
	}
}

func TestRateLimiter_ActionMapping(t *testing.T) {
	cases := []struct {
		tool hook.ToolType
		want string
	}{
		{hook.ToolAgent, "agent_launch"},
		{hook.ToolBash, "bash_command"},
		{hook.ToolWrite, "file_write"},
		{hook.ToolEdit, "file_write"},
		{hook.ToolRead, "tool_call"},
	}
	for _, tc := range cases {
		if got := actionFor(tc.tool); got != tc.want {
			t.Errorf("actionFor(%s) = %s, want %s", tc.tool, got, tc.want)
		}
	}
}

func TestRateLimiter_NilContext(t *testing.T) {
	v := newTestRateLimiter(t, "stabilization", time.Unix(0, 0))
	if r := v.Validate(context.Background(), nil); !r.Passed {
		t.Fatal("nil context should pass")
	}
}

func TestRateLimiter_PersistsState(t *testing.T) {
	dir := t.TempDir()
	statePath := filepath.Join(dir, "rl.json")
	now := time.Unix(5000, 0)

	v1 := NewRateLimiterValidator(statePath, "stabilization")
	v1.now = func() time.Time { return now }
	ctx := &hook.Context{ToolName: hook.ToolBash, Event: hook.CanonicalEventBeforeTool}
	for i := 0; i < 15; i++ {
		_ = v1.Validate(context.Background(), ctx)
	}

	// New validator instance reads the same state file → should block immediately.
	v2 := NewRateLimiterValidator(statePath, "stabilization")
	v2.now = func() time.Time { return now }
	r := v2.Validate(context.Background(), ctx)
	if r.Passed {
		t.Fatal("expected new validator instance to see persisted state and block")
	}
}
