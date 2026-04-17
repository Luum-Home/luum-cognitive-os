package provider

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"

	"github.com/luum/cos-dispatch/pkg/hook"
)

// cursorPayload represents the JSON structure Cursor sends on stdin.
// Cursor uses camelCase event names (e.g. "beforeShellExecution") and may
// include extra vendor fields such as model_id that are not present in the
// Claude Code format.
type cursorPayload struct {
	HookEvent string          `json:"hook_event"`
	ToolName  string          `json:"tool_name"`
	ToolInput json.RawMessage `json:"tool_input"`
	SessionID string          `json:"session_id"`
	ExitCode  *int            `json:"exit_code,omitempty"`
	Output    string          `json:"output,omitempty"`
	// ModelID is a Cursor-specific field identifying the model that invoked the hook.
	ModelID string `json:"model_id,omitempty"`
}

// cursorToolInput represents Cursor tool_input fields.
// Cursor preserves the standard tool_input keys used by Claude Code.
type cursorToolInput struct {
	Command  string `json:"command,omitempty"`
	FilePath string `json:"file_path,omitempty"`
	Content  string `json:"content,omitempty"`
	Prompt   string `json:"prompt,omitempty"`
	Pattern  string `json:"pattern,omitempty"`
}

// cursorResponse is the vendor-conformant response envelope Cursor expects.
// Cursor hooks read "action" ("allow" or "deny") and an optional "message".
type cursorResponse struct {
	Action  string `json:"action"`
	Message string `json:"message,omitempty"`
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

// Detect returns true when CURSOR_SESSION_ID is set (the primary runtime
// signal Cursor injects) or CURSOR_PROJECT_DIR is set.  The .cursor/
// directory check is an additional heuristic used only when env vars are
// absent; it is intentionally last so that a checked-in .cursor/ in a
// non-Cursor session does not cause a false positive.
func (p *CursorProvider) Detect() bool {
	if os.Getenv("CURSOR_SESSION_ID") != "" {
		return true
	}
	if os.Getenv("CURSOR_PROJECT_DIR") != "" {
		return true
	}
	// Heuristic: .cursor/ directory in CWD.
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

	// Populate ProjectDir from Cursor-specific or fallback env vars.
	if dir := os.Getenv("CURSOR_PROJECT_DIR"); dir != "" {
		ctx.ProjectDir = dir
	} else if dir := os.Getenv("CLAUDE_PROJECT_DIR"); dir != "" {
		// cos-dispatch may be launched inside a Cursor session that also has
		// CLAUDE_PROJECT_DIR set (e.g. Claude Code running inside Cursor).
		ctx.ProjectDir = dir
	}

	// Preserve Cursor-specific model_id in context metadata.
	if payload.ModelID != "" {
		ctx.SetMetadata("cursor_model_id", payload.ModelID)
	}

	return ctx, nil
}

// BuildResponse returns Cursor's vendor-conformant response envelope.
// Cursor hooks expect {"action":"allow"|"deny","message":"..."}.
// The additionalContext argument is appended to message when non-empty.
func (p *CursorProvider) BuildResponse(hookCtx *hook.Context, decision string, message string, additionalContext string) any {
	msg := message
	if additionalContext != "" {
		if msg != "" {
			msg = msg + " — " + additionalContext
		} else {
			msg = additionalContext
		}
	}
	return cursorResponse{
		Action:  decision,
		Message: msg,
	}
}

// ConfigPaths returns Cursor config file paths.
func (p *CursorProvider) ConfigPaths(projectDir string) []string {
	return []string{
		filepath.Join(projectDir, ".cursor", "hooks.json"),
	}
}

// mapCursorEvent maps Cursor camelCase event names to canonical events.
// Cursor uses camelCase (beforeShellExecution, afterFileEdit) unlike Claude
// which uses PascalCase (PreToolUse, PostToolUse).
func mapCursorEvent(event string) hook.CanonicalEvent {
	switch event {
	case "beforeShellExecution":
		return hook.CanonicalEventBeforeTool
	case "afterFileEdit", "afterFileWrite", "afterShellExecution":
		return hook.CanonicalEventAfterTool
	case "sessionStart":
		return hook.CanonicalEventSessionStart
	case "sessionEnd":
		return hook.CanonicalEventSessionEnd
	default:
		return hook.CanonicalEventUnknown
	}
}
