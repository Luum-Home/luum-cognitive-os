package runner

import (
	"bufio"
	"fmt"
	"io"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"time"

	"luum-agent-os/cmd/cos-test/internal/config"
)

// PytestEvent represents a streaming event from pytest output.
type PytestEvent struct {
	Type     EventType
	TestName string
	Status   TestStatus
	Message  string
	Line     string
}

// EventType classifies streaming events.
type EventType int

const (
	EventCollecting EventType = iota
	EventTestStart
	EventTestResult
	EventSummary
	EventOutput
	EventError
)

// RunConfig configures a pytest run.
type RunConfig struct {
	Categories []config.TestCategory
	Filter     string
	Verbose    bool
	ExtraArgs  []string
	ReportPath string // path for JSON report output
}

// PytestRunner manages pytest execution.
type PytestRunner struct {
	cfg *config.Config
}

// NewPytestRunner creates a new pytest runner.
func NewPytestRunner(cfg *config.Config) *PytestRunner {
	return &PytestRunner{cfg: cfg}
}

// BuildArgs constructs the pytest command arguments.
func (r *PytestRunner) BuildArgs(rc *RunConfig) []string {
	args := []string{"-m", "pytest"}

	// Add test directories based on categories.
	categories := rc.Categories
	if len(categories) == 0 {
		categories = config.AllCategories()
	}

	// Build marker expression.
	if len(rc.Categories) > 0 {
		var markers []string
		for _, cat := range rc.Categories {
			markers = append(markers, config.CategoryMarker(cat))
		}
		args = append(args, "-m", strings.Join(markers, " or "))
	}

	// Add test directories.
	for _, cat := range categories {
		dir := r.cfg.TestDir(cat)
		if _, err := os.Stat(dir); err == nil {
			args = append(args, dir)
		}
	}

	// Filter by keyword.
	if rc.Filter != "" {
		args = append(args, "-k", rc.Filter)
	}

	// Standard flags.
	args = append(args, "--tb=short", "-q")

	// Verbose flag.
	if rc.Verbose {
		args = append(args, "-v")
	}

	// JSON report.
	reportPath := rc.ReportPath
	if reportPath == "" {
		reportPath = filepath.Join(r.cfg.TestsDir, ".report.json")
	}
	args = append(args, "--json-report", fmt.Sprintf("--json-report-file=%s", reportPath))

	// Extra args.
	args = append(args, rc.ExtraArgs...)

	return args
}

// Run executes pytest and streams events through a channel.
func (r *PytestRunner) Run(rc *RunConfig, events chan<- PytestEvent) (*TestSuite, error) {
	defer close(events)

	args := r.BuildArgs(rc)
	cmd := exec.Command("python", args...)
	cmd.Dir = r.cfg.ProjectRoot

	// Set up environment.
	cmd.Env = append(os.Environ(), "PYTHONDONTWRITEBYTECODE=1")

	stdout, err := cmd.StdoutPipe()
	if err != nil {
		return nil, fmt.Errorf("failed to get stdout pipe: %w", err)
	}
	stderr, err := cmd.StderrPipe()
	if err != nil {
		return nil, fmt.Errorf("failed to get stderr pipe: %w", err)
	}

	startTime := time.Now()
	if err := cmd.Start(); err != nil {
		return nil, fmt.Errorf("failed to start pytest: %w", err)
	}

	// Stream stdout.
	go r.streamOutput(stdout, events)
	// Stream stderr.
	go r.streamOutput(stderr, events)

	exitErr := cmd.Wait()
	elapsed := time.Since(startTime)

	// Read JSON report.
	reportPath := rc.ReportPath
	if reportPath == "" {
		reportPath = filepath.Join(r.cfg.TestsDir, ".report.json")
	}

	reportData, err := os.ReadFile(reportPath)
	if err != nil {
		// If no JSON report, construct a minimal suite from exit code.
		suite := &TestSuite{
			Duration: elapsed,
		}
		if exitErr != nil {
			suite.ExitCode = 1
			suite.Failed = 1
			suite.Total = 1
		}
		return suite, nil
	}

	// Clean up report file.
	defer os.Remove(reportPath)

	suite, err := ParseJSONReport(reportData)
	if err != nil {
		return nil, fmt.Errorf("failed to parse test report: %w", err)
	}

	return suite, nil
}

