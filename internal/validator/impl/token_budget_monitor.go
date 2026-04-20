package impl

import (
	"bufio"
	"context"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strconv"
	"time"

	"github.com/luum/cos-dispatch/internal/validator"
	"github.com/luum/cos-dispatch/pkg/hook"
)

// TokenBudgetMonitorValidator enforces hourly token + agent-launch budgets,
// porting hooks/token-budget-monitor.sh. State is read from the cost-events
// JSONL file at $CLAUDE_PROJECT_DIR/.cognitive-os/metrics/cost-events.jsonl.
//
// Thresholds (overridable via env at construction time):
//   - HourlyTokens: 5_000_000 default — block at >=95%, warn at >=80%
//   - AgentsPerHour: 30 default — block when reached
//
// Override env: RATE_LIMIT_OVERRIDE=true skips checks entirely.
type TokenBudgetMonitorValidator struct {
	costEventsPath string
	hourlyTokens   int64
	agentsPerHour  int
	overrideEnv    bool
	now            func() time.Time
}

// NewTokenBudgetMonitorValidator constructs the validator. Empty costEventsPath
// resolves to $CLAUDE_PROJECT_DIR/.cognitive-os/metrics/cost-events.jsonl.
func NewTokenBudgetMonitorValidator(costEventsPath string, hourlyTokens int64, agentsPerHour int) *TokenBudgetMonitorValidator {
	if costEventsPath == "" {
		root := os.Getenv("CLAUDE_PROJECT_DIR")
		if root == "" {
			root = "."
		}
		costEventsPath = filepath.Join(root, ".cognitive-os", "metrics", "cost-events.jsonl")
	}
	if hourlyTokens <= 0 {
		hourlyTokens = envInt64("RATE_LIMIT_HOURLY_TOKENS", 5_000_000)
	}
	if agentsPerHour <= 0 {
		agentsPerHour = int(envInt64("RATE_LIMIT_MAX_AGENTS", 30))
	}
	return &TokenBudgetMonitorValidator{
		costEventsPath: costEventsPath,
		hourlyTokens:   hourlyTokens,
		agentsPerHour:  agentsPerHour,
		overrideEnv:    os.Getenv("RATE_LIMIT_OVERRIDE") == "true",
		now:            time.Now,
	}
}

func (v *TokenBudgetMonitorValidator) Name() string { return "token-budget-monitor" }
func (v *TokenBudgetMonitorValidator) Category() validator.ValidatorCategory {
	return validator.CategoryIO
}

// Validate counts tokens and agent launches from the cost events file over the
// last hour, then applies the same decision tree as the bash hook.
func (v *TokenBudgetMonitorValidator) Validate(_ context.Context, hookCtx *hook.Context) *validator.Result {
	if v.overrideEnv {
		return validator.Pass()
	}
	if hookCtx == nil {
		return validator.Pass()
	}

	tokens, agents := v.countLastHour()
	pct := 0
	if v.hourlyTokens > 0 {
		pct = int(tokens * 100 / v.hourlyTokens)
	}

	switch {
	case pct >= 95:
		return &validator.Result{
			Passed:      false,
			ShouldBlock: true,
			Message: fmt.Sprintf("RATE LIMIT REACHED (%d%%). Auto-pausing agent launches. Tokens: %d/%d | Agents: %d/%d",
				pct, tokens, v.hourlyTokens, agents, v.agentsPerHour),
			FixHint: "To force continue: set RATE_LIMIT_OVERRIDE=true",
			Reference: validator.Reference{
				Code: "COS-RATE-002",
				URL:  "docs/architecture/cos-dispatch/token-budget-monitor.md",
			},
			Details: map[string]string{
				"tokens_used": strconv.FormatInt(tokens, 10),
				"limit":       strconv.FormatInt(v.hourlyTokens, 10),
				"pct":         strconv.Itoa(pct),
				"agents":      strconv.Itoa(agents),
			},
		}
	case agents >= v.agentsPerHour:
		return &validator.Result{
			Passed:      false,
			ShouldBlock: true,
			Message: fmt.Sprintf("RATE LIMIT: Agent launch limit reached (%d/%d this hour).",
				agents, v.agentsPerHour),
			FixHint: "Wait until the next hour or set RATE_LIMIT_OVERRIDE=true",
			Reference: validator.Reference{
				Code: "COS-RATE-003",
				URL:  "docs/architecture/cos-dispatch/token-budget-monitor.md",
			},
			Details: map[string]string{
				"agents": strconv.Itoa(agents),
				"limit":  strconv.Itoa(v.agentsPerHour),
			},
		}
	case pct >= 80:
		return &validator.Result{
			Passed:      false,
			ShouldBlock: false, // warning, not blocking
			Message: fmt.Sprintf("WARNING: %d%% of hourly token limit used (%d/%d). %d agents launched this hour. Consider pausing.",
				pct, tokens, v.hourlyTokens, agents),
			Reference: validator.Reference{
				Code: "COS-RATE-004",
				URL:  "docs/architecture/cos-dispatch/token-budget-monitor.md",
			},
		}
	}
	return validator.Pass()
}

// countLastHour parses the cost events JSONL file and returns (tokens, agents)
// observed over the last hour. Malformed or missing files return zeros.
func (v *TokenBudgetMonitorValidator) countLastHour() (int64, int) {
	f, err := os.Open(v.costEventsPath)
	if err != nil {
		return 0, 0
	}
	defer f.Close()

	cutoff := v.now().Add(-time.Hour).Unix()
	var tokens int64
	var agents int

	type costEvent struct {
		Timestamp    string `json:"timestamp"`
		TotalTokens  int64  `json:"total_tokens"`
		InputTokens  int64  `json:"input_tokens"`
		OutputTokens int64  `json:"output_tokens"`
		Action       string `json:"action"`
	}

	scanner := bufio.NewScanner(f)
	// Allow large lines (cost events can include big context blobs).
	scanner.Buffer(make([]byte, 1024*1024), 16*1024*1024)
	for scanner.Scan() {
		line := scanner.Bytes()
		if len(line) == 0 {
			continue
		}
		var e costEvent
		if err := json.Unmarshal(line, &e); err != nil {
			continue
		}
		ts, err := time.Parse(time.RFC3339, e.Timestamp)
		if err != nil {
			// Try without trailing Z handling — RFC3339 should normally cover it.
			continue
		}
		if ts.Unix() < cutoff {
			continue
		}
		if e.TotalTokens > 0 {
			tokens += e.TotalTokens
		} else {
			tokens += e.InputTokens + e.OutputTokens
		}
		if e.Action == "agent_launch" {
			agents++
		}
	}
	return tokens, agents
}

// envInt64 reads an integer env var, returning fallback if missing/invalid.
func envInt64(key string, fallback int64) int64 {
	raw := os.Getenv(key)
	if raw == "" {
		return fallback
	}
	n, err := strconv.ParseInt(raw, 10, 64)
	if err != nil {
		return fallback
	}
	return n
}
