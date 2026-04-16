package pattern

import (
	"database/sql"
	"errors"
	"fmt"
	"math"
	"time"
)

// SQLDetector reads execution history from a SQLTracker (or any *sql.DB
// matching the schema) and surfaces DetectedPatterns.
//
// Phase 4 implements three of the six pattern types:
//   - RepeatedFailure: same (validator, error_code) seen ≥ minRepeats times
//   - PerfRegression:  validator's recent mean latency vs older mean
//   - ErrorCluster:    same error_code spans ≥ minSessions distinct sessions
type SQLDetector struct {
	db *sql.DB

	// Tunables — defaults set in NewDetector.
	MinRepeats        int     // RepeatedFailure: failures threshold (default 3)
	MaxEvidence       int     // cap evidence rows per pattern   (default 5)
	RegressionFactor  float64 // PerfRegression slowdown ratio   (default 1.5x)
	RegressionMinRuns int     // PerfRegression min runs each window (default 5)
	ErrorClusterSess  int     // ErrorCluster distinct-session threshold (default 3)
}

// NewDetector returns a SQLDetector wired to the given database.
func NewDetector(db *sql.DB) *SQLDetector {
	if db == nil {
		return nil
	}
	return &SQLDetector{
		db:                db,
		MinRepeats:        3,
		MaxEvidence:       5,
		RegressionFactor:  1.5,
		RegressionMinRuns: 5,
		ErrorClusterSess:  3,
	}
}

// Analyze runs all detectors over executions newer than `since` and returns
// patterns whose confidence is at least minConfidence.
func (d *SQLDetector) Analyze(since time.Time, minConfidence float64) ([]DetectedPattern, error) {
	if d == nil || d.db == nil {
		return nil, errors.New("pattern: detector has no database")
	}

	var out []DetectedPattern

	repeats, err := d.detectRepeatedFailures(since, "")
	if err != nil {
		return nil, fmt.Errorf("repeated_failure: %w", err)
	}
	out = append(out, repeats...)

	regs, err := d.detectPerfRegressions(since)
	if err != nil {
		return nil, fmt.Errorf("perf_regression: %w", err)
	}
	out = append(out, regs...)

	clusters, err := d.detectErrorClusters(since)
	if err != nil {
		return nil, fmt.Errorf("error_cluster: %w", err)
	}
	out = append(out, clusters...)

	return filterByConfidence(out, minConfidence), nil
}

// AnalyzeSession runs the session-scoped detectors. RepeatedFailure is the
// most useful single-session signal; PerfRegression and ErrorCluster need
// cross-session history and are skipped here.
func (d *SQLDetector) AnalyzeSession(sessionID string, minConfidence float64) ([]DetectedPattern, error) {
	if d == nil || d.db == nil {
		return nil, errors.New("pattern: detector has no database")
	}
	if sessionID == "" {
		return nil, errors.New("pattern: AnalyzeSession requires a session_id")
	}

	repeats, err := d.detectRepeatedFailures(time.Time{}, sessionID)
	if err != nil {
		return nil, fmt.Errorf("repeated_failure: %w", err)
	}

	return filterByConfidence(repeats, minConfidence), nil
}

// ---------------------------------------------------------------------------
// RepeatedFailure
// ---------------------------------------------------------------------------

// detectRepeatedFailures groups failed executions by (validator, error_code)
// and reports any group with at least MinRepeats hits. Confidence scales
// with occurrence count, capped at 1.0.
func (d *SQLDetector) detectRepeatedFailures(since time.Time, sessionID string) ([]DetectedPattern, error) {
	query := `SELECT validator_name, COALESCE(error_code, ''), COUNT(*) AS n
              FROM executions
              WHERE result = ?`
	args := []any{ResultFail}

	if !since.IsZero() {
		query += " AND timestamp >= ?"
		args = append(args, since)
	}
	if sessionID != "" {
		query += " AND session_id = ?"
		args = append(args, sessionID)
	}
	query += `
        GROUP BY validator_name, error_code
        HAVING n >= ?
        ORDER BY n DESC`
	args = append(args, d.MinRepeats)

	type group struct {
		validator string
		errCode   string
		count     int
	}
	rows, err := d.db.Query(query, args...)
	if err != nil {
		return nil, err
	}

	// Collect group results before issuing per-group evidence queries; on a
	// pinned single-connection database (e.g., :memory:), keeping the outer
	// rows open while running nested queries deadlocks the connection pool.
	var groups []group
	for rows.Next() {
		var g group
		if err := rows.Scan(&g.validator, &g.errCode, &g.count); err != nil {
			rows.Close()
			return nil, err
		}
		groups = append(groups, g)
	}
	if err := rows.Err(); err != nil {
		rows.Close()
		return nil, err
	}
	rows.Close()

	var patterns []DetectedPattern
	for _, g := range groups {
		evidence, err := d.evidenceForFailure(g.validator, g.errCode, since, sessionID)
		if err != nil {
			return nil, err
		}

		desc := fmt.Sprintf("%s failed %d times", g.validator, g.count)
		if g.errCode != "" {
			desc = fmt.Sprintf("%s failed %d times with code %s", g.validator, g.count, g.errCode)
		}

		// Confidence: 0.5 at MinRepeats, asymptotes to 1.0.
		// (count - MinRepeats + 1) / (count - MinRepeats + 2)
		extra := float64(g.count - d.MinRepeats + 1)
		conf := 0.5 + 0.5*(extra/(extra+1))

		patterns = append(patterns, DetectedPattern{
			Type:        PatternRepeatedFailure,
			Description: desc,
			Confidence:  round2(conf),
			Evidence:    evidence,
			Suggestion: fmt.Sprintf(
				"Investigate %s — %d consecutive failures suggest a real bug or noisy validator. "+
					"If the validator is wrong, disable it via cognitive-os.yaml.",
				g.validator, g.count),
			AutoFixable: false,
		})
	}
	return patterns, nil
}

