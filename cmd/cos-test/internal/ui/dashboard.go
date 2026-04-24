package ui

import (
	"fmt"
	"strings"
	"time"

	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/lipgloss"
)

// DashboardModel is the interactive Bubbletea dashboard.
type DashboardModel struct {
	// State.
	Categories   []string
	SelectedCat  int
	Tests        []DashboardTest
	Running      bool
	ShowFailures bool
	Width        int
	Height       int
	StartTime    time.Time
	spinIdx      int

	// Counters.
	TotalTests  int
	Passed      int
	Failed      int
	Skipped     int
	CurrentTest string

	// Failure details.
	Failures []FailureInfo

	// Quit signal.
	Quitting bool
}

// DashboardTest represents a test in the dashboard.
type DashboardTest struct {
	Name     string
	Category string
	Status   string // "pending", "running", "passed", "failed", "skipped"
	Duration time.Duration
}

// DashboardRunMsg requests running tests for the selected category.
type DashboardRunMsg struct {
	Category string
}

// DashboardTestUpdateMsg updates a single test in the dashboard.
type DashboardTestUpdateMsg struct {
	TestName string
	Status   string
	Duration time.Duration
	Message  string
}

// DashboardRunDoneMsg signals a category run is complete.
type DashboardRunDoneMsg struct{}

// NewDashboardModel creates a new dashboard model.
func NewDashboardModel(categories []string) DashboardModel {
	return DashboardModel{
		Categories: categories,
		Width:      80,
		Height:     24,
	}
}

// Init implements tea.Model.
func (m DashboardModel) Init() tea.Cmd {
	return tickCmd()
}

// Update implements tea.Model.
func (m DashboardModel) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
	switch msg := msg.(type) {
	case tea.KeyMsg:
		switch msg.String() {
		case "q", "ctrl+c":
			m.Quitting = true
			return m, tea.Quit

		case "r":
			if !m.Running {
				m.Running = true
				m.Passed = 0
				m.Failed = 0
				m.Skipped = 0
				m.TotalTests = 0
				m.Failures = nil
				m.StartTime = time.Now()
				return m, func() tea.Msg {
					return DashboardRunMsg{Category: m.Categories[m.SelectedCat]}
				}
			}

		case "f":
			m.ShowFailures = !m.ShowFailures

		case "1", "2", "3", "4", "5":
			idx := int(msg.String()[0] - '1')
			if idx >= 0 && idx < len(m.Categories) {
				m.SelectedCat = idx
			}

		case "tab", "right", "l":
			m.SelectedCat = (m.SelectedCat + 1) % len(m.Categories)

		case "shift+tab", "left", "h":
			m.SelectedCat = (m.SelectedCat - 1 + len(m.Categories)) % len(m.Categories)
		}

	case tea.WindowSizeMsg:
		m.Width = msg.Width
		m.Height = msg.Height

	case TickMsg:
		m.spinIdx = (m.spinIdx + 1) % len(SpinnerFrames)
		if m.Running {
			return m, tickCmd()
		}
		return m, tickCmd()

	case DashboardTestUpdateMsg:
		m.TotalTests++
		m.CurrentTest = msg.TestName
		switch msg.Status {
		case "passed":
			m.Passed++
		case "failed":
			m.Failed++
			m.Failures = append(m.Failures, FailureInfo{
				TestName: msg.TestName,
				Message:  msg.Message,
			})
		case "skipped":
			m.Skipped++
		}

	case DashboardRunDoneMsg:
		m.Running = false
		m.CurrentTest = ""
	}

	return m, nil
}

