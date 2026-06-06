package provider

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"

	"github.com/luum/cos-dispatch/pkg/hook"
)

// devinPayload represents the JSON structure Devin (Codeium Cascade) sends
// on stdin.  Devin extends the base hook format with a "cascade_context"
// object that carries workspace metadata.
type devinPayload struct {
	HookEvent string          `json:"hook_event"`
	ToolName  string          `json:"tool_name"`
	ToolInput json.RawMessage `json:"tool_input"`
	SessionID string          `json:"session_id"`
	ExitCode  *int            `json:"exit_code,omitempty"`
	Output    string          `json:"output,omitempty"`
	// CascadeContext is a Devin-specific envelope carrying workspace metadata.
	CascadeContext *devinCascadeContext `json:"cascade_context,omitempty"`
}

// devinCascadeContext contains Devin-specific workspace metadata injected
// by the Cascade runtime alongside every hook event.
type devinCascadeContext struct {
	Workspace  string `json:"workspace,omitempty"`
	ActiveFile string `json:"active_file,omitempty"`
}

// devinToolInput represents Devin tool_input fields.
type devinToolInput struct {
	Command  string `json:"command,omitempty"`
	FilePath string `json:"file_path,omitempty"`
	Content  string `json:"content,omitempty"`
	Prompt   string `json:"prompt,omitempty"`
	Pattern  string `json:"pattern,omitempty"`
}

// devinResponse is the vendor-conformant response envelope Devin expects.
// Cascade hooks read "cascadeDecision" ("allow" or "deny") and an optional
// "reason" string.
type devinResponse struct {
	CascadeDecision string `json:"cascadeDecision"`
	Reason          string `json:"reason,omitempty"`
}

// DevinProvider adapts Devin (Codeium Cascade) hook payloads to the
// canonical format.
type DevinProvider struct{}

// NewDevinProvider creates a Devin provider adapter.
func NewDevinProvider() *DevinProvider {
	return &DevinProvider{}
}

func (p *DevinProvider) Name() hook.Provider {
	return hook.ProviderDevin
}

// Detect returns true when DEVIN_SESSION_ID or CASCADE_CONTEXT env vars are
// set.  DEVIN_SESSION_ID is injected by the Devin runtime; CASCADE_CONTEXT
// is the fallback variable set when Cascade is active but hasn't created a full
// session object yet (e.g. during tool initialisation).
func (p *DevinProvider) Detect() bool {
	return os.Getenv("DEVIN_SESSION_ID") != "" || os.Getenv("CASCADE_CONTEXT") != ""
}

// Parse converts Devin JSON into a canonical hook.Context.
// The cascade_context object (if present) is stored in Context metadata so
// downstream validators can access workspace information without re-parsing.
func (p *DevinProvider) Parse(raw []byte) (*hook.Context, error) {
	var payload devinPayload
	if err := json.Unmarshal(raw, &payload); err != nil {
		return nil, fmt.Errorf("devin: parse payload: %w", err)
	}

	var ti devinToolInput
	if len(payload.ToolInput) > 0 {
		if err := json.Unmarshal(payload.ToolInput, &ti); err != nil {
			return nil, fmt.Errorf("devin: parse tool_input: %w", err)
		}
	}

	ctx := &hook.Context{
		Provider:  hook.ProviderDevin,
		Event:     mapDevinEvent(payload.HookEvent),
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

	// Populate ProjectDir from Devin-specific env vars, falling back to the
	// cascade_context workspace field when available.
	if dir := os.Getenv("DEVIN_PROJECT_DIR"); dir != "" {
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

// BuildResponse returns Devin's vendor-conformant response envelope.
// Cascade hooks expect {"cascadeDecision":"allow"|"deny","reason":"..."}.
func (p *DevinProvider) BuildResponse(hookCtx *hook.Context, decision string, message string, additionalContext string) any {
	reason := message
	if additionalContext != "" {
		if reason != "" {
			reason = reason + " — " + additionalContext
		} else {
			reason = additionalContext
		}
	}
	return devinResponse{
		CascadeDecision: decision,
		Reason:          reason,
	}
}

// ConfigPaths returns Devin config file paths.
func (p *DevinProvider) ConfigPaths(projectDir string) []string {
	return []string{
		filepath.Join(projectDir, ".devin", "hooks.json"),
	}
}

// mapDevinEvent maps Devin Cascade event names to canonical events.
// Devin uses PascalCase with a "Cascade" prefix for its native events and
// also accepts the Claude-compatible names for cross-provider payloads.
func mapDevinEvent(event string) hook.CanonicalEvent {
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
