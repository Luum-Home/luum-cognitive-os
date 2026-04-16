package pattern

import (
	"path/filepath"
	"testing"
	"time"
)

func TestNewTracker_AppliesSchema(t *testing.T) {
	dbPath := filepath.Join(t.TempDir(), "patterns.db")
	tr, err := NewTracker(dbPath)
	if err != nil {
		t.Fatalf("NewTracker: %v", err)
	}
	defer tr.Close()

	// Schema should be in place: querying sqlite_master must succeed and
	// return our five tables.
	rows, err := tr.DB().Query(`SELECT name FROM sqlite_master WHERE type='table' ORDER BY name`)
	if err != nil {
		t.Fatalf("query schema: %v", err)
	}
	defer rows.Close()

	want := map[string]bool{
		"detected_patterns":   false,
		"executions":          false,
		"failure_sequences":   false,
		"generated_artifacts": false,
		"session_summaries":   false,
	}
	for rows.Next() {
		var name string
		if err := rows.Scan(&name); err != nil {
			t.Fatalf("scan: %v", err)
		}
		if _, ok := want[name]; ok {
			want[name] = true
		}
	}
	for tbl, seen := range want {
		if !seen {
			t.Errorf("table %q missing from schema", tbl)
		}
	}
}

func TestTracker_RecordFlushQuery_Roundtrip(t *testing.T) {
	tr, err := NewTracker(":memory:")
	if err != nil {
		t.Fatalf("NewTracker: %v", err)
	}
	defer tr.Close()

	now := time.Date(2026, 4, 15, 12, 0, 0, 0, time.UTC)
	tr.Record(ExecutionRecord{
		Timestamp:     now,
		SessionID:     "sess-1",
		EventType:     "before_tool",
		ToolType:      "Bash",
		ValidatorName: "rate-limiter",
		Result:        ResultPass,
		DurationMs:    12,
	})
	tr.Record(ExecutionRecord{
		Timestamp:     now.Add(time.Second),
		SessionID:     "sess-1",
		EventType:     "before_tool",
		ToolType:      "Bash",
		ValidatorName: "secret-detector",
		Result:        ResultFail,
		DurationMs:    34,
		ErrorCode:     "COS-SEC-001",
		ErrorMessage:  "leaked api key",
	})

	if err := tr.Flush(); err != nil {
		t.Fatalf("Flush: %v", err)
	}

	var count int
	if err := tr.DB().QueryRow(`SELECT COUNT(*) FROM executions`).Scan(&count); err != nil {
		t.Fatalf("count: %v", err)
	}
	if count != 2 {
		t.Errorf("count = %d, want 2", count)
	}

	// nullableString sentinel: empty optional fields should be NULL
	var nullCount int
	if err := tr.DB().QueryRow(`SELECT COUNT(*) FROM executions WHERE error_code IS NULL`).Scan(&nullCount); err != nil {
		t.Fatalf("null check: %v", err)
	}
	if nullCount != 1 {
		t.Errorf("expected 1 row with NULL error_code, got %d", nullCount)
	}

	// Pull the failing row back and verify field roundtrip
	rows, err := tr.DB().Query(`SELECT validator_name, result, error_code, error_message, duration_ms
	                            FROM executions WHERE result = ?`, ResultFail)
	if err != nil {
		t.Fatalf("query fail: %v", err)
	}
	defer rows.Close()
	if !rows.Next() {
		t.Fatal("expected one failing row")
	}
	var (
		name, result, ecode, emsg string
		dur                       int64
	)
	if err := rows.Scan(&name, &result, &ecode, &emsg, &dur); err != nil {
		t.Fatalf("scan: %v", err)
	}
	if name != "secret-detector" || result != ResultFail || ecode != "COS-SEC-001" ||
		emsg != "leaked api key" || dur != 34 {
		t.Errorf("roundtrip mismatch: name=%q result=%q ecode=%q emsg=%q dur=%d",
			name, result, ecode, emsg, dur)
	}
}

func TestTracker_AutoFlushOnBufferFull(t *testing.T) {
	tr, err := NewTracker(":memory:")
	if err != nil {
		t.Fatalf("NewTracker: %v", err)
	}
	defer tr.Close()

	tr.SetBufferSize(3)

	for i := 0; i < 5; i++ {
		tr.Record(ExecutionRecord{
			SessionID:     "sess-auto",
			EventType:     "before_tool",
			ToolType:      "Bash",
			ValidatorName: "v",
			Result:        ResultPass,
			DurationMs:    1,
		})
	}

	// After 5 records with bufferSize=3, the first three should already be on
	// disk (auto-flushed when size hit 3). Two are still buffered.
	var onDisk int
	if err := tr.DB().QueryRow(`SELECT COUNT(*) FROM executions`).Scan(&onDisk); err != nil {
		t.Fatalf("count: %v", err)
	}
	if onDisk != 3 {
		t.Errorf("auto-flush count = %d, want 3", onDisk)
	}

	if err := tr.Flush(); err != nil {
		t.Fatalf("Flush: %v", err)
	}

	if err := tr.DB().QueryRow(`SELECT COUNT(*) FROM executions`).Scan(&onDisk); err != nil {
		t.Fatalf("count: %v", err)
	}
	if onDisk != 5 {
		t.Errorf("post-flush count = %d, want 5", onDisk)
	}
}

