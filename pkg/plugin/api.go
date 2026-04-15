// Package plugin defines the API types for external cos-dispatch plugins.
//
// Plugins communicate with the dispatcher over JSON. A plugin receives a
// ValidateRequest and returns a ValidateResponse indicating whether the
// tool invocation should be allowed, blocked, or annotated with a message.
package plugin

// ValidateRequest is sent to an external plugin for validation.
type ValidateRequest struct {
	// Provider is the AI agent provider name (e.g., "claude", "codex").
	Provider string `json:"provider"`

	// EventName is the canonical event name (e.g., "before_tool").
	EventName string `json:"event_name"`

	// ToolFamily is the normalized tool family (e.g., "Bash", "Edit").
	ToolFamily string `json:"tool_family"`

	// Command is the shell command, populated for Bash tool invocations.
	Command string `json:"command,omitempty"`

	// FilePath is the target file path, populated for file tool invocations.
	FilePath string `json:"file_path,omitempty"`

	// Config holds plugin-specific configuration passed from cos-dispatch config.
	Config map[string]any `json:"config,omitempty"`
}

// ValidateResponse is returned by an external plugin after validation.
type ValidateResponse struct {
	// Passed indicates whether the validation passed.
	Passed bool `json:"passed"`

	// ShouldBlock indicates whether the tool invocation should be blocked.
	// When true, the dispatcher prevents the tool from executing.
	ShouldBlock bool `json:"should_block"`

	// Message is a human-readable explanation of the validation result.
	Message string `json:"message,omitempty"`

	// ErrorCode is a machine-readable error identifier (e.g., "COS-SEC-001").
	ErrorCode string `json:"error_code,omitempty"`

	// FixHint suggests how the user can fix the issue.
	FixHint string `json:"fix_hint,omitempty"`
}

// PluginInfo describes an external plugin's identity and metadata.
type PluginInfo struct {
	// Name is the plugin's unique identifier.
	Name string `json:"name"`

	// Version is the plugin's semantic version.
	Version string `json:"version"`

	// Description is a short summary of what the plugin does.
	Description string `json:"description"`

	// Author is the plugin author or maintainer.
	Author string `json:"author,omitempty"`
}
