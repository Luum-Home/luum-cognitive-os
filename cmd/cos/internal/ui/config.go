package ui

import (
	"os"
)

// UIConfig holds the global UI configuration.
type UIConfig struct {
	NoColor bool
	Verbose bool
}

// Config is the global UI configuration instance.
var Config = &UIConfig{}

// Initialize sets up the UI configuration based on flags and environment.
func Initialize(noColor, verbose bool) {
	Config.NoColor = noColor || shouldDisableColor()
	Config.Verbose = verbose

	if Config.NoColor {
		disableAllColors()
	}
}

// shouldDisableColor determines if colors should be disabled.
func shouldDisableColor() bool {
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
	BoxStyle = BoxStyle.UnsetBorderForeground()
	SummaryBoxStyle = SummaryBoxStyle.UnsetBorderForeground()
}

// IsVerbose returns true if verbose mode is enabled.
func IsVerbose() bool {
	return Config.Verbose
}
