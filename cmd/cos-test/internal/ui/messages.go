package ui

import (
	"fmt"
	"strings"

	"github.com/charmbracelet/lipgloss"
)

// MessageType represents different types of messages.
type MessageType int

const (
	MessageSuccess MessageType = iota
	MessageError
	MessageWarning
	MessageInfo
	MessageProgress
)

// Message represents a styled console message.
type Message struct {
	Type    MessageType
	Icon    string
	Text    string
	Details string
}

// Print outputs the message to stdout with proper styling.
func (m Message) Print() {
	fmt.Println(m.Render())
}

// Render creates the styled string representation.
func (m Message) Render() string {
	if Config.NoColor {
		msg := fmt.Sprintf("%s %s", m.Icon, m.Text)
		if m.Details != "" {
			msg += fmt.Sprintf("\n   %s", m.Details)
		}
		return msg
	}

	var style lipgloss.Style
	switch m.Type {
	case MessageSuccess:
		style = SuccessStyle
	case MessageError:
		style = ErrorStyle
	case MessageWarning:
		style = WarningStyle
	case MessageInfo:
		style = InfoStyle
	case MessageProgress:
		style = ProgressBarStyle
	}

	msg := fmt.Sprintf("%s %s", m.Icon, m.Text)
	if m.Details != "" {
		msg += "\n" + MutedStyle.Render(fmt.Sprintf("   %s", m.Details))
	}
	return style.Render(msg)
}

// WithDetails adds details to a message.
func (m Message) WithDetails(details string) Message {
	m.Details = details
	return m
}

// Quick message constructors.

// Success creates a success message.
func Success(text string) Message {
	return Message{Type: MessageSuccess, Icon: IconSuccess, Text: text}
}

// Error creates an error message.
func Error(text string) Message {
	return Message{Type: MessageError, Icon: IconError, Text: text}
}

// Warn creates a warning message.
func Warn(text string) Message {
	return Message{Type: MessageWarning, Icon: IconWarning, Text: text}
}

// Info creates an info message.
func Info(text string) Message {
	return Message{Type: MessageInfo, Icon: IconInfo, Text: text}
}

// Progress creates a progress message.
func Progress(text string) Message {
	return Message{Type: MessageProgress, Icon: IconProgress, Text: text}
}

// Title prints a styled title.
func Title(text string) {
	fmt.Println(TitleStyle.Render(text))
}

// Header prints a styled header.
func Header(text string) {
	fmt.Println(HeaderStyle.Render(text))
}

// Separator creates a visual separator.
func Separator() {
	fmt.Println(MutedStyle.Render(strings.Repeat("-", 60)))
}

// ProgressBar creates a visual progress bar string.
func ProgressBar(current, total, width int) string {
	if total == 0 {
		return ""
	}
	if width <= 0 {
		width = 40
	}

	pct := float64(current) / float64(total)
	filled := int(pct * float64(width))
	if filled > width {
		filled = width
	}

	bar := strings.Repeat(ProgressFull, filled) + strings.Repeat(ProgressEmpty, width-filled)
	return ProgressBarStyle.Render(
		fmt.Sprintf("[%s] %d%% (%d/%d)", bar, int(pct*100), current, total),
	)
}

// Counter creates a styled counter.
func Counter(label string, count int) string {
	return fmt.Sprintf("%s: %s", label, CounterStyle.Render(fmt.Sprintf("%d", count)))
}

// Box creates a styled box around content.
func Box(title, content string) string {
	styledTitle := HeaderStyle.Render(title)
	return BoxStyle.Render(styledTitle + "\n\n" + content)
}

// SummaryBox creates a special summary box.
func SummaryBox(title, content string) string {
	styledTitle := HeaderStyle.Render(title)
	return SummaryBoxStyle.Render(styledTitle + "\n\n" + content)
}

// List creates a bulleted list.
func List(items []string) string {
	result := make([]string, 0, len(items))
	for _, item := range items {
		result = append(result, fmt.Sprintf("   %s %s", IconBullet, item))
	}
	return strings.Join(result, "\n")
}
