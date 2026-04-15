package provider

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"

	"github.com/luum/cos-dispatch/pkg/hook"
)

// codexPayload represents the JSON structure Codex sends on stdin.
// Codex adopted Claude Code's hook format, so the structure is nearly identical.
type codexPayload struct {
	HookEvent string          `json:"hook_event"`
	ToolName  string          `json:"tool_name"`
	ToolInput json.RawMessage `json:"tool_input"`
	SessionID string          `json:"session_id"`
	ExitCode  *int            `json:"exit_code,omitempty"`
	Output    string          `json:"output,omitempty"`
}

// codexToolInput mirrors Claude's tool_input since Codex copied the format.
type codexToolInput struct {
	Command  string `json:"command,omitempty"`
	FilePath string `json:"file_path,omitempty"`
	Content  string `json:"content,omitempty"`
	Prompt   string `json:"prompt,omitempty"`
	Pattern  string `json:"pattern,omitempty"`
}

// CodexProvider adapts OpenAI Codex hook payloads to the canonical format.
type CodexProvider struct{}

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
		filepath.Join(projectDir, "hooks.json"),
	}
}

// mapCodexEvent maps Codex event names to canonical events.
// Codex uses the same event names as Claude Code.
func mapCodexEvent(event string) hook.CanonicalEvent {
	switch event {
	case "PreToolUse":
		return hook.CanonicalEventBeforeTool
	case "PostToolUse":
		return hook.CanonicalEventAfterTool
	case "SessionStart":
		return hook.CanonicalEventSessionStart
	case "SessionEnd":
		return hook.CanonicalEventSessionEnd
	default:
		return hook.CanonicalEventUnknown
	}
}
