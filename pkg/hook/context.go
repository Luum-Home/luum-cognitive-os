// Package hook provides core types for the cos-dispatch hook context.
//
// The Context type is the canonical representation of any AI agent hook
// invocation, normalized across providers (Claude, Codex, Gemini, Cursor,
// Windsurf). Provider-specific parsers produce a Context; validators and
// transformers consume it.
package hook

import "encoding/json"

// Provider identifies the AI agent that triggered the hook.
type Provider string

const (
	// ProviderUnknown represents an undetected or unrecognized provider.
	ProviderUnknown Provider = ""

	// ProviderClaude represents Claude Code hook payloads.
	ProviderClaude Provider = "claude"

	// ProviderCodex represents OpenAI Codex hook payloads.
	ProviderCodex Provider = "codex"

	// ProviderGemini represents Google Gemini CLI hook payloads.
	ProviderGemini Provider = "gemini"

	// ProviderCursor represents Cursor editor hook payloads.
	ProviderCursor Provider = "cursor"

	// ProviderWindsurf represents Windsurf (Codeium) hook payloads.
	ProviderWindsurf Provider = "windsurf"
)

// CanonicalEvent is the normalized, provider-agnostic hook event name.
type CanonicalEvent string

const (
	// CanonicalEventUnknown represents an unrecognized event.
	CanonicalEventUnknown CanonicalEvent = ""

	// CanonicalEventBeforeTool fires before a tool executes.
	CanonicalEventBeforeTool CanonicalEvent = "before_tool"

	// CanonicalEventAfterTool fires after a tool executes.
	CanonicalEventAfterTool CanonicalEvent = "after_tool"

	// CanonicalEventSessionStart fires when a new session begins.
	CanonicalEventSessionStart CanonicalEvent = "session_start"

	// CanonicalEventSessionEnd fires when a session terminates.
	CanonicalEventSessionEnd CanonicalEvent = "session_end"

	// CanonicalEventPromptSubmit fires when the user submits a prompt.
	CanonicalEventPromptSubmit CanonicalEvent = "prompt_submit"

	// CanonicalEventSubagentStart fires when a sub-agent is launched.
	CanonicalEventSubagentStart CanonicalEvent = "subagent_start"

	// CanonicalEventCompact fires on context compaction.
	CanonicalEventCompact CanonicalEvent = "compact"
)

// ToolType identifies the normalized tool being invoked.
type ToolType string

const (
	// ToolUnknown represents an unrecognized tool.
	ToolUnknown ToolType = ""

	// ToolBash represents the Bash/shell execution tool.
	ToolBash ToolType = "Bash"

	// ToolEdit represents the file-edit tool.
	ToolEdit ToolType = "Edit"

	// ToolWrite represents the file-write tool.
	ToolWrite ToolType = "Write"

	// ToolRead represents the file-read tool.
	ToolRead ToolType = "Read"

	// ToolAgent represents the sub-agent tool.
	ToolAgent ToolType = "Agent"

	// ToolGlob represents the file-glob tool.
	ToolGlob ToolType = "Glob"

	// ToolGrep represents the content-search tool.
	ToolGrep ToolType = "Grep"
)

// ToolInput contains the tool-specific input parameters, normalized across
// providers. Fields are populated selectively based on the tool type.
type ToolInput struct {
	// Command is the shell command for Bash tool.
	Command string `json:"command,omitempty"`

	// FilePath is the target file path for file operations.
	FilePath string `json:"file_path,omitempty"`

	// Content is the file content for Write tool.
	Content string `json:"content,omitempty"`

	// Description is a human-readable description of the tool invocation.
	Description string `json:"description,omitempty"`

	// Prompt is the prompt text for Agent tool.
	Prompt string `json:"prompt,omitempty"`

	// Pattern is the search pattern for Grep/Glob tools.
	Pattern string `json:"pattern,omitempty"`

	// Extra holds any additional provider-specific fields not captured above.
	Extra map[string]any `json:"extra,omitempty"`
}

// Context is the canonical hook invocation context. Provider-specific parsers
// produce it; validators and transformers consume it.
type Context struct {
	// Provider identifies the AI agent that triggered the hook.
	Provider Provider `json:"provider"`

	// Event is the normalized event that triggered the hook.
	Event CanonicalEvent `json:"event"`

	// ToolName identifies the tool being invoked.
	ToolName ToolType `json:"tool_name"`

	// ToolInput contains the tool-specific input parameters.
	ToolInput ToolInput `json:"tool_input"`

	// SessionID is the unique identifier for the agent session.
	SessionID string `json:"session_id"`

	// ProjectDir is the root project directory.
	ProjectDir string `json:"project_dir"`

	// CWD is the current working directory at invocation time.
	CWD string `json:"cwd"`

	// RawJSON holds the original unparsed input for advanced processing.
	// Excluded from JSON marshaling.
	RawJSON []byte `json:"-"`

	// ExitCode is the tool's exit code, populated only for AfterTool events.
	ExitCode *int `json:"exit_code,omitempty"`

	// ToolOutput is the tool's output text, populated only for AfterTool events.
	ToolOutput string `json:"tool_output,omitempty"`

	// Metadata holds arbitrary key-value data attached by transformers or plugins.
	Metadata map[string]any `json:"metadata,omitempty"`
}

// GetCommand returns the command from ToolInput.
func (c *Context) GetCommand() string {
	return c.ToolInput.Command
}

// GetFilePath returns the file path from ToolInput.
func (c *Context) GetFilePath() string {
	return c.ToolInput.FilePath
}

// GetContent returns the file content from ToolInput.
func (c *Context) GetContent() string {
	return c.ToolInput.Content
}

// IsBashTool reports whether the tool is a shell execution tool.
func (c *Context) IsBashTool() bool {
	return c.ToolName == ToolBash
}

// IsFileTool reports whether the tool is a file-mutation tool (Write or Edit).
func (c *Context) IsFileTool() bool {
	return c.ToolName == ToolWrite || c.ToolName == ToolEdit
}

// IsBeforeTool reports whether this is a pre-tool event.
func (c *Context) IsBeforeTool() bool {
	return c.Event == CanonicalEventBeforeTool
}

// IsAfterTool reports whether this is a post-tool event.
func (c *Context) IsAfterTool() bool {
	return c.Event == CanonicalEventAfterTool
}

// HasSessionID reports whether a session ID is present.
func (c *Context) HasSessionID() bool {
	return c.SessionID != ""
}

// SetMetadata sets a metadata key-value pair, initializing the map if needed.
func (c *Context) SetMetadata(key string, value any) {
	if c.Metadata == nil {
		c.Metadata = make(map[string]any)
	}
	c.Metadata[key] = value
}

// MarshalJSON implements json.Marshaler. It uses the default encoding but
// ensures RawJSON is excluded (via the json:"-" tag on the field).
func (c *Context) MarshalJSON() ([]byte, error) {
	// Alias avoids infinite recursion.
	type Alias Context
	return json.Marshal((*Alias)(c))
}

// UnmarshalJSON implements json.Unmarshaler. It captures the raw bytes
// in RawJSON alongside the structured fields.
func (c *Context) UnmarshalJSON(data []byte) error {
	type Alias Context
	aux := (*Alias)(c)
	if err := json.Unmarshal(data, aux); err != nil {
		return err
	}
	c.RawJSON = make([]byte, len(data))
	copy(c.RawJSON, data)
	return nil
}