// View implements tea.Model.
func (m DashboardModel) View() string {
	if m.Quitting {
		return ""
	}

	var b strings.Builder

	// Title bar.
	title := TitleStyle.Render("Cognitive OS Test Dashboard")
	b.WriteString(title)
	b.WriteString("\n\n")

	// Category tabs.
	b.WriteString(m.renderTabs())
	b.WriteString("\n\n")

	// Counters panel.
	b.WriteString(m.renderCounters())
	b.WriteString("\n\n")

	// Current test / status.
	if m.Running {
		spinner := SpinnerFrames[m.spinIdx]
		if m.CurrentTest != "" {
			b.WriteString(InfoStyle.Render(fmt.Sprintf("  %s Running: %s", spinner, truncate(m.CurrentTest, m.Width-20))))
		} else {
			b.WriteString(InfoStyle.Render(fmt.Sprintf("  %s Starting tests...", spinner)))
		}
		b.WriteString("\n")

		elapsed := time.Since(m.StartTime).Round(time.Millisecond)
		b.WriteString(MutedStyle.Render(fmt.Sprintf("  Elapsed: %s", elapsed)))
		b.WriteString("\n")
	} else {
		b.WriteString(MutedStyle.Render("  Press 'r' to run tests"))
		b.WriteString("\n")
	}

	// Failure details panel.
	if m.ShowFailures && len(m.Failures) > 0 {
		b.WriteString("\n")
		b.WriteString(m.renderFailures())
	}

	// Help bar.
	b.WriteString("\n")
	b.WriteString(m.renderHelp())

	return lipgloss.NewStyle().Padding(1, 2).Render(b.String())
}

func (m DashboardModel) renderTabs() string {
	var tabs []string
	for i, cat := range m.Categories {
		label := fmt.Sprintf(" %d:%s ", i+1, cat)
		if i == m.SelectedCat {
			tabs = append(tabs, SelectedStyle.Render(label))
		} else {
			tabs = append(tabs, CategoryStyle.Render(label))
		}
	}
	return "  " + strings.Join(tabs, " ")
}

func (m DashboardModel) renderCounters() string {
	total := m.Passed + m.Failed + m.Skipped

	passStr := SuccessStyle.Render(fmt.Sprintf("%s %d", IconCheck, m.Passed))
	failStr := ErrorStyle.Render(fmt.Sprintf("%s %d", IconCross, m.Failed))
	skipStr := MutedStyle.Render(fmt.Sprintf("~ %d", m.Skipped))
	totalStr := CounterStyle.Render(fmt.Sprintf("Total: %d", total))

	return fmt.Sprintf("  %s  %s  %s     %s", passStr, failStr, skipStr, totalStr)
}

func (m DashboardModel) renderFailures() string {
	var b strings.Builder
	b.WriteString(ErrorStyle.Render("  Failures:"))
	b.WriteString("\n")

	maxShow := 5
	if len(m.Failures) < maxShow {
		maxShow = len(m.Failures)
	}

	for _, f := range m.Failures[:maxShow] {
		b.WriteString(fmt.Sprintf("    %s %s\n", ErrorStyle.Render(IconCross), f.TestName))
		if f.Message != "" {
			lines := strings.Split(f.Message, "\n")
			max := 2
			if len(lines) < max {
				max = len(lines)
			}
			for _, line := range lines[:max] {
				b.WriteString(MutedStyle.Render(fmt.Sprintf("      %s\n", line)))
			}
		}
	}

	if len(m.Failures) > maxShow {
		b.WriteString(MutedStyle.Render(fmt.Sprintf("    ... and %d more\n", len(m.Failures)-maxShow)))
	}

	return b.String()
}

func (m DashboardModel) renderHelp() string {
	keys := []string{
		MutedStyle.Render("r") + DimStyle.Render(":run"),
		MutedStyle.Render("f") + DimStyle.Render(":failures"),
		MutedStyle.Render("1-5") + DimStyle.Render(":category"),
		MutedStyle.Render("tab") + DimStyle.Render(":next"),
		MutedStyle.Render("q") + DimStyle.Render(":quit"),
	}
	return MutedStyle.Render("  ") + strings.Join(keys, MutedStyle.Render("  "))
}
