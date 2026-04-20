package impl

import (
	"github.com/luum/cos-dispatch/internal/validator"
	"github.com/luum/cos-dispatch/pkg/hook"
)

// FactoryConfig parameterizes RegisterDefaults so callers can override paths,
// limits, and the project phase without touching code.
type FactoryConfig struct {
	// ProjectDir is the project root used for resolving state, config, and
	// metrics paths. Empty falls back to $CLAUDE_PROJECT_DIR or cwd.
	ProjectDir string

	// Phase is the project phase passed to the rate limiter (e.g. "stabilization",
	// "reconstruction"). Empty defaults to "stabilization".
	Phase string

	// HourlyTokens overrides the per-hour token budget used by the rate limit
	// protection validator. Zero/negative falls back to env or 5_000_000.
	HourlyTokens int64

	// AgentsPerHour overrides the per-hour agent launch budget. Zero/negative
	// falls back to env or 30.
	AgentsPerHour int

	// RateLimiterStatePath, CostEventsPath and ContentPolicyPath let tests use
	// scratch files. Empty values resolve to ProjectDir-derived defaults.
	RateLimiterStatePath string
	CostEventsPath       string
	ContentPolicyPath    string
}

// RegisterDefaults wires the six Phase-3 Go validators into the registry with
// predicates that match the bash hook event/tool gating:
//
//   - rate-limiter:           BeforeTool on Bash | Edit | Write | Agent
//   - token-budget-monitor:   BeforeTool on Agent
//   - secret-detector:        AfterTool on Edit | Write
//   - content-policy:         AfterTool on Edit | Write
//   - completeness-check:     BeforeTool on Agent
//   - prompt-quality:         BeforeTool on Agent
//
// Returns the registry it operated on (callers may pass nil to get a fresh one).
func RegisterDefaults(reg *validator.Registry, cfg FactoryConfig) *validator.Registry {
	if reg == nil {
		reg = validator.NewRegistry()
	}

	beforeFileOrCmd := validator.And(
		validator.EventIs(hook.CanonicalEventBeforeTool),
		validator.Or(
			validator.ToolTypeIs(hook.ToolBash),
			validator.ToolTypeIs(hook.ToolEdit),
			validator.ToolTypeIs(hook.ToolWrite),
			validator.ToolTypeIs(hook.ToolAgent),
		),
	)
	beforeAgent := validator.And(
		validator.EventIs(hook.CanonicalEventBeforeTool),
		validator.ToolTypeIs(hook.ToolAgent),
	)
	afterFile := validator.And(
		validator.EventIs(hook.CanonicalEventAfterTool),
		validator.Or(
			validator.ToolTypeIs(hook.ToolEdit),
			validator.ToolTypeIs(hook.ToolWrite),
		),
	)

	reg.Register(NewRateLimiterValidator(cfg.RateLimiterStatePath, cfg.Phase), beforeFileOrCmd)
	reg.Register(NewTokenBudgetMonitorValidator(cfg.CostEventsPath, cfg.HourlyTokens, cfg.AgentsPerHour), beforeAgent)
	reg.Register(NewSecretDetectorValidator(cfg.ProjectDir), afterFile)
	reg.Register(NewContentPolicyValidator(cfg.ProjectDir, cfg.ContentPolicyPath), afterFile)
	reg.Register(NewCompletenessCheckerValidator(), beforeAgent)
	reg.Register(NewPromptQualityValidator(), beforeAgent)

	return reg
}
