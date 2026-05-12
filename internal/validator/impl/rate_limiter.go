// Package impl contains concrete validator implementations ported from the
// bash hooks suite. Each validator implements the validator.Validator interface
// and is registered via factory.go with an appropriate predicate.
package impl

import (
	"context"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"sync"
	"time"

	"github.com/luum/cos-dispatch/internal/validator"
	"github.com/luum/cos-dispatch/pkg/hook"
)

// rateLimiterDefaults mirrors the defaults from lib/rate_limiter.py.
//
// Per-action limits are tracked over a 60-second sliding window. The phase
// modifier multiplies the base limit (e.g. reconstruction = 1.5x).
type rateLimiterDefaults struct {
	WindowSeconds   int
	CooldownSeconds int
	BaseLimits      map[string]int
	PhaseModifiers  map[string]float64
}

func defaultRateLimiterConfig() rateLimiterDefaults {
	return rateLimiterDefaults{
		WindowSeconds:   60,
		CooldownSeconds: 60,
		BaseLimits: map[string]int{
			"agent_launch": 10,
			"bash_command": 15,
			"file_write":   30,
			"tool_call":    60,
		},
		PhaseModifiers: map[string]float64{
			"stabilization":  1.0,
			"reconstruction": 1.5,
			"experimental":   2.0,
		},
	}
}

// RateLimiterValidator enforces per-action rate limits with a phase-aware
// modifier. State is persisted to a JSON file mirroring the bash/Python
// implementation so both can interoperate.
type RateLimiterValidator struct {
	statePath string
	phase     string
	now       func() time.Time // injectable for tests
	cfg       rateLimiterDefaults
	mu        sync.Mutex
}

// NewRateLimiterValidator constructs a RateLimiterValidator. If statePath is
// empty, it defaults to $CLAUDE_PROJECT_DIR/.cognitive-os/rate-limit-state.json
// (or .cognitive-os/rate-limit-state.json relative to cwd if unset).
func NewRateLimiterValidator(statePath, phase string) *RateLimiterValidator {
	if phase == "" {
		phase = "stabilization"
	}
	if statePath == "" {
		root := os.Getenv("CLAUDE_PROJECT_DIR")
		if root == "" {
			root = "."
		}
		statePath = filepath.Join(root, ".cognitive-os", "rate-limit-state.json")
	}
	return &RateLimiterValidator{
		statePath: statePath,
		phase:     phase,
		now:       time.Now,
		cfg:       defaultRateLimiterConfig(),
	}
}

// Name returns the validator's unique name.
func (v *RateLimiterValidator) Name() string { return "rate-limiter" }

// Category returns CategoryIO since this validator reads and writes state.
func (v *RateLimiterValidator) Category() validator.ValidatorCategory {
	return validator.CategoryIO
}

// rlState is the on-disk representation of recent action timestamps.
type rlState struct {
	Actions map[string][]int64 `json:"actions"`
}

func (v *RateLimiterValidator) loadState() *rlState {
	data, err := os.ReadFile(v.statePath)
	if err != nil {
		return &rlState{Actions: make(map[string][]int64)}
	}
	var s rlState
	if err := json.Unmarshal(data, &s); err != nil || s.Actions == nil {
		return &rlState{Actions: make(map[string][]int64)}
	}
	return &s
}

func (v *RateLimiterValidator) saveState(s *rlState) {
	if err := os.MkdirAll(filepath.Dir(v.statePath), 0o755); err != nil {
		return
	}
	data, err := json.Marshal(s)
	if err != nil {
		return
	}
	_ = os.WriteFile(v.statePath, data, 0o644)
}

// limitFor returns the effective per-window limit for the action under the
// current phase.
func (v *RateLimiterValidator) limitFor(action string) int {
	base, ok := v.cfg.BaseLimits[action]
	if !ok {
		base = v.cfg.BaseLimits["tool_call"]
	}
	mod, ok := v.cfg.PhaseModifiers[v.phase]
	if !ok {
		mod = 1.0
	}
	return int(float64(base) * mod)
}

// actionFor maps a tool type to a rate-limited action category, mirroring the
// bash mapping in hooks/rate-limiter.sh.
func actionFor(tool hook.ToolType) string {
	switch tool {
	case hook.ToolAgent:
		return "agent_launch"
	case hook.ToolBash:
		return "bash_command"
	case hook.ToolWrite, hook.ToolEdit:
		return "file_write"
	default:
		return "tool_call"
	}
}

// Validate checks whether the current action should be rate-limited. On pass it
// records the action in the sliding window. On block it returns a Fail with a
// structured message including the queue suggestion text.
func (v *RateLimiterValidator) Validate(_ context.Context, hookCtx *hook.Context) *validator.Result {
	if hookCtx == nil {
		return validator.Pass()
	}
	v.mu.Lock()
	defer v.mu.Unlock()

	action := actionFor(hookCtx.ToolName)
	state := v.loadState()
	now := v.now().Unix()
	cutoff := now - int64(v.cfg.WindowSeconds)

	// Prune entries outside the sliding window.
	pruned := make([]int64, 0, len(state.Actions[action]))
	for _, ts := range state.Actions[action] {
		if ts >= cutoff {
			pruned = append(pruned, ts)
		}
	}
	state.Actions[action] = pruned

	limit := v.limitFor(action)
	if len(pruned) >= limit {
		msg := fmt.Sprintf("%s limit exceeded: %d/%d per minute (phase: %s)",
			action, len(pruned), limit, v.phase)
		fix := fmt.Sprintf("Wait ~%ds for the next slot.", v.cfg.CooldownSeconds)
		return &validator.Result{
			Passed:      false,
			ShouldBlock: true,
			Message:     msg,
			FixHint:     fix,
			Reference: validator.Reference{
				Code: "COS-RATE-001",
				URL:  "docs/04-Concepts/architecture/cos-dispatch/rate-limiter.md",
			},
			Details: map[string]string{
				"action":  action,
				"phase":   v.phase,
				"current": fmt.Sprintf("%d", len(pruned)),
				"limit":   fmt.Sprintf("%d", limit),
			},
		}
	}

	// Record this action and persist.
	state.Actions[action] = append(state.Actions[action], now)
	v.saveState(state)
	return validator.Pass()
}
