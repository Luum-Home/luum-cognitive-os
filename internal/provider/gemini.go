package provider

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"

	"github.com/luum/cos-dispatch/pkg/hook"
)

// geminiPayload represents the JSON structure Gemini CLI sends on stdin.
type geminiPayload struct {
	HookEvent string          `json:"hook_event"`
	ToolName  string          `json:"tool_name"`
	ToolInput json.RawMessage `json:"tool_input"`
	SessionID string          `json:"session_id"`
	ExitCode  *int            `json:"exit_code,omitempty"`
	Output    string          `json:"output,omitempty"`
}

// geminiToolInput represents Gemini CLI tool_input fields.
type geminiToolInput struct {
	Command  string `json:"command,omitempty"`
	FilePath string `json:"file_path,omitempty"`
	Content  string `json:"content,omitempty"`
	Prompt   string `json:"prompt,omitempty"`
	Pattern  string `json:"pattern,omitempty"`
}

// GeminiProvider adapts Google Gemini CLI hook payloads to the canonical format.
type GeminiProvider struct{}

// NewGeminiProvider creates a Gemini CLI provider adapter.
func NewGeminiProvider() *GeminiProvider {
	return &GeminiProvider{}
}

func (p *GeminiProvider) Name() hook.Provider {
	return hook.ProviderGemini
}

// Detect checks for GEMINI_PROJECT_DIR or GEMINI_CWD environment variables.
func (p *GeminiProvider) Detect() bool {
	return os.Getenv("GEMINI_PROJECT_DIR") != "" || os.Getenv("GEMINI_CWD") != ""
}

// Parse converts Gemini CLI JSON into a canonical hook.Context.
func (p *GeminiProvider) Parse(raw []byte) (*hook.Context, error) {
	var payload geminiPayload
	if err := json.Unmarshal(raw, &payload); err != nil {
		return nil, fmt.Errorf("gemini: parse payload: %w", err)
	}

	var ti geminiToolInput
	if len(payload.ToolInput) > 0 {
		if err := json.Unmarshal(payload.ToolInput, &ti); err != nil {
			return nil, fmt.Errorf("gemini: parse tool_input: %w", err)
		}
	}

	ctx := &hook.Context{
		Provider:  hook.ProviderGemini,
		Event:     mapGeminiEvent(payload.HookEvent),
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

	if dir := os.Getenv("GEMINI_PROJECT_DIR"); dir != "" {
		ctx.ProjectDir = dir
	} else if cwd := os.Getenv("GEMINI_CWD"); cwd != "" {
		ctx.CWD = cwd
	}

	return ctx, nil
}

// BuildResponse returns Gemini CLI's expected JSON response format.
func (p *GeminiProvider) BuildResponse(hookCtx *hook.Context, decision string, message string, additionalContext string) any {
	return map[string]any{
		"hookSpecificOutput": map[string]any{
			"permissionDecision": decision,
			"reason":             message,
			"additionalContext":  additionalContext,
		},
	}
}

// ConfigPaths returns Gemini CLI config file paths.
func (p *GeminiProvider) ConfigPaths(projectDir string) []string {
	return []string{
		filepath.Join(projectDir, ".gemini", "settings.json"),
	}
}

// mapGeminiEvent maps Gemini CLI event names to canonical events.
func mapGeminiEvent(event string) hook.CanonicalEvent {
	switch event {
	case "BeforeTool":
		return hook.CanonicalEventBeforeTool
	case "AfterTool":
		return hook.CanonicalEventAfterTool
	case "SessionStart":
		return hook.CanonicalEventSessionStart
	case "SessionEnd":
		return hook.CanonicalEventSessionEnd
	default:
		return hook.CanonicalEventUnknown
	}
}
