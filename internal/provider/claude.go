package provider

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"

	"github.com/luum/cos-dispatch/pkg/hook"
)

// claudePayload represents the JSON structure Claude Code sends on stdin.
type claudePayload struct {
	HookEvent string          `json:"hook_event"`
	ToolName  string          `json:"tool_name"`
	ToolInput json.RawMessage `json:"tool_input"`
	SessionID string          `json:"session_id"`
	ExitCode  *int            `json:"exit_code,omitempty"`
	Output    string          `json:"output,omitempty"`
}

// claudeToolInput represents the tool_input object for common Claude tools.
type claudeToolInput struct {
	Command  string `json:"command,omitempty"`
	FilePath string `json:"file_path,omitempty"`
	Content  string `json:"content,omitempty"`
	Prompt   string `json:"prompt,omitempty"`
	Pattern  string `json:"pattern,omitempty"`
}

// ClaudeProvider adapts Claude Code hook payloads to the canonical format.
type ClaudeProvider struct{}

// NewClaudeProvider creates a Claude Code provider adapter.
func NewClaudeProvider() *ClaudeProvider {
	return &ClaudeProvider{}
}

func (p *ClaudeProvider) Name() hook.Provider {
	return hook.ProviderClaude
}

// Detect checks for CLAUDE_PROJECT_DIR or CLAUDE_SESSION_ID environment variables.
func (p *ClaudeProvider) Detect() bool {
	return os.Getenv("CLAUDE_PROJECT_DIR") != "" || os.Getenv("CLAUDE_SESSION_ID") != ""
}

// Parse converts Claude Code JSON into a canonical hook.Context.
func (p *ClaudeProvider) Parse(raw []byte) (*hook.Context, error) {
	var payload claudePayload
	if err := json.Unmarshal(raw, &payload); err != nil {
		return nil, fmt.Errorf("claude: parse payload: %w", err)
	}

	var ti claudeToolInput
	if len(payload.ToolInput) > 0 {
		if err := json.Unmarshal(payload.ToolInput, &ti); err != nil {
			return nil, fmt.Errorf("claude: parse tool_input: %w", err)
		}
	}

	ctx := &hook.Context{
		Provider:  hook.ProviderClaude,
		Event:     mapClaudeEvent(payload.HookEvent),
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

	if dir := os.Getenv("CLAUDE_PROJECT_DIR"); dir != "" {
		ctx.ProjectDir = dir
	}

	return ctx, nil
}

// BuildResponse returns Claude Code's expected JSON response format.
func (p *ClaudeProvider) BuildResponse(hookCtx *hook.Context, decision string, message string, additionalContext string) any {
	return map[string]any{
		"hookSpecificOutput": map[string]any{
			"permissionDecision": decision,
			"reason":             message,
			"additionalContext":  additionalContext,
		},
	}
}

// ConfigPaths returns Claude Code config file paths.
func (p *ClaudeProvider) ConfigPaths(projectDir string) []string {
	return []string{
		filepath.Join(projectDir, ".claude", "settings.json"),
	}
}

// mapClaudeEvent maps Claude Code event names to canonical events.
func mapClaudeEvent(event string) hook.CanonicalEvent {
	switch event {
	case "PreToolUse":
		return hook.CanonicalEventBeforeTool
	case "PostToolUse":
		return hook.CanonicalEventAfterTool
	case "SessionStart":
		return hook.CanonicalEventSessionStart
	case "SessionEnd":
		return hook.CanonicalEventSessionEnd
	case "PromptSubmit":
		return hook.CanonicalEventPromptSubmit
	case "SubagentStart":
		return hook.CanonicalEventSubagentStart
	case "Compact":
		return hook.CanonicalEventCompact
	default:
		return hook.CanonicalEventUnknown
	}
}
