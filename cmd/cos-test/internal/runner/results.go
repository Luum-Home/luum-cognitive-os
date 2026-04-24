package runner

import (
	"encoding/json"
	"time"
)

// TestStatus represents the status of a test.
type TestStatus string

const (
	StatusPassed  TestStatus = "passed"
	StatusFailed  TestStatus = "failed"
	StatusSkipped TestStatus = "skipped"
	StatusError   TestStatus = "error"
	StatusRunning TestStatus = "running"
)

// TestResult represents a single test result.
type TestResult struct {
	NodeID   string        `json:"nodeid"`
	Outcome  TestStatus    `json:"outcome"`
	Duration time.Duration `json:"duration"`
	Message  string        `json:"message,omitempty"`
	Stdout   string        `json:"stdout,omitempty"`
	Stderr   string        `json:"stderr,omitempty"`
}

// TestSuite represents all results from a test run.
type TestSuite struct {
	Tests     []TestResult  `json:"tests"`
	Duration  time.Duration `json:"duration"`
	StartedAt time.Time     `json:"created"`
	Passed    int           `json:"passed"`
	Failed    int           `json:"failed"`
	Skipped   int           `json:"skipped"`
	Errors    int           `json:"errors"`
	Total     int           `json:"total"`
	ExitCode  int           `json:"exitcode"`
}

// pytestJSONReport is the raw JSON format from pytest-json-report.
type pytestJSONReport struct {
	Created  float64 `json:"created"`
	Duration float64 `json:"duration"`
	ExitCode int     `json:"exitcode"`
	Summary  struct {
		Passed  int `json:"passed"`
		Failed  int `json:"failed"`
		Skipped int `json:"skipped"`
		Error   int `json:"error"`
		Total   int `json:"total"`
	} `json:"summary"`
	Tests []struct {
		NodeID   string  `json:"nodeid"`
		Outcome  string  `json:"outcome"`
		Duration float64 `json:"duration"`
		Call     *struct {
			Stdout   string `json:"stdout"`
			Stderr   string `json:"stderr"`
			Longrepr string `json:"longrepr"`
		} `json:"call"`
	} `json:"tests"`
}

// ParseJSONReport parses pytest-json-report output into a TestSuite.
func ParseJSONReport(data []byte) (*TestSuite, error) {
	var report pytestJSONReport
	if err := json.Unmarshal(data, &report); err != nil {
		return nil, err
	}

	suite := &TestSuite{
		Duration:  time.Duration(report.Duration * float64(time.Second)),
		StartedAt: time.Unix(int64(report.Created), 0),
		Passed:    report.Summary.Passed,
		Failed:    report.Summary.Failed,
		Skipped:   report.Summary.Skipped,
		Errors:    report.Summary.Error,
		Total:     report.Summary.Total,
		ExitCode:  report.ExitCode,
	}

	for _, t := range report.Tests {
		result := TestResult{
			NodeID:   t.NodeID,
			Outcome:  TestStatus(t.Outcome),
			Duration: time.Duration(t.Duration * float64(time.Second)),
		}
		if t.Call != nil {
			result.Stdout = t.Call.Stdout
			result.Stderr = t.Call.Stderr
			result.Message = t.Call.Longrepr
		}
		suite.Tests = append(suite.Tests, result)
	}

	return suite, nil
}

// FailedTests returns only the failed tests.
func (s *TestSuite) FailedTests() []TestResult {
	var failed []TestResult
	for _, t := range s.Tests {
		if t.Outcome == StatusFailed || t.Outcome == StatusError {
			failed = append(failed, t)
		}
	}
	return failed
}

// IsSuccess returns true if all tests passed.
func (s *TestSuite) IsSuccess() bool {
	return s.Failed == 0 && s.Errors == 0
}