// RunSync executes pytest synchronously (for CI mode).
func (r *PytestRunner) RunSync(rc *RunConfig) (*TestSuite, error) {
	args := r.BuildArgs(rc)
	cmd := exec.Command("python", args...)
	cmd.Dir = r.cfg.ProjectRoot
	cmd.Env = append(os.Environ(), "PYTHONDONTWRITEBYTECODE=1")
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr

	startTime := time.Now()
	exitErr := cmd.Run()
	elapsed := time.Since(startTime)

	// Read JSON report.
	reportPath := rc.ReportPath
	if reportPath == "" {
		reportPath = filepath.Join(r.cfg.TestsDir, ".report.json")
	}

	reportData, err := os.ReadFile(reportPath)
	if err != nil {
		suite := &TestSuite{Duration: elapsed}
		if exitErr != nil {
			suite.ExitCode = 1
			suite.Failed = 1
			suite.Total = 1
		}
		return suite, nil
	}
	defer os.Remove(reportPath)

	return ParseJSONReport(reportData)
}

// streamOutput reads lines from a reader and sends events.
func (r *PytestRunner) streamOutput(reader io.Reader, events chan<- PytestEvent) {
	scanner := bufio.NewScanner(reader)
	for scanner.Scan() {
		line := scanner.Text()
		event := parsePytestLine(line)
		events <- event
	}
}

// parsePytestLine parses a single line of pytest output into an event.
func parsePytestLine(line string) PytestEvent {
	trimmed := strings.TrimSpace(line)

	// Detect test results: PASSED, FAILED, ERROR, SKIPPED.
	if strings.Contains(trimmed, " PASSED") {
		name := extractTestName(trimmed)
		return PytestEvent{
			Type:     EventTestResult,
			TestName: name,
			Status:   StatusPassed,
			Line:     line,
		}
	}
	if strings.Contains(trimmed, " FAILED") {
		name := extractTestName(trimmed)
		return PytestEvent{
			Type:     EventTestResult,
			TestName: name,
			Status:   StatusFailed,
			Line:     line,
		}
	}
	if strings.Contains(trimmed, " SKIPPED") {
		name := extractTestName(trimmed)
		return PytestEvent{
			Type:     EventTestResult,
			TestName: name,
			Status:   StatusSkipped,
			Line:     line,
		}
	}
	if strings.Contains(trimmed, " ERROR") {
		name := extractTestName(trimmed)
		return PytestEvent{
			Type:     EventTestResult,
			TestName: name,
			Status:   StatusError,
			Line:     line,
		}
	}

	// Detect collecting.
	if strings.HasPrefix(trimmed, "collecting") || strings.HasPrefix(trimmed, "collected") {
		return PytestEvent{
			Type:    EventCollecting,
			Message: trimmed,
			Line:    line,
		}
	}

	// Summary lines.
	if strings.Contains(trimmed, "passed") && strings.Contains(trimmed, "=") {
		return PytestEvent{
			Type:    EventSummary,
			Message: trimmed,
			Line:    line,
		}
	}

	// Default: general output.
	return PytestEvent{
		Type:    EventOutput,
		Message: trimmed,
		Line:    line,
	}
}

// extractTestName pulls the test name from a pytest output line.
func extractTestName(line string) string {
	// Lines look like: "tests/unit/test_foo.py::test_bar PASSED"
	parts := strings.Fields(line)
	if len(parts) > 0 {
		return parts[0]
	}
	return line
}
