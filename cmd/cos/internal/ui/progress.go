package ui

import (
	"fmt"
	"strings"
)

// Step prints a styled step indicator with an icon and message.
func Step(icon, message string) {
	switch icon {
	case IconSuccess, IconCheck:
		fmt.Printf("%s %s\n", SuccessStyle.Render(icon), message)
	case IconError, IconCross:
		fmt.Printf("%s %s\n", ErrorStyle.Render(icon), message)
	case IconWarning:
		fmt.Printf("%s %s\n", WarningStyle.Render(icon), message)
	default:
		fmt.Printf("%s %s\n", InfoStyle.Render(icon), message)
	}
}

// AuditGate prints a styled audit gate result.
// status is one of: "pass", "fail", "warning", "skipped".
func AuditGate(status, name, detail string) {
	var icon string
	switch status {
	case "pass":
		icon = SuccessStyle.Render(IconSuccess)
	case "fail":
		icon = ErrorStyle.Render(IconError)
	case "warning":
		icon = WarningStyle.Render(IconWarning)
	default:
		icon = InfoStyle.Render(IconInfo)
	}

	label := HeaderStyle.Render(capitalize(name))
	fmt.Printf("  %s %s: %s\n", icon, label, detail)
}

// ExportLine prints a styled export installation line.
// action is typically "+" for install or "-" for uninstall.
func ExportLine(action, path, exportType string) {
	var styledAction string
	switch action {
	case "+":
		styledAction = SuccessStyle.Render("+")
	case "-":
		styledAction = ErrorStyle.Render("-")
	default:
		styledAction = InfoStyle.Render(action)
	}

	typeBadge := MutedStyle.Render(fmt.Sprintf("(%s)", exportType))
	fmt.Printf("  %s %s %s\n", styledAction, path, typeBadge)
}

// Summary prints a styled summary box with a title and content lines.
func Summary(title string, lines []string) {
	content := strings.Join(lines, "\n")
	box := SummaryBoxStyle.Render(
		HeaderStyle.Render(title) + "\n" + content,
	)
	fmt.Println(box)
}

// capitalize returns the string with the first letter uppercased.
func capitalize(s string) string {
	if s == "" {
		return s
	}
	return strings.ToUpper(s[:1]) + s[1:]
}
