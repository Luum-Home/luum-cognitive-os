package pattern

import (
	"database/sql"
	"errors"
	"fmt"
	"sync"
	"time"

	// Pure-Go SQLite driver (no CGo) — keeps cross-compilation simple.
	_ "modernc.org/sqlite"
)

// schemaSQL is the embedded subset of docs/04-Concepts/architecture/cos-dispatch/schema.sql
// covering all 5 tables: executions, detected_patterns, generated_artifacts,
// failure_sequences, session_summaries. Wrapped in IF NOT EXISTS so calling
// NewTracker on an existing database is a no-op.
const schemaSQL = `
CREATE TABLE IF NOT EXISTS executions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    session_id      TEXT NOT NULL,
    event_type      TEXT NOT NULL,
    tool_type       TEXT NOT NULL,
    tool_input_hash TEXT,
    validator_name  TEXT NOT NULL,
    result          TEXT NOT NULL CHECK(result IN ('pass','fail','warn','transform','override')),
    -- override = a warn/fail result dismissed by a human or downstream system;
    -- primary source signal for FalsePositive detection in Phase 5.1.
    duration_ms     INTEGER NOT NULL,
    error_code      TEXT,
    error_message   TEXT,
    context_hash    TEXT
);
CREATE INDEX IF NOT EXISTS idx_executions_session    ON executions(session_id);
CREATE INDEX IF NOT EXISTS idx_executions_validator  ON executions(validator_name, result);
CREATE INDEX IF NOT EXISTS idx_executions_timestamp  ON executions(timestamp);
CREATE INDEX IF NOT EXISTS idx_executions_error_code ON executions(error_code);
CREATE INDEX IF NOT EXISTS idx_executions_tool       ON executions(tool_type, event_type);

CREATE TABLE IF NOT EXISTS detected_patterns (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    pattern_type     TEXT NOT NULL,
    description      TEXT NOT NULL,
    confidence       REAL NOT NULL,
    first_seen       DATETIME NOT NULL,
    last_seen        DATETIME NOT NULL,
    occurrence_count INTEGER NOT NULL DEFAULT 1,
    auto_fixable     BOOLEAN NOT NULL DEFAULT 0,
    suggestion       TEXT,
    status           TEXT NOT NULL DEFAULT 'active'
);
CREATE INDEX IF NOT EXISTS idx_patterns_status ON detected_patterns(status);
CREATE INDEX IF NOT EXISTS idx_patterns_type   ON detected_patterns(pattern_type);

CREATE TABLE IF NOT EXISTS generated_artifacts (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    name              TEXT NOT NULL UNIQUE,
    artifact_type     TEXT NOT NULL,
    source_pattern_id INTEGER REFERENCES detected_patterns(id),
    language          TEXT NOT NULL,
    code              TEXT NOT NULL,
    config_snippet    TEXT,
    confidence        REAL NOT NULL,
    generated_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    enabled           BOOLEAN NOT NULL DEFAULT 0,
    feedback          TEXT
);
CREATE INDEX IF NOT EXISTS idx_artifacts_enabled ON generated_artifacts(enabled);
CREATE INDEX IF NOT EXISTS idx_artifacts_source  ON generated_artifacts(source_pattern_id);

CREATE TABLE IF NOT EXISTS session_summaries (
    session_id          TEXT PRIMARY KEY,
    started_at          DATETIME NOT NULL,
    ended_at            DATETIME,
    total_executions    INTEGER NOT NULL DEFAULT 0,
    total_failures      INTEGER NOT NULL DEFAULT 0,
    total_duration_ms   INTEGER NOT NULL DEFAULT 0,
    patterns_detected   INTEGER NOT NULL DEFAULT 0,
    artifacts_generated INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS failure_sequences (
    source_code TEXT NOT NULL,
    target_code TEXT NOT NULL,
    count       INTEGER NOT NULL DEFAULT 1,
    first_seen  DATETIME NOT NULL,
    last_seen   DATETIME NOT NULL,
    PRIMARY KEY (source_code, target_code)
);
`

