package provider

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"

	"github.com/luum/cos-dispatch/pkg/hook"
)

// windsurfPayload represents the JSON structure Windsurf (Codeium Cascade) sends
// on stdin.  Windsurf extends the base hook format with a "cascade_context"
// object that carries workspace metadata.
type windsurfPayload struct {
	HookEvent string          `json:"hook_event"`
	ToolName  string          `json:"tool_name"`
	ToolInput json.RawMessage `json:"tool_input"`
	SessionID string          `json:"session_id"`
	ExitCode  *int            `json:"exit_code,omitempty"`
	Output    string          `json:"output,omitempty"`
	// CascadeContext is a Windsurf-specific envelope carrying workspace metadata.
	CascadeContext *windsurfCascadeContext `json:"cascade_context,omitempty"`
}

// windsurfCascadeContext contains Windsurf-specific workspace metadata injected
// by the Cascade runtime alongside every hook event.
type windsurfCascadeContext struct {
	Workspace  string `json:"workspace,omitempty"`
	ActiveFile string `json:"active_file,omitempty"`
}

// windsurfToolInput represents Windsurf tool_input fields.
type windsurfToolInput struct {
	Command  string `json:"command,omitempty"`
	FilePath string `json:"file_path,omitempty"`
	Content  string `json:"content,omitempty"`
	Prompt   string `json:"prompt,omitempty"`
	Pattern  string `json:"pattern,omitempty"`
}

// windsurfResponse is the vendor-conformant response envelope Windsurf expects.
// Cascade hooks read "cascadeDecision" ("allow" or "deny") and an optional
// "reason" string.
type windsurfResponse struct {
	CascadeDecision string `json:"cascadeDecision"`
	Reason          string `json:"reason,omitempty"`
}

// WindsurfProvider adapts Windsurf (Codeium Cascade) hook payloads to the
// canonical format.
type WindsurfProvider struct{}

// NewWindsurfProvider creates a Windsurf provider adapter.
func NewWindsurfProvider() *WindsurfProvider {
	return &WindsurfProvider{}
}

func (p *WindsurfProvider) Name() hook.Provider {
	return hook.ProviderWindsurf
}

// Detect returns true when WINDSURF_SESSION_ID or CASCADE_CONTEXT env vars are
// set.  WINDSURF_SESSION_ID is injected by the Windsurf runtime; CASCADE_CONTEXT
// is the fallback variable set when Cascade is active but hasn't created a full
// session object yet (e.g. during tool initialisation).
func (p *WindsurfProvider) Detect() bool {
	return os.Getenv("WINDSURF_SESSION_ID") != "" || os.Getenv("CASCADE_CONTEXT") != ""
}

// Parse converts Windsurf JSON into a canonical hook.Context.
// The cascade_context object (if present) is stored in Context metadata so
// downstream validators can access workspace information without re-parsing.
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

	// Populate ProjectDir from Windsurf-specific env vars, falling back to the
	// cascade_context workspace field when available.
	if dir := os.Getenv("WINDSURF_PROJECT_DIR"); dir != "" {
		ctx.ProjectDir = dir
	} else if payload.CascadeContext != nil && payload.CascadeContext.Workspace != "" {
		ctx.ProjectDir = payload.CascadeContext.Workspace
	}

	// Persist cascade_context into metadata so validators can consume it.
	if payload.CascadeContext != nil {
		ctx.SetMetadata("cascade_workspace", payload.CascadeContext.Workspace)
		ctx.SetMetadata("cascade_active_file", payload.CascadeContext.ActiveFile)
	}

	return ctx, nil
}

// BuildResponse returns Windsurf's vendor-conformant response envelope.
// Cascade hooks expect {"cascadeDecision":"allow"|"deny","reason":"..."}.
func (p *WindsurfProvider) BuildResponse(hookCtx *hook.Context, decision string, message string, additionalContext string) any {
	reason := message
	if additionalContext != "" {
		if reason != "" {
			reason = reason + " — " + additionalContext
		} else {
			reason = additionalContext
		}
	}
	return windsurfResponse{
		CascadeDecision: decision,
		Reason:          reason,
	}
}

// ConfigPaths returns Windsurf config file paths.
func (p *WindsurfProvider) ConfigPaths(projectDir string) []string {
	return []string{
		filepath.Join(projectDir, ".windsurf", "hooks.json"),
	}
}

// mapWindsurfEvent maps Windsurf Cascade event names to canonical events.
// Windsurf uses PascalCase with a "Cascade" prefix for its native events and
// also accepts the Claude-compatible names for cross-provider payloads.
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
