package cli

import (
	"fmt"
	"os"

	tea "github.com/charmbracelet/bubbletea"
	"github.com/spf13/cobra"

	"luum-agent-os/cmd/cos-test/internal/config"
	"luum-agent-os/cmd/cos-test/internal/runner"
	"luum-agent-os/cmd/cos-test/internal/ui"
)

var (
	runUnit        bool
	runBehavior    bool
	runIntegration bool
	runSystem      bool
	runE2E         bool
	runDocker      bool
	runAll         bool
)

var runCmd = &cobra.Command{
	Use:   "run [filter]",
	Short: "Run tests with live TUI progress",
	Long: `Run tests with live TUI progress.

Executes pytest with streaming output, showing a progress bar,
pass/fail counts, current test name, and elapsed time.

Use flags to select test categories, or --all to run everything.

Examples:
  cos-test run                      # Run all tests
  cos-test run --unit               # Run unit tests only
  cos-test run --behavior           # Run behavior tests only
  cos-test run -k test_hook_        # Filter by keyword
  cos-test run --ci                 # CI mode (plain text)`,
	RunE: func(cmd *cobra.Command, args []string) error {
		cfg := config.DefaultConfig()
		cfg.Categories = selectedCategories()
		cfg.Verbose = verbose
		cfg.CIMode = ciMode || ui.IsCIMode()

		filter := ""
		if len(args) > 0 {
			filter = args[0]
		}

		if cfg.CIMode {
			return runTestsCI(cfg, filter)
		}
		return runTestsTUI(cfg, filter)
	},
}

func init() {
	runCmd.Flags().BoolVar(&runUnit, "unit", false, "Run unit tests")
	runCmd.Flags().BoolVar(&runBehavior, "behavior", false, "Run behavior tests")
	runCmd.Flags().BoolVar(&runIntegration, "integration", false, "Run integration tests")
	runCmd.Flags().BoolVar(&runSystem, "system", false, "Run system tests")
	runCmd.Flags().BoolVar(&runE2E, "e2e", false, "Run e2e tests")
	runCmd.Flags().BoolVar(&runDocker, "docker", false, "Include tests that require Docker")
	runCmd.Flags().BoolVar(&runAll, "all", false, "Run all test categories")

	rootCmd.AddCommand(runCmd)
}

func selectedCategories() []config.TestCategory {
	if runAll {
		return config.AllCategories()
	}

	var cats []config.TestCategory
	if runUnit {
		cats = append(cats, config.CategoryUnit)
	}
	if runBehavior {
		cats = append(cats, config.CategoryBehavior)
	}
	if runIntegration {
		cats = append(cats, config.CategoryIntegration)
	}
	if runSystem {
		cats = append(cats, config.CategorySystem)
	}
	if runE2E {
		cats = append(cats, config.CategoryE2E)
	}

	// Default: run all if none selected.
	if len(cats) == 0 {
		cats = config.AllCategories()
	}
	return cats
}

// runTestsTUI runs tests with the Bubbletea TUI.
func runTestsTUI(cfg *config.Config, filter string) error {
	// Discover tests first for progress count.
	disc, err := runner.DiscoverTests(cfg)
	if err != nil {
		ui.Warn("Could not discover tests, progress may be inaccurate").Print()
	}

	total := 0
	if disc != nil {
		total = disc.TotalFiles
	}
	if total == 0 {
		total = 100 // estimate
	}

	// Create the progress model.
	model := ui.NewProgressModel(total)

	// Create the program.
	p := tea.NewProgram(model, tea.WithAltScreen())

	// Run pytest in background.
	pytestRunner := runner.NewPytestRunner(cfg)
	rc := &runner.RunConfig{
		Categories: cfg.Categories,
		Filter:     filter,
		Verbose:    cfg.Verbose,
	}

	go func() {
		events := make(chan runner.PytestEvent, 100)
		go func() {
			for evt := range events {
				if evt.Type == runner.EventTestResult {
					p.Send(ui.TestProgressMsg{
						TestName: evt.TestName,
						Status:   string(evt.Status),
					})
				}
			}
		}()

		suite, err := pytestRunner.Run(rc, events)
		_ = suite
		p.Send(ui.TestDoneMsg{Err: err})
	}()

	finalModel, err := p.Run()
	if err != nil {
		return fmt.Errorf("TUI error: %w", err)
	}

	// Show summary after TUI exits.
	m := finalModel.(ui.ProgressModel)
	if m.Failed > 0 {
		os.Exit(1)
	}
	return nil
}

// runTestsCI runs tests in CI mode (plain text).
func runTestsCI(cfg *config.Config, filter string) error {
	ui.Title("Cognitive OS Test Runner (CI Mode)")
	ui.Separator()

	pytestRunner := runner.NewPytestRunner(cfg)
	rc := &runner.RunConfig{
		Categories: cfg.Categories,
		Filter:     filter,
		Verbose:    cfg.Verbose,
	}

	suite, err := pytestRunner.RunSync(rc)
	if err != nil {
		ui.Error("Test execution failed").WithDetails(err.Error()).Print()
		return err
	}

	// Print summary.
	fmt.Println()
	ui.Separator()
	fmt.Printf("Results: %d passed, %d failed, %d skipped (total: %d)\n",
		suite.Passed, suite.Failed, suite.Skipped, suite.Total)
	fmt.Printf("Duration: %s\n", suite.Duration.Round(1))

	if !suite.IsSuccess() {
		fmt.Println()
		failures := suite.FailedTests()
		for _, f := range failures {
			fmt.Printf("  FAIL: %s\n", f.NodeID)
			if f.Message != "" {
				fmt.Printf("        %s\n", f.Message)
			}
		}
		os.Exit(1)
	}

	return nil
}
