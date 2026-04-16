package pattern

import (
	"testing"
	"time"
)

// newSeededTracker creates an in-memory SQLTracker, records the given
// fixtures, flushes, and returns the tracker so tests can wire the Detector.
func newSeededTracker(t *testing.T, recs []ExecutionRecord) *SQLTracker {
	t.Helper()
	tr, err := NewTracker(":memory:")
	if err != nil {
		t.Fatalf("NewTracker: %v", err)
	}
	for _, r := range recs {
		tr.Record(r)
	}
	if err := tr.Flush(); err != nil {
		t.Fatalf("Flush: %v", err)
	}
	return tr
}

func TestDetector_RepeatedFailure(t *testing.T) {
	now := time.Now().UTC()
	var recs []ExecutionRecord

	// Three failures of "lint" with the same code => RepeatedFailure
	for i := 0; i < 4; i++ {
		recs = append(recs, ExecutionRecord{
			Timestamp:     now.Add(time.Duration(i) * time.Minute),
			SessionID:     "s1",
			EventType:     "before_tool",
			ToolType:      "Bash",
			ValidatorName: "lint",
			Result:        ResultFail,
			DurationMs:    10,
			ErrorCode:     "COS-LINT-001",
			ErrorMessage:  "trailing whitespace",
		})
	}
	// Some passes to ensure they don't pollute the count.
	recs = append(recs, ExecutionRecord{
		Timestamp: now, SessionID: "s1", EventType: "before_tool",
		ToolType: "Bash", ValidatorName: "lint", Result: ResultPass, DurationMs: 5,
	})
	// A different validator that fails only twice — below threshold.
	for i := 0; i < 2; i++ {
		recs = append(recs, ExecutionRecord{
			Timestamp:     now,
			SessionID:     "s1",
			EventType:     "before_tool",
			ToolType:      "Bash",
			ValidatorName: "fmt",
			Result:        ResultFail,
			DurationMs:    8,
			ErrorCode:     "COS-FMT-001",
		})
	}

	tr := newSeededTracker(t, recs)
	defer tr.Close()
	det := NewDetector(tr.DB())

	patterns, err := det.Analyze(time.Time{}, 0)
	if err != nil {
		t.Fatalf("Analyze: %v", err)
	}

	got := filterByType(patterns, PatternRepeatedFailure)
	if len(got) != 1 {
		t.Fatalf("RepeatedFailure count = %d, want 1; all=%+v", len(got), patterns)
	}
	p := got[0]
	if p.Confidence < 0.7 {
		t.Errorf("confidence = %.2f, want >= 0.7", p.Confidence)
	}
	if len(p.Evidence) == 0 || len(p.Evidence) > det.MaxEvidence {
		t.Errorf("evidence count = %d, want 1..%d", len(p.Evidence), det.MaxEvidence)
	}
	if p.Evidence[0].ValidatorName != "lint" {
		t.Errorf("evidence validator = %q, want lint", p.Evidence[0].ValidatorName)
	}
}

func TestDetector_AnalyzeSession_ScopesToSession(t *testing.T) {
	now := time.Now().UTC()
	var recs []ExecutionRecord
	for i := 0; i < 4; i++ {
		recs = append(recs, ExecutionRecord{
			Timestamp:     now,
			SessionID:     "session-A",
			ValidatorName: "vA",
			EventType:     "before_tool", ToolType: "Bash",
			Result:    ResultFail,
			ErrorCode: "EA",
		})
	}
	for i := 0; i < 4; i++ {
		recs = append(recs, ExecutionRecord{
			Timestamp:     now,
			SessionID:     "session-B",
			ValidatorName: "vB",
			EventType:     "before_tool", ToolType: "Bash",
			Result:    ResultFail,
			ErrorCode: "EB",
		})
	}
	tr := newSeededTracker(t, recs)
	defer tr.Close()
	det := NewDetector(tr.DB())

	patterns, err := det.AnalyzeSession("session-A", 0)
	if err != nil {
		t.Fatalf("AnalyzeSession: %v", err)
	}
	if len(patterns) != 1 || patterns[0].Evidence[0].SessionID != "session-A" {
		t.Errorf("expected one pattern for session-A only, got %+v", patterns)
	}
}

