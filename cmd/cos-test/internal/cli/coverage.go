package cli

import (
	"fmt"
	"os"
	"path/filepath"
	"strings"

	"github.com/spf13/cobra"

	"luum-agent-os/cmd/cos-test/internal/config"
	"luum-agent-os/cmd/cos-test/internal/runner"
	"luum-agent-os/cmd/cos-test/internal/ui"
)

var coverageCmd = &cobra.Command{
	Use:   "coverage",
	Short: "Show test coverage across all dimensions",
	Long: `Show test coverage across all dimensions.

Scans test directories and cross-references with source files
to show a 4-dimension coverage matrix:
  - Infrastructure (hooks/_lib/)
  - Skills (skills/)
  - Hooks (hooks/)
  - State Transitions (behavior tests)

Output is a styled table with colored progress bars per dimension.`,
	RunE: func(cmd *cobra.Command, args []string) error {
		cfg := config.DefaultConfig()
		return showCoverage(cfg)
	},
}

func init() {
	rootCmd.AddCommand(coverageCmd)
}

func showCoverage(cfg *config.Config) error {
	ui.Title("Cognitive OS Test Coverage")
	ui.Separator()
	fmt.Println()

	// Discover all tests.
	disc, err := runner.DiscoverTests(cfg)
	if err != nil {
		return fmt.Errorf("failed to discover tests: %w", err)
	}

	// Count source files per dimension.
	dimensions := make(map[string]ui.CoverageDimension)

	// 1. Infrastructure dimension: hooks/_lib/ modules tested by unit tests.
	infraTotal := runner.CountSourceFiles(cfg.HooksLibDir)
	infraCovered := countCoveredModules(cfg.HooksLibDir, disc, config.CategoryUnit)
	dimensions["Infrastructure"] = ui.CoverageDimension{
		Total:   infraTotal,
		Covered: infraCovered,
	}

	// 2. Skills dimension: skills/ tested by integration/behavior tests.
	skillsTotal := countSkills(cfg.SkillsDir)
	skillsCovered := countCoveredSkills(cfg.SkillsDir, disc)
	dimensions["Skills"] = ui.CoverageDimension{
		Total:   skillsTotal,
		Covered: skillsCovered,
	}

	// 3. Hooks dimension: hooks/ tested by system tests.
	hooksTotal := countHooks(cfg.HooksDir)
	hooksCovered := countCoveredHooks(cfg.HooksDir, disc)
	dimensions["Hooks"] = ui.CoverageDimension{
		Total:   hooksTotal,
		Covered: hooksCovered,
	}

	// 4. State Transitions dimension: behavior test coverage.
	behaviorTotal := estimateBehaviorScenarios(cfg)
	behaviorCovered := len(disc.ByCategory[config.CategoryBehavior])
	dimensions["State Transitions"] = ui.CoverageDimension{
		Total:   behaviorTotal,
		Covered: behaviorCovered,
	}

	// Print per-category test counts.
	ui.Header("Tests by Category")
	fmt.Println()
	for _, cat := range config.AllCategories() {
		files := disc.ByCategory[cat]
		label := fmt.Sprintf("  %-15s", config.CategoryLabel(cat))
		count := fmt.Sprintf("%d test files", len(files))
		if len(files) > 0 {
			fmt.Println(label + ui.SuccessStyle.Render(count))
		} else {
			fmt.Println(label + ui.MutedStyle.Render(count))
		}
	}
	fmt.Printf("\n  Total: %d test files\n\n", disc.TotalFiles)

	// Print coverage matrix.
	fmt.Println(ui.RenderCoverageMatrix(dimensions))

	return nil
}

// countCoveredModules counts how many source modules in a directory have corresponding tests.
func countCoveredModules(sourceDir string, disc *runner.DiscoveryResult, cat config.TestCategory) int {
	if disc == nil {
		return 0
	}

	testFiles := disc.ByCategory[cat]
	testNames := make(map[string]bool)
	for _, tf := range testFiles {
		// Extract the module name from test_<module>.py.
		name := strings.TrimPrefix(tf.Name, "test_")
		name = strings.TrimSuffix(name, ".py")
		testNames[name] = true
	}

	covered := 0
	_ = filepath.Walk(sourceDir, func(path string, info os.FileInfo, err error) error {
		if err != nil || info.IsDir() {
			return nil
		}
		if !strings.HasSuffix(info.Name(), ".py") || strings.HasPrefix(info.Name(), "__") {
			return nil
		}
		name := strings.TrimSuffix(info.Name(), ".py")
		if testNames[name] {
			covered++
		}
		return nil
	})

	return covered
}

// countSkills counts skill directories.
func countSkills(skillsDir string) int {
	entries, err := os.ReadDir(skillsDir)
	if err != nil {
		return 0
	}
	count := 0
	for _, e := range entries {
		if e.IsDir() && !strings.HasPrefix(e.Name(), "_") && !strings.HasPrefix(e.Name(), ".") {
			count++
		}
	}
	return count
}

// countCoveredSkills checks which skills have test files referencing them.
func countCoveredSkills(skillsDir string, disc *runner.DiscoveryResult) int {
	if disc == nil {
		return 0
	}

	entries, err := os.ReadDir(skillsDir)
	if err != nil {
		return 0
	}

	// Build a set of all test file contents' referenced skill names.
	allTestNames := make(map[string]bool)
	for _, files := range disc.ByCategory {
		for _, tf := range files {
			name := strings.TrimPrefix(tf.Name, "test_")
			name = strings.TrimSuffix(name, ".py")
			allTestNames[name] = true
		}
	}

	covered := 0
	for _, e := range entries {
		if !e.IsDir() || strings.HasPrefix(e.Name(), "_") || strings.HasPrefix(e.Name(), ".") {
			continue
		}
		if allTestNames[e.Name()] {
			covered++
		}
	}
	return covered
}

// countHooks counts hook files.
func countHooks(hooksDir string) int {
	entries, err := os.ReadDir(hooksDir)
	if err != nil {
		return 0
	}
	count := 0
	for _, e := range entries {
		if !e.IsDir() && !strings.HasPrefix(e.Name(), "_") && !strings.HasPrefix(e.Name(), ".") {
			count++
		}
	}
	return count
}

// countCoveredHooks checks which hooks have corresponding test files.
func countCoveredHooks(hooksDir string, disc *runner.DiscoveryResult) int {
	if disc == nil {
		return 0
	}

	entries, err := os.ReadDir(hooksDir)
	if err != nil {
		return 0
	}

	allTestNames := make(map[string]bool)
	for _, files := range disc.ByCategory {
		for _, tf := range files {
			name := strings.TrimPrefix(tf.Name, "test_")
			name = strings.TrimSuffix(name, ".py")
			allTestNames[name] = true
		}
	}

	covered := 0
	for _, e := range entries {
		if e.IsDir() || strings.HasPrefix(e.Name(), "_") || strings.HasPrefix(e.Name(), ".") {
			continue
		}
		hookName := strings.TrimSuffix(e.Name(), filepath.Ext(e.Name()))
		if allTestNames[hookName] {
			covered++
		}
	}
	return covered
}

// estimateBehaviorScenarios estimates the total number of expected behavior scenarios.
func estimateBehaviorScenarios(cfg *config.Config) int {
	// Count hooks as a proxy for expected state transitions.
	hooks := countHooks(cfg.HooksDir)
	if hooks == 0 {
		return 1
	}
	// Each hook should have at least one behavior test for success and failure paths.
	return hooks * 2
}
