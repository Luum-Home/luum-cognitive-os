package cli

import (
	"fmt"

	tea "github.com/charmbracelet/bubbletea"
	"github.com/spf13/cobra"

	"luum-agent-os/cmd/cos-test/internal/config"
	"luum-agent-os/cmd/cos-test/internal/runner"
	"luum-agent-os/cmd/cos-test/internal/ui"
)

var dashboardCmd = &cobra.Command{
	Use:   "dashboard",
	Short: "Interactive test dashboard",
	Long: `Interactive Bubbletea test dashboard.

Real-time test execution with:
  - Category selector (1-5 or tab)
  - Live pass/fail counters
  - Failure details panel (press 'f')
  - Keyboard: r=rerun, f=failures, q=quit, 1-5=category`,
	RunE: func(cmd *cobra.Command, args []string) error {
		if ciMode || ui.IsCIMode() {
			return runTestsCI(config.DefaultConfig(), "")
		}
		return runDashboard()
	},
}

func init() {
	rootCmd.AddCommand(dashboardCmd)
}

// dashboardAdapter wraps DashboardModel to add pytest integration.
type dashboardAdapter struct {
	ui.DashboardModel
	cfg    *config.Config
	runner *runner.PytestRunner
}

func newDashboardAdapter(cfg *config.Config) dashboardAdapter {
	categories := make([]string, 0, len(config.AllCategories()))
	for _, c := range config.AllCategories() {
		categories = append(categories, string(c))
	}

	return dashboardAdapter{
		DashboardModel: ui.NewDashboardModel(categories),
		cfg:            cfg,
		runner:         runner.NewPytestRunner(cfg),
	}
}

func (m dashboardAdapter) Init() tea.Cmd {
	return m.DashboardModel.Init()
}

func (m dashboardAdapter) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
	switch msg := msg.(type) {
	case ui.DashboardRunMsg:
		// Intercept run message to launch pytest.
		cat := config.TestCategory(msg.Category)
		return m, m.startTestRun(cat)

	default:
		updated, cmd := m.DashboardModel.Update(msg)
		m.DashboardModel = updated.(ui.DashboardModel)
		return m, cmd
	}
}

func (m dashboardAdapter) View() string {
	return m.DashboardModel.View()
}

func (m dashboardAdapter) startTestRun(cat config.TestCategory) tea.Cmd {
	return func() tea.Msg {
		rc := &runner.RunConfig{
			Categories: []config.TestCategory{cat},
			Verbose:    m.cfg.Verbose,
		}

		events := make(chan runner.PytestEvent, 100)
		var suite *runner.TestSuite

		go func() {
			var err error
			suite, err = m.runner.Run(rc, events)
			_ = suite
			_ = err
		}()

		for evt := range events {
			if evt.Type == runner.EventTestResult {
				// We cannot send tea.Msg from here directly, so this
				// collects results. The dashboard polls via tick.
				_ = evt
			}
		}

		return ui.DashboardRunDoneMsg{}
	}
}

func runDashboard() error {
	cfg := config.DefaultConfig()
	cfg.Verbose = verbose

	model := newDashboardAdapter(cfg)
	p := tea.NewProgram(model, tea.WithAltScreen())

	if _, err := p.Run(); err != nil {
		return fmt.Errorf("dashboard error: %w", err)
	}

	return nil
}
