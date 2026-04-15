package provider

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"

	"github.com/luum/cos-dispatch/pkg/hook"
)

// cursorPayload represents the JSON structure Cursor sends on stdin.
type cursorPayload struct {
	HookEvent string          `json:"hook_event"`
	ToolName  string          `json:"tool_name"`
	ToolInput json.RawMessage `json:"tool_input"`
	SessionID string          `json:"session_id"`
	ExitCode  *int            `json:"exit_code,omitempty"`
	Output    string          `json:"output,omitempty"`
}

// cursorToolInput represents Cursor tool_input fields.
type cursorToolInput struct {
	Command  string `json:"command,omitempty"`
	FilePath string `json:"file_path,omitempty"`
	Content  string `json:"content,omitempty"`
	Prompt   string `json:"prompt,omitempty"`
	Pattern  string `json:"pattern,omitempty"`
}

// CursorProvider adapts Cursor editor hook payloads to the canonical format.
type CursorProvider struct{}

// NewCursorProvider creates a Cursor provider adapter.
func NewCursorProvider() *CursorProvider {
	return &CursorProvider{}
}

func (p *CursorProvider) Name() hook.Provider {
	return hook.ProviderCursor
}

// Detect checks for CURSOR_SESSION_ID env var or presence of .cursor/ directory.
func (p *CursorProvider) Detect() bool {
	if os.Getenv("CURSOR_SESSION_ID") != "" {
		return true
	}
	// Check for .cursor/ directory in the current working directory.
	if _, err := os.Stat(".cursor"); err == nil {
		return true
	}
	return false
}

// Parse converts Cursor JSON into a canonical hook.Context.
func (p *CursorProvider) Parse(raw []byte) (*hook.Context, error) {
	var payload cursorPayload
	if err := json.Unmarshal(raw, &payload); err != nil {
		return nil, fmt.Errorf("cursor: parse payload: %w", err)
	}

	var ti cursorToolInput
	if len(payload.ToolInput) > 0 {
		if err := json.Unmarshal(payload.ToolInput, &ti); err != nil {
			return nil, fmt.Errorf("cursor: parse tool_input: %w", err)
		}
	}

	ctx := &hook.Context{
		Provider:  hook.ProviderCursor,
		Event:     mapCursorEvent(payload.HookEvent),
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

	return ctx, nil
}

// BuildResponse returns Cursor's expected JSON response format.
func (p *CursorProvider) BuildResponse(hookCtx *hook.Context, decision string, message string, additionalContext string) any {
	return map[string]any{
		"hookSpecificOutput": map[string]any{
			"permissionDecision": decision,
			"reason":             message,
			"additionalContext":  additionalContext,
		},
	}
}

// ConfigPaths returns Cursor config file paths.
func (p *CursorProvider) ConfigPaths(projectDir string) []string {
	return []string{
		filepath.Join(projectDir, ".cursor", "hooks.json"),
	}
}

// mapCursorEvent maps Cursor event names to canonical events.
func mapCursorEvent(event string) hook.CanonicalEvent {
	switch event {
	case "beforeShellExecution":
		return hook.CanonicalEventBeforeTool
	case "afterFileEdit":
		return hook.CanonicalEventAfterTool
	case "SessionStart":
		return hook.CanonicalEventSessionStart
	case "SessionEnd":
		return hook.CanonicalEventSessionEnd
	default:
		return hook.CanonicalEventUnknown
	}
}