func TestTracker_CloseFlushesAndIsIdempotent(t *testing.T) {
	dbPath := filepath.Join(t.TempDir(), "p.db")
	tr, err := NewTracker(dbPath)
	if err != nil {
		t.Fatalf("NewTracker: %v", err)
	}

	tr.Record(ExecutionRecord{
		SessionID:     "sess-close",
		EventType:     "before_tool",
		ToolType:      "Bash",
		ValidatorName: "v",
		Result:        ResultPass,
		DurationMs:    1,
	})

	if err := tr.Close(); err != nil {
		t.Fatalf("Close: %v", err)
	}

	// Subsequent Record/Flush after Close are no-ops, not panics.
	tr.Record(ExecutionRecord{ValidatorName: "ignored"})
	if err := tr.Flush(); err != nil {
		t.Errorf("Flush after Close: %v", err)
	}
	if err := tr.Close(); err != nil {
		t.Errorf("second Close: %v", err)
	}

	// Reopen the file and verify the buffered record was flushed on Close.
	tr2, err := NewTracker(dbPath)
	if err != nil {
		t.Fatalf("reopen: %v", err)
	}
	defer tr2.Close()

	var n int
	if err := tr2.DB().QueryRow(`SELECT COUNT(*) FROM executions`).Scan(&n); err != nil {
		t.Fatalf("count: %v", err)
	}
	if n != 1 {
		t.Errorf("rows after Close+reopen = %d, want 1", n)
	}
}

func TestNewTracker_RejectsEmptyPath(t *testing.T) {
	if _, err := NewTracker(""); err == nil {
		t.Fatal("expected error for empty dbPath")
	}
}

// TestFailureSequences_TwoConsecutiveFails verifies that two adjacent failure
// records in the same session produce one row in failure_sequences with count=1.
func TestFailureSequences_TwoConsecutiveFails(t *testing.T) {
	tr, err := NewTracker(":memory:")
	if err != nil {
		t.Fatalf("NewTracker: %v", err)
	}
	defer tr.Close()

	tr.SetBufferSize(10) // prevent auto-flush mid-test

	now := time.Date(2026, 4, 16, 10, 0, 0, 0, time.UTC)
	tr.Record(ExecutionRecord{
		Timestamp:     now,
		SessionID:     "sess-seq",
		EventType:     "before_tool",
		ToolType:      "Bash",
		ValidatorName: "v1",
		Result:        ResultFail,
		DurationMs:    5,
		ErrorCode:     "COS-001",
	})
	tr.Record(ExecutionRecord{
		Timestamp:     now.Add(time.Second),
		SessionID:     "sess-seq",
		EventType:     "before_tool",
		ToolType:      "Bash",
		ValidatorName: "v2",
		Result:        ResultFail,
		DurationMs:    6,
		ErrorCode:     "COS-002",
	})

	if err := tr.Flush(); err != nil {
		t.Fatalf("Flush: %v", err)
	}

	var count int
	if err := tr.DB().QueryRow(
		`SELECT count FROM failure_sequences WHERE source_code=? AND target_code=?`,
		"COS-001", "COS-002",
	).Scan(&count); err != nil {
		t.Fatalf("query failure_sequences: %v", err)
	}
	if count != 1 {
		t.Errorf("failure_sequences count = %d, want 1", count)
	}
}