// defaultBufferSize is how many records the Tracker holds in memory before
// auto-flushing. Tuned so a typical session (~hundreds of validator calls)
// produces a small number of disk writes.
const defaultBufferSize = 64

// SQLTracker is a buffered, goroutine-safe Tracker backed by SQLite.
type SQLTracker struct {
	db         *sql.DB
	bufferSize int

	mu     sync.Mutex
	buffer []ExecutionRecord
	closed bool
}

// NewTracker opens (or creates) the SQLite database at dbPath, applies the
// schema if missing, and returns a SQLTracker ready to Record events.
//
// dbPath may be ":memory:" for tests. The caller is responsible for calling
// Close() to flush pending records and release the database handle.
func NewTracker(dbPath string) (*SQLTracker, error) {
	if dbPath == "" {
		return nil, errors.New("pattern: NewTracker requires a non-empty dbPath")
	}

	db, err := sql.Open("sqlite", dbPath)
	if err != nil {
		return nil, fmt.Errorf("pattern: open %q: %w", dbPath, err)
	}

	// In-memory databases live inside a single SQLite connection. Go's sql
	// pool may open multiple connections, each with its own empty in-memory
	// DB — that produces "no such table" errors when the Detector reads
	// from a different connection than the one the schema was applied to.
	// Pin the pool to one connection for ":memory:" to keep tests reliable.
	if dbPath == ":memory:" {
		db.SetMaxOpenConns(1)
	} else {
		// modernc.org/sqlite respects PRAGMAs via Exec; enable WAL for
		// concurrent readers (the Detector) while the dispatcher writes.
		_, _ = db.Exec("PRAGMA journal_mode=WAL;")
		_, _ = db.Exec("PRAGMA synchronous=NORMAL;")
	}

	if _, err := db.Exec(schemaSQL); err != nil {
		_ = db.Close()
		return nil, fmt.Errorf("pattern: apply schema: %w", err)
	}

	return &SQLTracker{
		db:         db,
		bufferSize: defaultBufferSize,
		buffer:     make([]ExecutionRecord, 0, defaultBufferSize),
	}, nil
}

// DB exposes the underlying *sql.DB for read-only queries (e.g., Detector).
// Callers must not close it; use SQLTracker.Close() instead.
func (t *SQLTracker) DB() *sql.DB { return t.db }

// SetBufferSize overrides the auto-flush threshold. Useful in tests or when
// the dispatcher wants stricter durability guarantees. Must be > 0.
func (t *SQLTracker) SetBufferSize(n int) {
	if n <= 0 {
		return
	}
	t.mu.Lock()
	t.bufferSize = n
	t.mu.Unlock()
}

// Record buffers a single execution. If the buffer reaches its threshold,
// it is flushed inline. The call returns immediately; flush errors are
// captured by the next Flush() invocation (the dispatcher hot-path
// intentionally does not surface them).
func (t *SQLTracker) Record(rec ExecutionRecord) {
	t.mu.Lock()
	defer t.mu.Unlock()
	if t.closed {
		return
	}
	if rec.Timestamp.IsZero() {
		rec.Timestamp = time.Now().UTC()
	}
	t.buffer = append(t.buffer, rec)
	if len(t.buffer) >= t.bufferSize {
		// Best-effort inline flush; ignore error so dispatcher never blocks
		// on disk failure. The next explicit Flush() will retry.
		_ = t.flushLocked()
	}
}

// Flush writes any buffered records to the database. Safe to call multiple
// times. Idempotent on an empty buffer.
func (t *SQLTracker) Flush() error {
	t.mu.Lock()
	defer t.mu.Unlock()
	return t.flushLocked()
}

