package provider

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"

	"github.com/luum/cos-dispatch/pkg/hook"
)

// windsurfPayload represents the JSON structure Windsurf sends on stdin.
type windsurfPayload struct {
	HookEvent string          `json:"hook_event"`
	ToolName  string          `json:"tool_name"`
	ToolInput json.RawMessage `json:"tool_input"`
	SessionID string          `json:"session_id"`
	ExitCode  *int            `json:"exit_code,omitempty"`
	Output    string          `json:"output,omitempty"`
}

// windsurfToolInput represents Windsurf tool_input fields.
type windsurfToolInput struct {
	Command  string `json:"command,omitempty"`
	FilePath string `json:"file_path,omitempty"`
	Content  string `json:"content,omitempty"`
	Prompt   string `json:"prompt,omitempty"`
	Pattern  string `json:"pattern,omitempty"`
}

// WindsurfProvider adapts Windsurf (Codeium) hook payloads to the canonical format.
type WindsurfProvider struct{}

// NewWindsurfProvider creates a Windsurf provider adapter.
func NewWindsurfProvider() *WindsurfProvider {
	return &WindsurfProvider{}
}

func (p *WindsurfProvider) Name() hook.Provider {
	return hook.ProviderWindsurf
}

// Detect checks for WINDSURF_SESSION_ID env var or CASCADE_CONTEXT env var.
func (p *WindsurfProvider) Detect() bool {
	return os.Getenv("WINDSURF_SESSION_ID") != "" || os.Getenv("CASCADE_CONTEXT") != ""
}

// Parse converts Windsurf JSON into a canonical hook.Context.
func (p *WindsurfProvider) Parse(raw []byte) (*hook.Context, error) {
	var payload windsurfPayload
	if err := json.Unmarshal(raw, &payload); err != nil {
		return nil, fmt.Errorf("windsurf: parse payload: %w", err)
	}

	var ti windsurfToolInput
	if len(payload.ToolInput) > 0 {
		if err := json.Unmarshal(payload.ToolInput, &ti); err != nil {
			return nil, fmt.Errorf("windsurf: parse tool_input: %w", err)
		}
	}

	ctx := &hook.Context{
		Provider:  hook.ProviderWindsurf,
		Event:     mapWindsurfEvent(payload.HookEvent),
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

// BuildResponse returns Windsurf's expected JSON response format.
func (p *WindsurfProvider) BuildResponse(hookCtx *hook.Context, decision string, message string, additionalContext string) any {
	return map[string]any{
		"hookSpecificOutput": map[string]any{
			"permissionDecision": decision,
			"reason":             message,
			"additionalContext":  additionalContext,
		},
	}
}

// ConfigPaths returns Windsurf config file paths.
func (p *WindsurfProvider) ConfigPaths(projectDir string) []string {
	return []string{
		filepath.Join(projectDir, ".windsurf", "hooks.json"),
	}
}

// mapWindsurfEvent maps Windsurf cascade event names to canonical events.
func mapWindsurfEvent(event string) hook.CanonicalEvent {
	switch event {
	case "PreCascadeAction", "PreToolUse":
		return hook.CanonicalEventBeforeTool
	case "PostCascadeAction", "PostToolUse":
		return hook.CanonicalEventAfterTool
	case "SessionStart":
		return hook.CanonicalEventSessionStart
	case "SessionEnd":
		return hook.CanonicalEventSessionEnd
	default:
		return hook.CanonicalEventUnknown
	}
}