func (d *SQLDetector) evidenceForFailure(validator, errCode string, since time.Time, sessionID string) ([]ExecutionRecord, error) {
	query := `SELECT id, timestamp, session_id, event_type, tool_type,
                     COALESCE(tool_input_hash, ''), validator_name, result, duration_ms,
                     COALESCE(error_code, ''), COALESCE(error_message, ''), COALESCE(context_hash, '')
              FROM executions
              WHERE validator_name = ? AND result = ? AND COALESCE(error_code, '') = ?`
	args := []any{validator, ResultFail, errCode}
	if !since.IsZero() {
		query += " AND timestamp >= ?"
		args = append(args, since)
	}
	if sessionID != "" {
		query += " AND session_id = ?"
		args = append(args, sessionID)
	}
	query += " ORDER BY timestamp DESC LIMIT ?"
	args = append(args, d.MaxEvidence)

	return scanExecutions(d.db, query, args...)
}

// ---------------------------------------------------------------------------
// PerfRegression
// ---------------------------------------------------------------------------

// detectPerfRegressions splits each validator's history into a "recent" and
// "older" window at the midpoint, and flags validators whose recent mean
// duration is at least RegressionFactor× the older mean. Both windows must
// have at least RegressionMinRuns samples.
func (d *SQLDetector) detectPerfRegressions(since time.Time) ([]DetectedPattern, error) {
	query := `SELECT validator_name, timestamp, duration_ms
              FROM executions
              WHERE 1=1`
	var args []any
	if !since.IsZero() {
		query += " AND timestamp >= ?"
		args = append(args, since)
	}
	query += " ORDER BY validator_name, timestamp ASC"

	rows, err := d.db.Query(query, args...)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	byValidator := map[string][]perfSample{}
	for rows.Next() {
		var (
			name string
			ts   time.Time
			dur  int64
		)
		if err := rows.Scan(&name, &ts, &dur); err != nil {
			return nil, err
		}
		byValidator[name] = append(byValidator[name], perfSample{ts: ts, ms: dur})
	}
	if err := rows.Err(); err != nil {
		return nil, err
	}

	var patterns []DetectedPattern
	for name, samples := range byValidator {
		min := d.RegressionMinRuns * 2
		if len(samples) < min {
			continue
		}
		mid := len(samples) / 2
		older := samples[:mid]
		recent := samples[mid:]

		olderMean := meanDuration(older)
		recentMean := meanDuration(recent)
		if olderMean <= 0 {
			continue
		}
		ratio := recentMean / olderMean
		if ratio < d.RegressionFactor {
			continue
		}

		// Take the slowest recent runs as evidence so a human can spot the
		// timestamps where the regression appears.
		evidence, err := d.recentSlowExecutions(name, recent[0].ts, d.MaxEvidence)
		if err != nil {
			return nil, err
		}

		// Confidence scales with how far over the threshold we are.
		// At the threshold (ratio == factor) -> 0.55; doubling factor -> ~0.9
		over := ratio / d.RegressionFactor
		conf := 0.5 + 0.5*(1.0-1.0/over)
		if conf > 1 {
			conf = 1
		}

		patterns = append(patterns, DetectedPattern{
			Type: PatternPerfRegression,
			Description: fmt.Sprintf(
				"%s slowed from %.1fms to %.1fms mean (%.2fx)",
				name, olderMean, recentMean, ratio),
			Confidence: round2(conf),
			Evidence:   evidence,
			Suggestion: fmt.Sprintf(
				"Profile %s; recent runs are %.2fx slower than earlier runs. "+
					"Consider caching, narrower scope, or moving to a less-frequent event.",
				name, ratio),
			AutoFixable: false,
		})
	}
	return patterns, nil
}

