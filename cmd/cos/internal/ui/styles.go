package ui

import (
	"github.com/charmbracelet/lipgloss"
)

// Color palette — Cognitive OS branding.
const (
	ColorPrimary = "99"  // Purple (COS brand)
	ColorSuccess = "46"  // Green
	ColorError   = "196" // Red
	ColorWarning = "214" // Orange
	ColorInfo    = "69"  // Blue
	ColorMuted   = "241" // Gray
	ColorAccent  = "86"  // Cyan
	ColorDim     = "245" // Light gray
)

// Global styles.
var (
	TitleStyle = lipgloss.NewStyle().
			Bold(true).
			Foreground(lipgloss.Color(ColorPrimary)).
			MarginBottom(1)

	HeaderStyle = lipgloss.NewStyle().
			Bold(true).
			Foreground(lipgloss.Color(ColorAccent))

	SuccessStyle = lipgloss.NewStyle().
			Foreground(lipgloss.Color(ColorSuccess))

	ErrorStyle = lipgloss.NewStyle().
			Foreground(lipgloss.Color(ColorError))

	WarningStyle = lipgloss.NewStyle().
			Foreground(lipgloss.Color(ColorWarning))

	InfoStyle = lipgloss.NewStyle().
			Foreground(lipgloss.Color(ColorInfo))

	MutedStyle = lipgloss.NewStyle().
			Foreground(lipgloss.Color(ColorMuted))

	DimStyle = lipgloss.NewStyle().
			Foreground(lipgloss.Color(ColorDim))

	BoxStyle = lipgloss.NewStyle().
			Border(lipgloss.RoundedBorder()).
			BorderForeground(lipgloss.Color(ColorMuted)).
			Padding(1, 2)

	SummaryBoxStyle = lipgloss.NewStyle().
			Border(lipgloss.DoubleBorder()).
			BorderForeground(lipgloss.Color(ColorAccent)).
			Padding(1, 2).
			MarginTop(1)
)

// Icons.
const (
	IconSuccess = "[PASS]"
	IconError   = "[FAIL]"
	IconWarning = "[WARN]"
	IconInfo    = "[INFO]"
	IconCheck   = "+"
	IconCross   = "x"
	IconArrow   = ">"
	IconBullet  = "-"
)
