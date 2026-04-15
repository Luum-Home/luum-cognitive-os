// Package provider implements provider detection, normalization, and response
// building for AI coding agents. Each provider adapter converts agent-specific
// JSON into the canonical hook.Context and builds agent-specific responses.
package provider

import (
	"github.com/luum/cos-dispatch/pkg/hook"
)

// Provider normalizes agent-specific JSON into canonical hook.Context
// and builds agent-specific responses from validation results.
type Provider interface {
	// Name returns the canonical provider identifier.
	Name() hook.Provider

	// Detect returns true if the current environment was launched by this provider.
	Detect() bool

	// Parse converts raw JSON from stdin into a canonical hook.Context.
	Parse(raw []byte) (*hook.Context, error)

	// BuildResponse constructs the provider-specific JSON response.
	BuildResponse(hookCtx *hook.Context, decision string, message string, additionalContext string) any

	// ConfigPaths returns the provider-specific config file paths relative to projectDir.
	ConfigPaths(projectDir string) []string
}

// Registry manages provider detection and selection.
type Registry struct {
	providers []Provider
	fallback  Provider
}

// NewRegistry creates a Registry with all known providers.
// Claude is the default fallback since it's the most common provider.
func NewRegistry() *Registry {
	return &Registry{
		providers: []Provider{
			NewClaudeProvider(),
			NewCodexProvider(),
			NewGeminiProvider(),
			NewCursorProvider(),
			NewWindsurfProvider(),
		},
		fallback: NewClaudeProvider(),
	}
}

// Detect returns the first provider whose environment is detected,
// or the fallback provider (Claude) if none match.
func (r *Registry) Detect() Provider {
	for _, p := range r.providers {
		if p.Detect() {
			return p
		}
	}
	return r.fallback
}

// Get returns the provider with the given name, or (nil, false) if not found.
func (r *Registry) Get(name hook.Provider) (Provider, bool) {
	for _, p := range r.providers {
		if p.Name() == name {
			return p, true
		}
	}
	return nil, false
}
