package provider

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"

	"github.com/luum/cos-dispatch/pkg/hook"
)

// codexPayload represents the JSON structure Codex hook drivers send on stdin.
// Codex hook projection uses Claude-like top-level hook_event names for the
// lifecycle events it supports, while .codex/hooks.json remains a native
// Codex settings driver.
type codexPayload struct {
	HookEvent string          `json:"hook_event"`
	ToolName  string          `json:"tool_name"`
	ToolInput json.RawMessage `json:"tool_input"`
	SessionID string          `json:"session_id"`
	ExitCode  *int            `json:"exit_code,omitempty"`
	Output    string          `json:"output,omitempty"`
}

// codexToolInput captures the common tool_input fields Codex hook payloads expose.
type codexToolInput struct {
	Command  string `json:"command,omitempty"`
	FilePath string `json:"file_path,omitempty"`
	Content  string `json:"content,omitempty"`
	Prompt   string `json:"prompt,omitempty"`
	Pattern  string `json:"pattern,omitempty"`
}

// CodexProvider adapts OpenAI Codex hook payloads to the canonical format.
type CodexProvider struct{}

// SupportedEvents is the honest Codex hook surface captured by ADR-081.
// Pre/Post tool events are represented here because Codex can emit them for
// Bash; Parse marks non-Bash tools as a coverage gap instead of pretending full
// Claude parity.
var CodexSupportedEvents = map[string]bool{
	"SessionStart":     true,
	"UserPromptSubmit": true,
	"PreToolUse":       true,
	"PostToolUse":      true,
	"Stop":             true,
	"SessionEnd":       true,
}

// NewCodexProvider creates a Codex provider adapter.
func NewCodexProvider() *CodexProvider {
	return &CodexProvider{}
}

func (p *CodexProvider) Name() hook.Provider {
	return hook.ProviderCodex
}

// Detect checks for CODEX_PROJECT_DIR or CODEX_SESSION_ID environment variables.
func (p *CodexProvider) Detect() bool {
	return os.Getenv("CODEX_PROJECT_DIR") != "" || os.Getenv("CODEX_SESSION_ID") != ""
}

// Parse converts Codex JSON into a canonical hook.Context.
func (p *CodexProvider) Parse(raw []byte) (*hook.Context, error) {
	var payload codexPayload
	if err := json.Unmarshal(raw, &payload); err != nil {
		return nil, fmt.Errorf("codex: parse payload: %w", err)
	}

	var ti codexToolInput
	if len(payload.ToolInput) > 0 {
		if err := json.Unmarshal(payload.ToolInput, &ti); err != nil {
			return nil, fmt.Errorf("codex: parse tool_input: %w", err)
		}
	}

	ctx := &hook.Context{
		Provider:  hook.ProviderCodex,
		Event:     mapCodexEvent(payload.HookEvent),
		ToolName:  hook.ToolType(payload.ToolName),
		SessionID: payload.SessionID,
		RawJSON:   raw,
		ExitCode:  payload.ExitCode,
		ToolInput: hook.ToolInput{
			Command:  ti.Command,
			FilePath: ti.FilePath,
			Content:  ti.Content,
			Prompt:   ti.Prompt,
			Pattern:  ti.Pattern,
		},
	}

	if payload.Output != "" {
		ctx.ToolOutput = payload.Output
	}

	if (payload.HookEvent == "PreToolUse" || payload.HookEvent == "PostToolUse") && payload.ToolName != "" && payload.ToolName != string(hook.ToolBash) {
		ctx.SetMetadata("parse_error_reason", "codex_tool_coverage_gap")
	}

	if dir := os.Getenv("CODEX_PROJECT_DIR"); dir != "" {
		ctx.ProjectDir = dir
	}

	return ctx, nil
}

// BuildResponse returns Codex's expected JSON response format.
// Codex uses the same response structure as Claude Code.
func (p *CodexProvider) BuildResponse(hookCtx *hook.Context, decision string, message string, additionalContext string) any {
	return map[string]any{
		"hookSpecificOutput": map[string]any{
			"permissionDecision": decision,
			"reason":             message,
			"additionalContext":  additionalContext,
		},
	}
}

// ConfigPaths returns Codex config file paths.
func (p *CodexProvider) ConfigPaths(projectDir string) []string {
	return []string{
		filepath.Join(projectDir, ".codex", "hooks.json"),
	}
}

// SupportedEvents returns Codex native lifecycle event names that this provider
// can normalize. Consumers use this to avoid routing unsupported Claude-only
// events into Codex by accident.
func (p *CodexProvider) SupportedEvents() map[string]bool {
	return CodexSupportedEvents
}

// mapCodexEvent maps Codex event names to canonical events.
func mapCodexEvent(event string) hook.CanonicalEvent {
	switch event {
	case "PreToolUse":
		return hook.CanonicalEventBeforeTool
	case "PostToolUse":
		return hook.CanonicalEventAfterTool
	case "SessionStart":
		return hook.CanonicalEventSessionStart
	case "UserPromptSubmit":
		return hook.CanonicalEventPromptSubmit
	case "Stop", "SessionEnd":
		return hook.CanonicalEventSessionEnd
	default:
		return hook.CanonicalEventUnknown
	}
}