func (d *SQLDetector) recentSlowExecutions(validator string, since time.Time, limit int) ([]ExecutionRecord, error) {
	query := `SELECT id, timestamp, session_id, event_type, tool_type,
                     COALESCE(tool_input_hash, ''), validator_name, result, duration_ms,
                     COALESCE(error_code, ''), COALESCE(error_message, ''), COALESCE(context_hash, '')
              FROM executions
              WHERE validator_name = ? AND timestamp >= ?
              ORDER BY duration_ms DESC LIMIT ?`
	return scanExecutions(d.db, query, validator, since, limit)
}

// ---------------------------------------------------------------------------
// ErrorCluster
// ---------------------------------------------------------------------------

// detectErrorClusters flags an error_code that appears across at least
// ErrorClusterSess distinct sessions — strong evidence the issue is real
// and not a one-off.
func (d *SQLDetector) detectErrorClusters(since time.Time) ([]DetectedPattern, error) {
	query := `SELECT error_code, COUNT(*) AS n, COUNT(DISTINCT session_id) AS sessions
              FROM executions
              WHERE error_code IS NOT NULL AND error_code != ''`
	var args []any
	if !since.IsZero() {
		query += " AND timestamp >= ?"
		args = append(args, since)
	}
	query += `
        GROUP BY error_code
        HAVING sessions >= ?
        ORDER BY sessions DESC, n DESC`
	args = append(args, d.ErrorClusterSess)

	type cluster struct {
		code     string
		total    int
		sessions int
	}
	rows, err := d.db.Query(query, args...)
	if err != nil {
		return nil, err
	}

	// Same pattern as detectRepeatedFailures: drain the outer rows before
	// nested evidence queries to avoid single-connection deadlock.
	var clusters []cluster
	for rows.Next() {
		var c cluster
		if err := rows.Scan(&c.code, &c.total, &c.sessions); err != nil {
			rows.Close()
			return nil, err
		}
		clusters = append(clusters, c)
	}
	if err := rows.Err(); err != nil {
		rows.Close()
		return nil, err
	}
	rows.Close()

	var patterns []DetectedPattern
	for _, c := range clusters {
		evidence, err := d.evidenceForCode(c.code, since)
		if err != nil {
			return nil, err
		}

		// More distinct sessions => higher confidence. Asymptotes to 1.0.
		extra := float64(c.sessions - d.ErrorClusterSess + 1)
		conf := 0.6 + 0.4*(extra/(extra+1))

		patterns = append(patterns, DetectedPattern{
			Type: PatternErrorCluster,
			Description: fmt.Sprintf(
				"Error %s seen %d times across %d sessions",
				c.code, c.total, c.sessions),
			Confidence: round2(conf),
			Evidence:   evidence,
			Suggestion: fmt.Sprintf(
				"Error %s reproduces across sessions — likely a real defect. "+
					"Check the validator's reference link or open an issue.",
				c.code),
			AutoFixable: false,
		})
	}
	return patterns, nil
}

func (d *SQLDetector) evidenceForCode(errCode string, since time.Time) ([]ExecutionRecord, error) {
	query := `SELECT id, timestamp, session_id, event_type, tool_type,
                     COALESCE(tool_input_hash, ''), validator_name, result, duration_ms,
                     COALESCE(error_code, ''), COALESCE(error_message, ''), COALESCE(context_hash, '')
              FROM executions
              WHERE error_code = ?`
	args := []any{errCode}
	if !since.IsZero() {
		query += " AND timestamp >= ?"
		args = append(args, since)
	}
	query += " ORDER BY timestamp DESC LIMIT ?"
	args = append(args, d.MaxEvidence)
	return scanExecutions(d.db, query, args...)
}

// ---------------------------------------------------------------------------
// helpers
// ---------------------------------------------------------------------------

func scanExecutions(db *sql.DB, query string, args ...any) ([]ExecutionRecord, error) {
	rows, err := db.Query(query, args...)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var out []ExecutionRecord
	for rows.Next() {
		var r ExecutionRecord
		if err := rows.Scan(
			&r.ID, &r.Timestamp, &r.SessionID, &r.EventType, &r.ToolType,
			&r.ToolInputHash, &r.ValidatorName, &r.Result, &r.DurationMs,
			&r.ErrorCode, &r.ErrorMessage, &r.ContextHash,
		); err != nil {
			return nil, err
		}
		out = append(out, r)
	}
	return out, rows.Err()
}

// perfSample holds one (timestamp, duration) point used by the
// PerfRegression detector.
type perfSample struct {
	ts time.Time
	ms int64
}

func meanDuration(samples []perfSample) float64 {
	if len(samples) == 0 {
		return 0
	}
	var sum int64
	for _, s := range samples {
		sum += s.ms
	}
	return float64(sum) / float64(len(samples))
}

func filterByConfidence(in []DetectedPattern, min float64) []DetectedPattern {
	if min <= 0 {
		return in
	}
	out := in[:0]
	for _, p := range in {
		if p.Confidence >= min {
			out = append(out, p)
		}
	}
	return out
}

func round2(f float64) float64 {
	return math.Round(f*100) / 100
}
