package ui

import (
	"os"
)

// UIConfig holds the global UI configuration.
type UIConfig struct {
	NoColor bool
	Verbose bool
	CIMode  bool
}

// Config is the global UI configuration instance.
var Config = &UIConfig{}

// Initialize sets up the UI configuration based on flags and environment.
func Initialize(noColor, verbose, ciMode bool) {
	Config.NoColor = noColor || shouldDisableColor()
	Config.Verbose = verbose
	Config.CIMode = ciMode || isCIEnvironment()

	if Config.NoColor || Config.CIMode {
		disableAllColors()
	}
}

// isCIEnvironment detects CI environments.
func isCIEnvironment() bool {
	ciEnvs := []string{"CI", "GITHUB_ACTIONS", "GITLAB_CI", "JENKINS", "BUILDKITE"}
	for _, env := range ciEnvs {
		if os.Getenv(env) == "true" || os.Getenv(env) == "1" {
			return true
		}
	}
	return false
}

// shouldDisableColor determines if colors should be disabled.
func shouldDisableColor() bool {
	if isCIEnvironment() {
		return true
	}
	if os.Getenv("NO_COLOR") != "" {
		return true
	}
	term := os.Getenv("TERM")
	if term == "dumb" || term == "" {
		return true
	}
	return false
}

// disableAllColors removes colors from all styles.
func disableAllColors() {
	TitleStyle = TitleStyle.UnsetForeground()
	HeaderStyle = HeaderStyle.UnsetForeground()
	SuccessStyle = SuccessStyle.UnsetForeground()
	ErrorStyle = ErrorStyle.UnsetForeground()
	WarningStyle = WarningStyle.UnsetForeground()
	InfoStyle = InfoStyle.UnsetForeground()
	MutedStyle = MutedStyle.UnsetForeground()
	DimStyle = DimStyle.UnsetForeground()
	ProgressBarStyle = ProgressBarStyle.UnsetForeground()
	CounterStyle = CounterStyle.UnsetForeground()
	BoxStyle = BoxStyle.UnsetBorderForeground()
	SummaryBoxStyle = SummaryBoxStyle.UnsetBorderForeground()
	SelectedStyle = SelectedStyle.UnsetForeground().UnsetBackground()
}

// IsVerbose returns true if verbose mode is enabled.
func IsVerbose() bool {
	return Config.Verbose
}

// IsCIMode returns true if running in CI mode.
func IsCIMode() bool {
	return Config.CIMode
}
