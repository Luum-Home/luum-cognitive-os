-- cos-dispatch: Pattern Tracking Database Schema
-- SQLite, stored at .cognitive-os/patterns.db

-- Core execution log: one row per validator/transformer execution
CREATE TABLE executions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    session_id      TEXT NOT NULL,
    event_type      TEXT NOT NULL,          -- 'before_tool', 'after_tool', 'session_start', etc.
    tool_type       TEXT NOT NULL,          -- 'Bash', 'Write', 'Edit', 'Agent', etc.
    tool_input_hash TEXT,                   -- SHA-256 of normalized input (for dedup)
    validator_name  TEXT NOT NULL,
    result          TEXT NOT NULL,          -- 'pass', 'fail', 'warn', 'transform'
    duration_ms     INTEGER NOT NULL,
    error_code      TEXT,
    error_message   TEXT,
    context_hash    TEXT                    -- dedup key for same-input retries
);

CREATE INDEX idx_executions_session ON executions(session_id);
CREATE INDEX idx_executions_validator ON executions(validator_name, result);
CREATE INDEX idx_executions_timestamp ON executions(timestamp);
CREATE INDEX idx_executions_error_code ON executions(error_code);
CREATE INDEX idx_executions_tool ON executions(tool_type, event_type);

-- Detected patterns and their lifecycle
CREATE TABLE detected_patterns (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    pattern_type     TEXT NOT NULL,         -- 'repeated_failure', 'false_positive', 'missing_coverage',
                                            --  'perf_regression', 'error_cluster', 'sequence_correlation'
    description      TEXT NOT NULL,
    confidence       REAL NOT NULL,         -- 0.0 to 1.0
    first_seen       DATETIME NOT NULL,
    last_seen        DATETIME NOT NULL,
    occurrence_count INTEGER NOT NULL DEFAULT 1,
    auto_fixable     BOOLEAN NOT NULL DEFAULT 0,
    suggestion       TEXT,
    status           TEXT NOT NULL DEFAULT 'active'  -- 'active', 'addressed', 'dismissed'
);

CREATE INDEX idx_patterns_status ON detected_patterns(status);
CREATE INDEX idx_patterns_type ON detected_patterns(pattern_type);

-- Generated artifacts from auto-generator
CREATE TABLE generated_artifacts (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    name              TEXT NOT NULL UNIQUE,
    artifact_type     TEXT NOT NULL,        -- 'validator', 'transformer', 'plugin', 'rule'
    source_pattern_id INTEGER REFERENCES detected_patterns(id),
    language          TEXT NOT NULL,        -- 'go', 'bash'
    code              TEXT NOT NULL,
    config_snippet    TEXT,                 -- TOML to register with enabled=false
    confidence        REAL NOT NULL,
    generated_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    enabled           BOOLEAN NOT NULL DEFAULT 0,
    feedback          TEXT                  -- 'enabled', 'disabled', 'modified', 'deleted'
);

CREATE INDEX idx_artifacts_enabled ON generated_artifacts(enabled);
CREATE INDEX idx_artifacts_source ON generated_artifacts(source_pattern_id);

-- Failure sequence tracking: when fixing error A causes error B
CREATE TABLE failure_sequences (
    source_code TEXT NOT NULL,
    target_code TEXT NOT NULL,
    count       INTEGER NOT NULL DEFAULT 1,
    first_seen  DATETIME NOT NULL,
    last_seen   DATETIME NOT NULL,
    PRIMARY KEY (source_code, target_code)
);

-- Session summary for cross-session pattern analysis
CREATE TABLE session_summaries (
    session_id       TEXT PRIMARY KEY,
    started_at       DATETIME NOT NULL,
    ended_at         DATETIME,
    total_executions INTEGER NOT NULL DEFAULT 0,
    total_failures   INTEGER NOT NULL DEFAULT 0,
    total_duration_ms INTEGER NOT NULL DEFAULT 0,
    patterns_detected INTEGER NOT NULL DEFAULT 0,
    artifacts_generated INTEGER NOT NULL DEFAULT 0
);
