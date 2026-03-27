package manifest

// Manifest is the top-level structure representing a cos-package.yaml file.
type Manifest struct {
	// Package identity.
	Name        string   `yaml:"name"`
	Version     string   `yaml:"version"`
	Description string   `yaml:"description"`
	Authors     []string `yaml:"authors,omitempty"`
	License     string   `yaml:"license"`
	Repository  string   `yaml:"repository,omitempty"`
	Homepage    string   `yaml:"homepage,omitempty"`
	Keywords    []string `yaml:"keywords,omitempty"`
	CosVersion  string   `yaml:"cos_version,omitempty"`

	// What this package provides.
	Provides []string `yaml:"provides"`

	// Exported components.
	Exports []Export `yaml:"exports"`

	// Dependencies on other cos packages.
	Dependencies map[string]Dependency `yaml:"dependencies,omitempty"`

	// Dependency groups for conditional installation.
	Groups map[string]map[string]Dependency `yaml:"groups,omitempty"`

	// Conditional exports gated by feature flags.
	Features map[string]Feature `yaml:"features,omitempty"`

	// Lifecycle scripts.
	Scripts map[string]string `yaml:"scripts,omitempty"`

	// Monorepo workspace configuration.
	Workspace *Workspace `yaml:"workspace,omitempty"`

	// Runtime requirements.
	Platform *Platform `yaml:"platform,omitempty"`

	// Publishing configuration.
	Publish *PublishConfig `yaml:"publish,omitempty"`
}

// Export declares a file to install, mapped to its destination type.
type Export struct {
	// Path relative to package root.
	Source string `yaml:"source"`

	// Destination category: skill, rule, hook, template, agent.
	Type string `yaml:"type"`

	// One-line description for catalog entries.
	Description string `yaml:"description,omitempty"`

	// Contextual triggers for skills/rules.
	Triggers []string `yaml:"triggers,omitempty"`

	// Hook lifecycle event. Required when Type is "hook".
	// Values: PreToolUse, PostToolUse, SessionStart, Stop.
	HookEvent string `yaml:"hook_event,omitempty"`

	// Hook matcher pattern. Required when Type is "hook".
	HookMatcher string `yaml:"hook_matcher,omitempty"`

	// Whether this rule is always active (loaded at startup).
	AlwaysActive bool `yaml:"always_active,omitempty"`
}

// Dependency specifies a required package and its version constraint.
type Dependency struct {
	// Semver version constraint.
	Version string `yaml:"version"`

	// Optional: only install when these features are enabled.
	Features []string `yaml:"features,omitempty"`
}

// Feature defines conditional exports gated by a feature flag.
type Feature struct {
	// Whether this feature is enabled by default.
	Default bool `yaml:"default,omitempty"`

	// Human-readable description.
	Description string `yaml:"description,omitempty"`

	// Additional exports enabled by this feature.
	Exports []Export `yaml:"exports,omitempty"`

	// Additional dependencies required by this feature.
	Dependencies map[string]Dependency `yaml:"dependencies,omitempty"`
}

// Workspace configures monorepo support.
type Workspace struct {
	// Relative paths to sub-packages.
	Members []string `yaml:"members,omitempty"`

	// Fields applied to all members unless overridden.
	Shared *SharedConfig `yaml:"shared,omitempty"`

	// Dependencies shared across all workspace members.
	SharedDependencies map[string]Dependency `yaml:"shared_dependencies,omitempty"`
}

// SharedConfig holds fields shared across workspace members.
type SharedConfig struct {
	License string   `yaml:"license,omitempty"`
	Authors []string `yaml:"authors,omitempty"`
}

// Platform specifies runtime requirements.
type Platform struct {
	// Operating systems: linux, darwin, windows.
	OS []string `yaml:"os,omitempty"`

	// Required shell: bash, zsh, fish, sh.
	Shell string `yaml:"shell,omitempty"`

	// External tools that must be in PATH.
	Tools []ToolRequirement `yaml:"tools,omitempty"`

	// IDE compatibility: claude-code, cursor, windsurf, cline.
	IDE []string `yaml:"ide,omitempty"`
}

// ToolRequirement specifies an external tool and its version constraint.
type ToolRequirement struct {
	Name    string `yaml:"name"`
	Version string `yaml:"version,omitempty"`
}

// PublishConfig configures package publishing.
type PublishConfig struct {
	// Glob patterns for files to include.
	Include []string `yaml:"include,omitempty"`

	// Glob patterns for files to exclude.
	Exclude []string `yaml:"exclude,omitempty"`

	// Target registry. Default: "github".
	Registry string `yaml:"registry,omitempty"`

	// Minimum quality score to publish (0-100). Default: 40.
	MinScore *int `yaml:"min_score,omitempty"`
}