// flushLocked must be called with t.mu held.
func (t *SQLTracker) flushLocked() error {
	if len(t.buffer) == 0 {
		return nil
	}

	tx, err := t.db.Begin()
	if err != nil {
		return fmt.Errorf("pattern: begin tx: %w", err)
	}

	const insertSQL = `INSERT INTO executions
        (timestamp, session_id, event_type, tool_type, tool_input_hash,
         validator_name, result, duration_ms, error_code, error_message, context_hash)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`

	stmt, err := tx.Prepare(insertSQL)
	if err != nil {
		_ = tx.Rollback()
		return fmt.Errorf("pattern: prepare insert: %w", err)
	}
	defer stmt.Close()

	for _, r := range t.buffer {
		if _, err := stmt.Exec(
			r.Timestamp,
			r.SessionID,
			r.EventType,
			r.ToolType,
			nullableString(r.ToolInputHash),
			r.ValidatorName,
			r.Result,
			r.DurationMs,
			nullableString(r.ErrorCode),
			nullableString(r.ErrorMessage),
			nullableString(r.ContextHash),
		); err != nil {
			_ = tx.Rollback()
			return fmt.Errorf("pattern: insert execution: %w", err)
		}
	}

	// Populate failure_sequences: detect consecutive failure pairs within the
	// same session in this flush batch and upsert into failure_sequences.
	// "Consecutive" means adjacent positions in the buffer with the same
	// session_id. Cross-session sequences are deferred to Phase 5.1.
	if err := insertFailureSequences(tx, t.buffer); err != nil {
		_ = tx.Rollback()
		return fmt.Errorf("pattern: insert failure sequences: %w", err)
	}

	if err := tx.Commit(); err != nil {
		return fmt.Errorf("pattern: commit tx: %w", err)
	}

	t.buffer = t.buffer[:0]
	return nil
}

// insertFailureSequences scans the flush batch for consecutive failure pairs
// within the same session and upserts them into the failure_sequences table.
// "Failure" means result is ResultFail or ResultWarn (not pass/transform/override).
// Only adjacent records sharing a session_id are considered; cross-session
// detection is out of scope for Phase 5.0.
func insertFailureSequences(tx *sql.Tx, batch []ExecutionRecord) error {
	if len(batch) < 2 {
		return nil
	}

	const upsertSQL = `
INSERT INTO failure_sequences (source_code, target_code, count, first_seen, last_seen)
VALUES (?, ?, 1, ?, ?)
ON CONFLICT(source_code, target_code) DO UPDATE SET
    count    = failure_sequences.count + 1,
    last_seen = excluded.last_seen`

	stmt, err := tx.Prepare(upsertSQL)
	if err != nil {
		return fmt.Errorf("prepare upsert: %w", err)
	}
	defer stmt.Close()

	isFailure := func(r ExecutionRecord) bool {
		return r.Result == ResultFail || r.Result == ResultWarn
	}

	now := time.Now().UTC()
	for i := 1; i < len(batch); i++ {
		prev, cur := batch[i-1], batch[i]
		if prev.SessionID != cur.SessionID {
			continue
		}
		if !isFailure(prev) || !isFailure(cur) {
			continue
		}
		src := prev.ErrorCode
		tgt := cur.ErrorCode
		if src == "" || tgt == "" {
			// Without error codes we cannot build a meaningful sequence key.
			continue
		}
		if _, err := stmt.Exec(src, tgt, now, now); err != nil {
			return fmt.Errorf("upsert sequence %s->%s: %w", src, tgt, err)
		}
	}
	return nil
}

// Close flushes any pending records and releases the database handle.
// Subsequent Record/Flush calls become no-ops.
func (t *SQLTracker) Close() error {
	t.mu.Lock()
	defer t.mu.Unlock()
	if t.closed {
		return nil
	}
	flushErr := t.flushLocked()
	closeErr := t.db.Close()
	t.closed = true
	if flushErr != nil {
		return flushErr
	}
	return closeErr
}

// nullableString turns "" into NULL so empty optional columns aren't stored
// as empty strings (cleaner Detector queries).
func nullableString(s string) any {
	if s == "" {
		return nil
	}
	return s
}
