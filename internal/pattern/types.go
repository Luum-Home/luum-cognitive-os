// Package pattern provides execution tracking and pattern detection for
// the cos-dispatch validator/transformer pipeline.
//
// The package has two responsibilities:
//
//  1. Tracker — records each validator execution to a SQLite database
//     with non-blocking, buffered writes so dispatch latency is unaffected.
//  2. Detector — analyses recorded executions to surface recurring problems
//     (repeated failures, performance regressions, error clusters, etc.) so
//     they can be addressed before they degrade developer trust.
//
// Phase 4 implements three of the six pattern types defined in
// docs/architecture/cos-dispatch/interfaces.md (RepeatedFailure,
// PerfRegression, ErrorCluster). The remaining three (FalsePositive,
// MissingCoverage, SequenceCorrelation) are reserved for Phase 5.
//
// Schema: docs/architecture/cos-dispatch/schema.sql
package pattern

import "time"

// PatternType enumerates the kinds of behaviour the Detector can flag.
type PatternType int

const (
	// PatternRepeatedFailure: same validator fails over and over for the
	// same context (likely a real bug or a noisy validator).
	PatternRepeatedFailure PatternType = iota
	// PatternFalsePositive: validator fires but is consistently overridden.
	PatternFalsePositive
	// PatternMissingCoverage: a tool type has no validators registered.
	PatternMissingCoverage
	// PatternPerfRegression: validator latency trending upward over time.
	PatternPerfRegression
	// PatternErrorCluster: identical error code seen across many sessions.
	PatternErrorCluster
	// PatternSequenceCorrelation: fixing error A is followed by error B.
	PatternSequenceCorrelation
)

// String returns the canonical lower_snake name used in the database.
func (t PatternType) String() string {
	switch t {
	case PatternRepeatedFailure:
		return "repeated_failure"
	case PatternFalsePositive:
		return "false_positive"
	case PatternMissingCoverage:
		return "missing_coverage"
	case PatternPerfRegression:
		return "perf_regression"
	case PatternErrorCluster:
		return "error_cluster"
	case PatternSequenceCorrelation:
		return "sequence_correlation"
	default:
		return "unknown"
	}
}

// Result enumerates the canonical outcomes a validator/transformer execution
// can produce, matching the `result` CHECK constraint in the schema.
//
// ResultOverride signals that a warn/fail result was dismissed by a human or
// downstream system. It is the primary source signal for FalsePositive
// detection in Phase 5.1 — record it whenever an operator explicitly accepts
// a flagged hook execution.
const (
	ResultPass      = "pass"
	ResultFail      = "fail"
	ResultWarn      = "warn"
	ResultTransform = "transform"
	ResultOverride  = "override"
)

// ExecutionRecord is one row in the executions table — one validator (or
// transformer) run against one hook context.
type ExecutionRecord struct {
	ID            int64     `db:"id"`
	Timestamp     time.Time `db:"timestamp"`
	SessionID     string    `db:"session_id"`
	EventType     string    `db:"event_type"` // 'before_tool', 'after_tool', etc.
	ToolType      string    `db:"tool_type"`  // 'Bash', 'Write', 'Edit', 'Agent', etc.
	ToolInputHash string    `db:"tool_input_hash"`
	ValidatorName string    `db:"validator_name"`
	Result        string    `db:"result"`      // pass|fail|warn|transform
	DurationMs    int64     `db:"duration_ms"`
	ErrorCode     string    `db:"error_code"`
	ErrorMessage  string    `db:"error_message"`
	ContextHash   string    `db:"context_hash"`
}

// DetectedPattern is the Detector's observation about one recurring issue.
// Confidence is in [0,1]. Evidence carries the records that support the
// finding so a human can verify before acting on it.
type DetectedPattern struct {
	Type        PatternType
	Description string
	Confidence  float64
	Evidence    []ExecutionRecord
	Suggestion  string
	AutoFixable bool
}

// Tracker records execution data. Implementations buffer writes so callers
// (dispatcher hot-path) never block on disk I/O.
type Tracker interface {
	Record(record ExecutionRecord)
	Flush() error
	Close() error
}

// Detector analyses execution history and returns patterns above the
// confidence threshold.
type Detector interface {
	Analyze(since time.Time, minConfidence float64) ([]DetectedPattern, error)
	AnalyzeSession(sessionID string, minConfidence float64) ([]DetectedPattern, error)
}