func TestDetector_PerfRegression(t *testing.T) {
	base := time.Now().UTC().Add(-1 * time.Hour)
	var recs []ExecutionRecord

	// 6 fast runs, then 6 slow runs of "slow-validator"
	for i := 0; i < 6; i++ {
		recs = append(recs, ExecutionRecord{
			Timestamp:     base.Add(time.Duration(i) * time.Minute),
			SessionID:     "s1",
			EventType:     "before_tool",
			ToolType:      "Bash",
			ValidatorName: "slow-validator",
			Result:        ResultPass,
			DurationMs:    10,
		})
	}
	for i := 0; i < 6; i++ {
		recs = append(recs, ExecutionRecord{
			Timestamp:     base.Add(time.Duration(10+i) * time.Minute),
			SessionID:     "s2",
			EventType:     "before_tool",
			ToolType:      "Bash",
			ValidatorName: "slow-validator",
			Result:        ResultPass,
			DurationMs:    50, // 5x slower
		})
	}
	// A control validator with stable latency — must NOT be flagged.
	for i := 0; i < 12; i++ {
		recs = append(recs, ExecutionRecord{
			Timestamp:     base.Add(time.Duration(i) * time.Minute),
			SessionID:     "s1",
			EventType:     "before_tool",
			ToolType:      "Bash",
			ValidatorName: "stable-validator",
			Result:        ResultPass,
			DurationMs:    20,
		})
	}

	tr := newSeededTracker(t, recs)
	defer tr.Close()
	det := NewDetector(tr.DB())

	patterns, err := det.Analyze(time.Time{}, 0)
	if err != nil {
		t.Fatalf("Analyze: %v", err)
	}

	regs := filterByType(patterns, PatternPerfRegression)
	if len(regs) != 1 {
		t.Fatalf("PerfRegression count = %d, want 1; all=%+v", len(regs), patterns)
	}
	if regs[0].Evidence[0].ValidatorName != "slow-validator" {
		t.Errorf("flagged validator = %q, want slow-validator", regs[0].Evidence[0].ValidatorName)
	}
	// 5x slowdown over 1.5x threshold => high confidence.
	if regs[0].Confidence < 0.7 {
		t.Errorf("confidence = %.2f, want >= 0.7 for 5x slowdown", regs[0].Confidence)
	}
}

func TestDetector_ErrorCluster_SpansSessions(t *testing.T) {
	now := time.Now().UTC()
	var recs []ExecutionRecord
	// Same error code in 4 distinct sessions (above threshold of 3).
	for i, sess := range []string{"s1", "s2", "s3", "s4"} {
		recs = append(recs, ExecutionRecord{
			Timestamp:     now.Add(time.Duration(i) * time.Minute),
			SessionID:     sess,
			ValidatorName: "secret-detector",
			EventType:     "before_tool", ToolType: "Edit",
			Result:    ResultFail,
			ErrorCode: "COS-SEC-001",
		})
	}
	// An error code only seen in one session — must NOT be a cluster.
	recs = append(recs, ExecutionRecord{
		Timestamp:     now,
		SessionID:     "lonely",
		ValidatorName: "v",
		EventType:     "before_tool", ToolType: "Bash",
		Result:    ResultFail,
		ErrorCode: "ONE-OFF",
	})

	tr := newSeededTracker(t, recs)
	defer tr.Close()
	det := NewDetector(tr.DB())

	patterns, err := det.Analyze(time.Time{}, 0)
	if err != nil {
		t.Fatalf("Analyze: %v", err)
	}
	clusters := filterByType(patterns, PatternErrorCluster)
	if len(clusters) != 1 {
		t.Fatalf("ErrorCluster count = %d, want 1; all=%+v", len(clusters), patterns)
	}
	if clusters[0].Evidence[0].ErrorCode != "COS-SEC-001" {
		t.Errorf("clustered code = %q, want COS-SEC-001", clusters[0].Evidence[0].ErrorCode)
	}
}

func TestDetector_FilterByConfidence(t *testing.T) {
	now := time.Now().UTC()
	var recs []ExecutionRecord
	// Exactly MinRepeats failures => baseline confidence (~0.5).
	for i := 0; i < 3; i++ {
		recs = append(recs, ExecutionRecord{
			Timestamp:     now,
			SessionID:     "s1",
			EventType:     "before_tool", ToolType: "Bash",
			ValidatorName: "marginal",
			Result:        ResultFail,
			ErrorCode:     "X",
		})
	}
	tr := newSeededTracker(t, recs)
	defer tr.Close()
	det := NewDetector(tr.DB())

	all, err := det.Analyze(time.Time{}, 0)
	if err != nil {
		t.Fatalf("Analyze: %v", err)
	}
	if len(all) != 1 {
		t.Fatalf("expected 1 pattern, got %d", len(all))
	}

	// Demand higher confidence than this borderline case can produce.
	high, err := det.Analyze(time.Time{}, 0.99)
	if err != nil {
		t.Fatalf("Analyze high: %v", err)
	}
	if len(high) != 0 {
		t.Errorf("expected 0 high-confidence patterns, got %d (confidence=%.2f)",
			len(high), all[0].Confidence)
	}
}

func TestPatternType_String(t *testing.T) {
	cases := map[PatternType]string{
		PatternRepeatedFailure:     "repeated_failure",
		PatternFalsePositive:       "false_positive",
		PatternMissingCoverage:     "missing_coverage",
		PatternPerfRegression:      "perf_regression",
		PatternErrorCluster:        "error_cluster",
		PatternSequenceCorrelation: "sequence_correlation",
		PatternType(99):            "unknown",
	}
	for pt, want := range cases {
		if got := pt.String(); got != want {
			t.Errorf("PatternType(%d).String() = %q, want %q", pt, got, want)
		}
	}
}

func filterByType(patterns []DetectedPattern, t PatternType) []DetectedPattern {
	var out []DetectedPattern
	for _, p := range patterns {
		if p.Type == t {
			out = append(out, p)
		}
	}
	return out
}
