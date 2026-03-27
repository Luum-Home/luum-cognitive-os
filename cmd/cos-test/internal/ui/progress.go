package ui

import (
	"fmt"
	"strings"
	"time"

	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/lipgloss"
)

// ProgressModel is a Bubbletea model for showing test run progress.
type ProgressModel struct {
	Total       int
	Current     int
	Passed      int
	Failed      int
	Skipped     int
	CurrentTest string
	StartTime   time.Time
	Done        bool
	Err         error
	width       int
	spinIdx     int
}

// TickMsg triggers spinner animation.
type TickMsg time.Time

// TestProgressMsg updates test progress.
type TestProgressMsg struct {
	TestName string
	Status   string // "passed", "failed", "skipped", "error"
}

// TestDoneMsg signals all tests are done.
type TestDoneMsg struct {
	Err error
}

// NewProgressModel creates a new progress model.
func NewProgressModel(total int) ProgressModel {
	return ProgressModel{
		Total:     total,
		StartTime: time.Now(),
		width:     60,
	}
}

// Init implements tea.Model.
func (m ProgressModel) Init() tea.Cmd {
	return tickCmd()
}

func tickCmd() tea.Cmd {
	return tea.Tick(100*time.Millisecond, func(t time.Time) tea.Msg {
		return TickMsg(t)
	})
}

// Update implements tea.Model.
func (m ProgressModel) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
	switch msg := msg.(type) {
	case tea.KeyMsg:
		if msg.String() == "q" || msg.String() == "ctrl+c" {
			return m, tea.Quit
		}

	case tea.WindowSizeMsg:
		m.width = msg.Width
		if m.width > 80 {
			m.width = 80
		}

	case TickMsg:
		m.spinIdx = (m.spinIdx + 1) % len(SpinnerFrames)
		if !m.Done {
			return m, tickCmd()
		}

	case TestProgressMsg:
		m.Current++
		m.CurrentTest = msg.TestName
		switch msg.Status {
		case "passed":
			m.Passed++
		case "failed":
			m.Failed++
		case "skipped":
			m.Skipped++
		case "error":
			m.Failed++
		}

	case TestDoneMsg:
		m.Done = true
		m.Err = msg.Err
		return m, tea.Quit
	}

	return m, nil
}

// View implements tea.Model.
func (m ProgressModel) View() string {
	var b strings.Builder

	elapsed := time.Since(m.StartTime).Round(time.Millisecond)

	// Title.
	b.WriteString(TitleStyle.Render("Cognitive OS Test Runner"))
	b.WriteString("\n\n")

	// Progress bar.
	barWidth := 40
	if m.width > 0 && m.width < 60 {
		barWidth = m.width - 20
	}
	bar := ProgressBar(m.Current, m.Total, barWidth)
	b.WriteString(bar)
	b.WriteString("\n\n")

	// Counters.
	passStr := SuccessStyle.Render(fmt.Sprintf("%s %d passed", IconCheck, m.Passed))
	failStr := ErrorStyle.Render(fmt.Sprintf("%s %d failed", IconCross, m.Failed))
	skipStr := MutedStyle.Render(fmt.Sprintf("~ %d skipped", m.Skipped))
	b.WriteString(fmt.Sprintf("  %s  %s  %s", passStr, failStr, skipStr))
	b.WriteString("\n\n")

	// Current test.
	if !m.Done && m.CurrentTest != "" {
		spinner := SpinnerFrames[m.spinIdx]
		b.WriteString(InfoStyle.Render(fmt.Sprintf("  %s %s", spinner, truncate(m.CurrentTest, m.width-6))))
		b.WriteString("\n")
	}

	// Elapsed time.
	b.WriteString(MutedStyle.Render(fmt.Sprintf("  Elapsed: %s", elapsed)))
	b.WriteString("\n")

	if m.Done {
		b.WriteString("\n")
		if m.Failed > 0 {
			b.WriteString(ErrorStyle.Render(fmt.Sprintf("  %s %d tests failed", IconError, m.Failed)))
		} else {
			b.WriteString(SuccessStyle.Render(fmt.Sprintf("  %s All %d tests passed", IconSuccess, m.Passed)))
		}
		b.WriteString("\n")
	}

	return lipgloss.NewStyle().Padding(1, 2).Render(b.String())
}

func truncate(s string, maxLen int) string {
	if maxLen <= 0 {
		maxLen = 40
	}
	if len(s) <= maxLen {
		return s
	}
	return s[:maxLen-3] + "..."
}
