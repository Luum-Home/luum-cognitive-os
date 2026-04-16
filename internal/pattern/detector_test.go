package pattern

import (
	"os"
	"path/filepath"
	"strings"
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

// newTempTracker creates a SQLTracker backed by a real temp-file SQLite DB.
// Per ADR-010 tests must NOT use :memory: — they must use os.CreateTemp.
func newTempTracker(t *testing.T) *SQLTracker {
	t.Helper()
	f, err := os.CreateTemp(t.TempDir(), "patterns-*.db")
	if err != nil {
		t.Fatalf("CreateTemp: %v", err)
	}
	f.Close()
	tr, err := NewTracker(f.Name())
	if err != nil {
		t.Fatalf("NewTracker: %v", err)
	}
	t.Cleanup(func() { tr.Close() })
	return tr
}

// ---------------------------------------------------------------------------
// Phase 5.1 — FalsePositive
// ---------------------------------------------------------------------------

func TestDetect_FalsePositive_HighOverrideRatio(t *testing.T) {
	tr := newTempTracker(t)
	now := time.Now().UTC()

	// validator "noisy": 7 warn + 3 override = 10 total, 30% overrides
	// but we want ratio >= 0.5: use 3 warn + 7 override = 10 total, 70% override
	for i := 0; i < 3; i++ {
		tr.Record(ExecutionRecord{
			Timestamp: now.Add(time.Duration(i) * time.Second),
			SessionID: "s1", EventType: "before_tool", ToolType: "Bash",
			ValidatorName: "noisy", Result: ResultWarn, DurationMs: 5,
		})
	}
	for i := 0; i < 7; i++ {
		tr.Record(ExecutionRecord{
			Timestamp: now.Add(time.Duration(10+i) * time.Second),
			SessionID: "s1", EventType: "before_tool", ToolType: "Bash",
			ValidatorName: "noisy", Result: ResultOverride, DurationMs: 5,
		})
	}
	// unrelated validator: 2 fails, no overrides — must NOT fire
	for i := 0; i < 2; i++ {
		tr.Record(ExecutionRecord{
			Timestamp: now, SessionID: "s1", EventType: "before_tool", ToolType: "Bash",
			ValidatorName: "strict", Result: ResultFail, DurationMs: 5,
		})
	}
	if err := tr.Flush(); err != nil {
		t.Fatalf("Flush: %v", err)
	}

	det := NewDetector(tr.DB())
	det.FalsePositiveMinSample = 5
	det.FalsePositiveThreshold = 0.5

	patterns, err := det.Analyze(time.Time{}, 0)
	if err != nil {
		t.Fatalf("Analyze: %v", err)
	}
	fps := filterByType(patterns, PatternFalsePositive)
	if len(fps) != 1 {
		t.Fatalf("FalsePositive count = %d, want 1; all=%+v", len(fps), patterns)
	}
	if !strings.Contains(fps[0].Suggestion, "noisy") {
		t.Errorf("suggestion does not mention validator 'noisy': %q", fps[0].Suggestion)
	}
	if fps[0].Confidence <= 0 {
		t.Errorf("confidence = %.2f, want > 0", fps[0].Confidence)
	}
}

func TestDetect_FalsePositive_BelowThreshold(t *testing.T) {
	tr := newTempTracker(t)
	now := time.Now().UTC()

	// 8 warn + 2 override = 10 total; ratio 0.2 < 0.5 threshold — no pattern
	for i := 0; i < 8; i++ {
		tr.Record(ExecutionRecord{
			Timestamp: now.Add(time.Duration(i) * time.Second),
			SessionID: "s1", EventType: "before_tool", ToolType: "Bash",
			ValidatorName: "low-fp", Result: ResultWarn, DurationMs: 5,
		})
	}
	for i := 0; i < 2; i++ {
		tr.Record(ExecutionRecord{
			Timestamp: now.Add(time.Duration(20+i) * time.Second),
			SessionID: "s1", EventType: "before_tool", ToolType: "Bash",
			ValidatorName: "low-fp", Result: ResultOverride, DurationMs: 5,
		})
	}
	if err := tr.Flush(); err != nil {
		t.Fatalf("Flush: %v", err)
	}

	det := NewDetector(tr.DB())
	det.FalsePositiveMinSample = 5
	det.FalsePositiveThreshold = 0.5

	patterns, err := det.Analyze(time.Time{}, 0)
	if err != nil {
		t.Fatalf("Analyze: %v", err)
	}
	fps := filterByType(patterns, PatternFalsePositive)
	if len(fps) != 0 {
		t.Errorf("FalsePositive count = %d, want 0 (ratio below threshold)", len(fps))
	}
}

func TestDetect_FalsePositive_SmallSample(t *testing.T) {
	tr := newTempTracker(t)
	now := time.Now().UTC()

	// 1 warn + 1 override = 2 total; below MinSample of 5 — no pattern
	tr.Record(ExecutionRecord{
		Timestamp: now, SessionID: "s1", EventType: "before_tool", ToolType: "Bash",
		ValidatorName: "tiny", Result: ResultWarn, DurationMs: 5,
	})
	tr.Record(ExecutionRecord{
		Timestamp: now.Add(time.Second), SessionID: "s1", EventType: "before_tool", ToolType: "Bash",
		ValidatorName: "tiny", Result: ResultOverride, DurationMs: 5,
	})
	if err := tr.Flush(); err != nil {
		t.Fatalf("Flush: %v", err)
	}

	det := NewDetector(tr.DB())
	det.FalsePositiveMinSample = 5
	det.FalsePositiveThreshold = 0.5

	patterns, err := det.Analyze(time.Time{}, 0)
	if err != nil {
		t.Fatalf("Analyze: %v", err)
	}
	fps := filterByType(patterns, PatternFalsePositive)
	if len(fps) != 0 {
		t.Errorf("FalsePositive count = %d, want 0 (sample too small)", len(fps))
	}
}

// ---------------------------------------------------------------------------
// Phase 5.1 — MissingCoverage
// ---------------------------------------------------------------------------

func TestDetect_MissingCoverage_UncoveredToolType(t *testing.T) {
	tr := newTempTracker(t)
	now := time.Now().UTC()

	// 15 events for 'CustomTool' with empty validator_name (no validator matched)
	for i := 0; i < 15; i++ {
		tr.Record(ExecutionRecord{
			Timestamp: now.Add(time.Duration(i) * time.Second),
			SessionID: "s1", EventType: "before_tool", ToolType: "CustomTool",
			ValidatorName: "", Result: ResultPass, DurationMs: 3,
		})
	}
	if err := tr.Flush(); err != nil {
		t.Fatalf("Flush: %v", err)
	}

	det := NewDetector(tr.DB())
	det.MissingCoverageThreshold = 10

	patterns, err := det.Analyze(time.Time{}, 0)
	if err != nil {
		t.Fatalf("Analyze: %v", err)
	}
	mc := filterByType(patterns, PatternMissingCoverage)
	if len(mc) != 1 {
		t.Fatalf("MissingCoverage count = %d, want 1; all=%+v", len(mc), patterns)
	}
	if !strings.Contains(mc[0].Suggestion, "CustomTool") {
		t.Errorf("suggestion does not mention 'CustomTool': %q", mc[0].Suggestion)
	}
}

func TestDetect_MissingCoverage_BelowThreshold(t *testing.T) {
	tr := newTempTracker(t)
	now := time.Now().UTC()

	// 3 events — below threshold of 10
	for i := 0; i < 3; i++ {
		tr.Record(ExecutionRecord{
			Timestamp: now.Add(time.Duration(i) * time.Second),
			SessionID: "s1", EventType: "before_tool", ToolType: "RareTool",
			ValidatorName: "", Result: ResultPass, DurationMs: 3,
		})
	}
	if err := tr.Flush(); err != nil {
		t.Fatalf("Flush: %v", err)
	}

	det := NewDetector(tr.DB())
	det.MissingCoverageThreshold = 10

	patterns, err := det.Analyze(time.Time{}, 0)
	if err != nil {
		t.Fatalf("Analyze: %v", err)
	}
	mc := filterByType(patterns, PatternMissingCoverage)
	if len(mc) != 0 {
		t.Errorf("MissingCoverage count = %d, want 0 (below threshold)", len(mc))
	}
}

// ---------------------------------------------------------------------------
// Phase 5.1 — SequenceCorrelation
// ---------------------------------------------------------------------------

func TestDetect_SequenceCorrelation_RepeatedPair(t *testing.T) {
	dbFile := filepath.Join(t.TempDir(), "seq-test.db")
	tr, err := NewTracker(dbFile)
	if err != nil {
		t.Fatalf("NewTracker: %v", err)
	}
	defer tr.Close()

	// Insert directly into failure_sequences: count=5 >= threshold of 3
	now := time.Now().UTC()
	_, err = tr.DB().Exec(
		`INSERT INTO failure_sequences (source_code, target_code, count, first_seen, last_seen)
		 VALUES (?, ?, ?, ?, ?)`,
		"COS-A", "COS-B", 5, now, now,
	)
	if err != nil {
		t.Fatalf("INSERT failure_sequences: %v", err)
	}

	det := NewDetector(tr.DB())
	det.SequenceCorrelationThreshold = 3

	patterns, err := det.Analyze(time.Time{}, 0)
	if err != nil {
		t.Fatalf("Analyze: %v", err)
	}
	sc := filterByType(patterns, PatternSequenceCorrelation)
	if len(sc) != 1 {
		t.Fatalf("SequenceCorrelation count = %d, want 1; all=%+v", len(sc), patterns)
	}
	if !strings.Contains(sc[0].Suggestion, "COS-A") || !strings.Contains(sc[0].Suggestion, "COS-B") {
		t.Errorf("suggestion missing codes: %q", sc[0].Suggestion)
	}
	if !strings.Contains(sc[0].Suggestion, "count=5") {
		t.Errorf("suggestion missing count: %q", sc[0].Suggestion)
	}
}

func TestDetect_SequenceCorrelation_SingleOccurrence(t *testing.T) {
	dbFile := filepath.Join(t.TempDir(), "seq-single.db")
	tr, err := NewTracker(dbFile)
	if err != nil {
		t.Fatalf("NewTracker: %v", err)
	}
	defer tr.Close()

	// count=1 — below threshold of 3
	now := time.Now().UTC()
	_, err = tr.DB().Exec(
		`INSERT INTO failure_sequences (source_code, target_code, count, first_seen, last_seen)
		 VALUES (?, ?, ?, ?, ?)`,
		"COS-X", "COS-Y", 1, now, now,
	)
	if err != nil {
		t.Fatalf("INSERT failure_sequences: %v", err)
	}

	det := NewDetector(tr.DB())
	det.SequenceCorrelationThreshold = 3

	patterns, err := det.Analyze(time.Time{}, 0)
	if err != nil {
		t.Fatalf("Analyze: %v", err)
	}
	sc := filterByType(patterns, PatternSequenceCorrelation)
	if len(sc) != 0 {
		t.Errorf("SequenceCorrelation count = %d, want 0 (count below threshold)", len(sc))
	}
}

// ---------------------------------------------------------------------------
// Phase 5.1 — All six pattern types fire together
// ---------------------------------------------------------------------------

func TestDetect_Analyze_AllSixPatternTypes(t *testing.T) {
	dbFile := filepath.Join(t.TempDir(), "all-six.db")
	tr, err := NewTracker(dbFile)
	if err != nil {
		t.Fatalf("NewTracker: %v", err)
	}
	defer tr.Close()

	now := time.Now().UTC()

	// 1. PatternRepeatedFailure — "lint" fails 4 times (>= MinRepeats=3)
	for i := 0; i < 4; i++ {
		tr.Record(ExecutionRecord{
			Timestamp: now.Add(time.Duration(i) * time.Second),
			SessionID: "s1", EventType: "before_tool", ToolType: "Bash",
			ValidatorName: "lint", Result: ResultFail, DurationMs: 10, ErrorCode: "COS-LINT-001",
		})
	}

	// 2. PatternPerfRegression — "slow-v": 6 fast then 6 slow (RegressionMinRuns=5 => need 5*2=10)
	for i := 0; i < 6; i++ {
		tr.Record(ExecutionRecord{
			Timestamp: now.Add(time.Duration(i) * time.Minute),
			SessionID: "s2", EventType: "before_tool", ToolType: "Bash",
			ValidatorName: "slow-v", Result: ResultPass, DurationMs: 10,
		})
	}
	for i := 0; i < 6; i++ {
		tr.Record(ExecutionRecord{
			Timestamp: now.Add(time.Duration(20+i) * time.Minute),
			SessionID: "s3", EventType: "before_tool", ToolType: "Bash",
			ValidatorName: "slow-v", Result: ResultPass, DurationMs: 50,
		})
	}

	// 3. PatternErrorCluster — "COS-SEC-001" across 4 distinct sessions (>= ErrorClusterSess=3)
	for i, sess := range []string{"sA", "sB", "sC", "sD"} {
		tr.Record(ExecutionRecord{
			Timestamp: now.Add(time.Duration(i) * time.Second),
			SessionID: sess, EventType: "before_tool", ToolType: "Edit",
			ValidatorName: "sec", Result: ResultFail, DurationMs: 5, ErrorCode: "COS-SEC-001",
		})
	}

	// 4. PatternFalsePositive — "noisy-v": 3 warn + 7 override = 70% override ratio, 10 total
	for i := 0; i < 3; i++ {
		tr.Record(ExecutionRecord{
			Timestamp: now.Add(time.Duration(i) * time.Second),
			SessionID: "s5", EventType: "before_tool", ToolType: "Bash",
			ValidatorName: "noisy-v", Result: ResultWarn, DurationMs: 5,
		})
	}
	for i := 0; i < 7; i++ {
		tr.Record(ExecutionRecord{
			Timestamp: now.Add(time.Duration(10+i) * time.Second),
			SessionID: "s5", EventType: "before_tool", ToolType: "Bash",
			ValidatorName: "noisy-v", Result: ResultOverride, DurationMs: 5,
		})
	}

	// 5. PatternMissingCoverage — 12 events for "SpecialTool" with no validator
	for i := 0; i < 12; i++ {
		tr.Record(ExecutionRecord{
			Timestamp: now.Add(time.Duration(i) * time.Second),
			SessionID: "s6", EventType: "before_tool", ToolType: "SpecialTool",
			ValidatorName: "", Result: ResultPass, DurationMs: 3,
		})
	}

	if err := tr.Flush(); err != nil {
		t.Fatalf("Flush: %v", err)
	}

	// 6. PatternSequenceCorrelation — insert directly with count=4
	_, err = tr.DB().Exec(
		`INSERT INTO failure_sequences (source_code, target_code, count, first_seen, last_seen)
		 VALUES (?, ?, ?, ?, ?)`,
		"COS-LINT-001", "COS-SEC-001", 4, now, now,
	)
	if err != nil {
		t.Fatalf("INSERT failure_sequences: %v", err)
	}

	det := NewDetector(tr.DB())
	det.FalsePositiveMinSample = 5
	det.FalsePositiveThreshold = 0.5
	det.MissingCoverageThreshold = 10
	det.SequenceCorrelationThreshold = 3

	patterns, err := det.Analyze(time.Time{}, 0)
	if err != nil {
		t.Fatalf("Analyze: %v", err)
	}

	seen := map[PatternType]bool{}
	for _, p := range patterns {
		seen[p.Type] = true
	}

	allSix := []PatternType{
		PatternRepeatedFailure,
		PatternFalsePositive,
		PatternMissingCoverage,
		PatternPerfRegression,
		PatternErrorCluster,
		PatternSequenceCorrelation,
	}
	for _, pt := range allSix {
		if !seen[pt] {
			t.Errorf("missing pattern type %q in output (all patterns: %v)", pt, patterns)
		}
	}
	if len(patterns) < 6 {
		t.Errorf("len(patterns) = %d, want >= 6", len(patterns))
	}
}