// TestFailureSequences_TripleRepeat verifies that the same consecutive failure
// pair flushed in three separate batches accumulates to count=3.
func TestFailureSequences_TripleRepeat(t *testing.T) {
	tr, err := NewTracker(":memory:")
	if err != nil {
		t.Fatalf("NewTracker: %v", err)
	}
	defer tr.Close()

	tr.SetBufferSize(10) // manual flush only

	now := time.Date(2026, 4, 16, 11, 0, 0, 0, time.UTC)
	addPair := func(offset time.Duration) {
		tr.Record(ExecutionRecord{
			Timestamp: now.Add(offset), SessionID: "sess-triple",
			EventType: "before_tool", ToolType: "Edit",
			ValidatorName: "va", Result: ResultFail,
			DurationMs: 1, ErrorCode: "COS-A",
		})
		tr.Record(ExecutionRecord{
			Timestamp: now.Add(offset + time.Millisecond), SessionID: "sess-triple",
			EventType: "before_tool", ToolType: "Edit",
			ValidatorName: "vb", Result: ResultFail,
			DurationMs: 1, ErrorCode: "COS-B",
		})
		if err := tr.Flush(); err != nil {
			t.Fatalf("Flush: %v", err)
		}
	}

	addPair(0)
	addPair(10 * time.Second)
	addPair(20 * time.Second)

	var count int
	if err := tr.DB().QueryRow(
		`SELECT count FROM failure_sequences WHERE source_code=? AND target_code=?`,
		"COS-A", "COS-B",
	).Scan(&count); err != nil {
		t.Fatalf("query failure_sequences: %v", err)
	}
	if count != 3 {
		t.Errorf("failure_sequences count = %d, want 3", count)
	}
}

// TestSchemaContainsGeneratedArtifacts verifies that the generated_artifacts
// table exists in a fresh database and contains the expected columns.
// This guards against fresh-install failures in Phase 5.2 (Generator), which
// INSERTs new artifacts into this table.
func TestSchemaContainsGeneratedArtifacts(t *testing.T) {
	dbPath := filepath.Join(t.TempDir(), "artifacts-schema.db")
	tr, err := NewTracker(dbPath)
	if err != nil {
		t.Fatalf("NewTracker: %v", err)
	}
	defer tr.Close()

	// 1. Table must exist.
	var tableName string
	err = tr.DB().QueryRow(
		`SELECT name FROM sqlite_master WHERE type='table' AND name='generated_artifacts'`,
	).Scan(&tableName)
	if err != nil {
		t.Fatalf("generated_artifacts table not found in schema: %v", err)
	}

	// 2. Expected columns must be present (names only; PRAGMA returns one row per column).
	rows, err := tr.DB().Query(`PRAGMA table_info(generated_artifacts)`)
	if err != nil {
		t.Fatalf("PRAGMA table_info: %v", err)
	}
	defer rows.Close()

	wantCols := map[string]bool{
		"id":                false,
		"name":              false,
		"artifact_type":     false,
		"source_pattern_id": false,
		"language":          false,
		"code":              false,
		"config_snippet":    false,
		"confidence":        false,
		"generated_at":      false,
		"enabled":           false,
		"feedback":          false,
	}
	for rows.Next() {
		var (
			cid       int
			colName   string
			colType   string
			notNull   int
			dfltValue any
			pk        int
		)
		if err := rows.Scan(&cid, &colName, &colType, &notNull, &dfltValue, &pk); err != nil {
			t.Fatalf("scan PRAGMA row: %v", err)
		}
		if _, ok := wantCols[colName]; ok {
			wantCols[colName] = true
		}
	}
	if err := rows.Err(); err != nil {
		t.Fatalf("PRAGMA rows: %v", err)
	}

	for col, seen := range wantCols {
		if !seen {
			t.Errorf("column %q missing from generated_artifacts", col)
		}
	}
}

// TestFailureSequences_CrossSessionNotCounted confirms that adjacent failures
// in DIFFERENT sessions do NOT create a failure_sequences row.
func TestFailureSequences_CrossSessionNotCounted(t *testing.T) {
	tr, err := NewTracker(":memory:")
	if err != nil {
		t.Fatalf("NewTracker: %v", err)
	}
	defer tr.Close()

	tr.SetBufferSize(10)

	now := time.Date(2026, 4, 16, 12, 0, 0, 0, time.UTC)
	tr.Record(ExecutionRecord{
		Timestamp: now, SessionID: "sess-A",
		EventType: "before_tool", ToolType: "Bash",
		ValidatorName: "v1", Result: ResultFail,
		DurationMs: 1, ErrorCode: "COS-001",
	})
	tr.Record(ExecutionRecord{
		Timestamp: now.Add(time.Second), SessionID: "sess-B",
		EventType: "before_tool", ToolType: "Bash",
		ValidatorName: "v2", Result: ResultFail,
		DurationMs: 1, ErrorCode: "COS-002",
	})

	if err := tr.Flush(); err != nil {
		t.Fatalf("Flush: %v", err)
	}

	var rowCount int
	if err := tr.DB().QueryRow(`SELECT COUNT(*) FROM failure_sequences`).Scan(&rowCount); err != nil {
		t.Fatalf("count: %v", err)
	}
	if rowCount != 0 {
		t.Errorf("cross-session sequences = %d, want 0", rowCount)
	}
}
