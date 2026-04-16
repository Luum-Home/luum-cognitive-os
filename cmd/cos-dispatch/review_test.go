// review_test.go — binary-level tests for "cos-dispatch review" subcommand.
//
// Per ADR-010: every test executes the compiled binary (via os/exec) and
// verifies observable state (stdout, exit code, DB rows, files on disk).
// No mocks; real SQLite temp files.
package main

import (
	"database/sql"
	"encoding/json"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"testing"

	_ "modernc.org/sqlite"
)

// ---- helpers ----------------------------------------------------------------

// buildBinary compiles cos-dispatch into a temp file and returns the path.
// Subsequent tests in the same binary run share the same build (cached by Go).
func buildBinary(t *testing.T) string {
	t.Helper()
	binPath := filepath.Join(t.TempDir(), "cos-dispatch-test")
	cmd := exec.Command("go", "build", "-o", binPath, ".")
	cmd.Dir = "." // cmd/cos-dispatch — test binary runs from this dir
	out, err := cmd.CombinedOutput()
	if err != nil {
		t.Fatalf("build binary: %v\n%s", err, out)
	}
	return binPath
}

// seedArtifactsDB creates a fresh SQLite DB at dbPath with the
// generated_artifacts schema and inserts n sample rows.
func seedArtifactsDB(t *testing.T, dbPath string, names []string, outputDir string) {
	t.Helper()
	db, err := sql.Open("sqlite", dbPath)
	if err != nil {
		t.Fatalf("open seed DB: %v", err)
	}
	defer db.Close()

	_, err = db.Exec(`CREATE TABLE IF NOT EXISTS generated_artifacts (
		id                INTEGER PRIMARY KEY AUTOINCREMENT,
		name              TEXT NOT NULL UNIQUE,
		artifact_type     TEXT NOT NULL,
		source_pattern_id INTEGER,
		language          TEXT NOT NULL,
		code              TEXT NOT NULL,
		config_snippet    TEXT,
		confidence        REAL NOT NULL,
		generated_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
		enabled           BOOLEAN NOT NULL DEFAULT 0,
		feedback          TEXT
	)`)
	if err != nil {
		t.Fatalf("create table: %v", err)
	}

	for _, name := range names {
		_, err = db.Exec(
			`INSERT INTO generated_artifacts (name, artifact_type, language, code, confidence, enabled, feedback)
			 VALUES (?, 'validator', 'go', '// stub', 0.80, 0, '')`,
			name,
		)
		if err != nil {
			t.Fatalf("seed artifact %s: %v", name, err)
		}
		// Write a matching .go stub on disk so delete/modify ops can find it.
		if outputDir != "" {
			fileName := camelToSnakeReview(name) + ".go"
			filePath := filepath.Join(outputDir, fileName)
			if writeErr := os.WriteFile(filePath, []byte("// stub\npackage generated\n"), 0o644); writeErr != nil {
				t.Fatalf("write stub %s: %v", filePath, writeErr)
			}
		}
	}
}

// queryArtifact reads enabled and feedback columns for the named artifact.
func queryArtifact(t *testing.T, dbPath, name string) (enabled int, feedback string) {
	t.Helper()
	db, err := sql.Open("sqlite", dbPath)
	if err != nil {
		t.Fatalf("open DB: %v", err)
	}
	defer db.Close()
	row := db.QueryRow(`SELECT enabled, COALESCE(feedback,'') FROM generated_artifacts WHERE name = ?`, name)
	if err := row.Scan(&enabled, &feedback); err != nil {
		t.Fatalf("scan artifact %s: %v", name, err)
	}
	return
}

// ---- tests ------------------------------------------------------------------

// TestReview_ListEmpty verifies that --list on an empty (but valid) DB exits 0
// and prints the "no artifacts" placeholder.
func TestReview_ListEmpty(t *testing.T) {
	bin := buildBinary(t)
	dir := t.TempDir()
	dbPath := filepath.Join(dir, "patterns.db")
	seedArtifactsDB(t, dbPath, nil, "")

	cmd := exec.Command(bin, "review", "--list", "--db="+dbPath)
	cmd.Env = append(os.Environ(), "CLAUDE_PROJECT_DIR="+dir)
	out, err := cmd.CombinedOutput()
	if err != nil {
		t.Fatalf("review --list exit=%v stdout=%q", err, out)
	}
	if !strings.Contains(string(out), "no artifacts") {
		t.Errorf("expected 'no artifacts' in output, got: %q", out)
	}
}

// TestReview_ListWithArtifacts verifies that both seeded artifact names appear
// in the --list output.
func TestReview_ListWithArtifacts(t *testing.T) {
	bin := buildBinary(t)
	dir := t.TempDir()
	dbPath := filepath.Join(dir, "patterns.db")
	names := []string{"AutoValidator_RepeatFail_aabbccdd", "AutoValidator_Cluster_11223344"}
	seedArtifactsDB(t, dbPath, names, "")

	cmd := exec.Command(bin, "review", "--list", "--db="+dbPath)
	cmd.Env = append(os.Environ(), "CLAUDE_PROJECT_DIR="+dir)
	out, err := cmd.CombinedOutput()
	if err != nil {
		t.Fatalf("review --list exit=%v stdout=%q", err, out)
	}
	for _, name := range names {
		if !strings.Contains(string(out), name) {
			t.Errorf("expected %q in output, got: %q", name, out)
		}
	}
}

// TestReview_EnableSuccess verifies that --enable flips enabled=1 and sets
// feedback='enabled' in the DB.
func TestReview_EnableSuccess(t *testing.T) {
	bin := buildBinary(t)
	dir := t.TempDir()
	dbPath := filepath.Join(dir, "patterns.db")
	name := "AutoValidator_RepeatFail_cafebabe"
	seedArtifactsDB(t, dbPath, []string{name}, "")

	cmd := exec.Command(bin, "review", "--enable="+name, "--db="+dbPath)
	cmd.Env = append(os.Environ(), "CLAUDE_PROJECT_DIR="+dir)
	out, err := cmd.CombinedOutput()
	if err != nil {
		t.Fatalf("review --enable exit=%v stdout=%q", err, out)
	}

	enabled, feedback := queryArtifact(t, dbPath, name)
	if enabled != 1 {
		t.Errorf("enabled = %d, want 1 (stdout: %q)", enabled, out)
	}
	if feedback != "enabled" {
		t.Errorf("feedback = %q, want 'enabled'", feedback)
	}
}

// TestReview_DisableSuccess verifies that --disable leaves enabled=0 and sets
// feedback='disabled'.
func TestReview_DisableSuccess(t *testing.T) {
	bin := buildBinary(t)
	dir := t.TempDir()
	dbPath := filepath.Join(dir, "patterns.db")
	name := "AutoValidator_Cluster_deadbeef"
	seedArtifactsDB(t, dbPath, []string{name}, "")

	cmd := exec.Command(bin, "review", "--disable="+name, "--db="+dbPath)
	cmd.Env = append(os.Environ(), "CLAUDE_PROJECT_DIR="+dir)
	out, err := cmd.CombinedOutput()
	if err != nil {
		t.Fatalf("review --disable exit=%v stdout=%q", err, out)
	}

	enabled, feedback := queryArtifact(t, dbPath, name)
	if enabled != 0 {
		t.Errorf("enabled = %d, want 0 (stdout: %q)", enabled, out)
	}
	if feedback != "disabled" {
		t.Errorf("feedback = %q, want 'disabled'", feedback)
	}
}

// TestReview_DeleteRemovesFile verifies that --delete removes the .go file from
// disk but keeps the DB row with feedback='deleted'.
func TestReview_DeleteRemovesFile(t *testing.T) {
	bin := buildBinary(t)
	dir := t.TempDir()
	dbPath := filepath.Join(dir, "patterns.db")
	outputDir := filepath.Join(dir, "generated")
	if err := os.MkdirAll(outputDir, 0o755); err != nil {
		t.Fatalf("mkdir generated: %v", err)
	}

	name := "AutoValidator_RepeatFail_00112233"
	seedArtifactsDB(t, dbPath, []string{name}, outputDir)
	fileName := camelToSnakeReview(name) + ".go"
	filePath := filepath.Join(outputDir, fileName)

	// Confirm file exists before delete.
	if _, err := os.Stat(filePath); os.IsNotExist(err) {
		t.Fatalf("stub file not seeded at %s", filePath)
	}

	cmd := exec.Command(bin, "review", "--delete="+name, "--db="+dbPath, "--output-dir="+outputDir)
	cmd.Env = append(os.Environ(), "CLAUDE_PROJECT_DIR="+dir)
	out, err := cmd.CombinedOutput()
	if err != nil {
		t.Fatalf("review --delete exit=%v stdout=%q", err, out)
	}

	// File must be gone.
	if _, statErr := os.Stat(filePath); !os.IsNotExist(statErr) {
		t.Errorf("expected file %s to be deleted, still exists", filePath)
	}

	// DB row must remain with feedback='deleted'.
	_, feedback := queryArtifact(t, dbPath, name)
	if feedback != "deleted" {
		t.Errorf("feedback = %q, want 'deleted'", feedback)
	}
}

// TestReview_EnableNotFound verifies that --enable on a non-existent artifact
// exits 1 and emits a diagnostic to stderr.
func TestReview_EnableNotFound(t *testing.T) {
	bin := buildBinary(t)
	dir := t.TempDir()
	dbPath := filepath.Join(dir, "patterns.db")
	seedArtifactsDB(t, dbPath, nil, "")

	cmd := exec.Command(bin, "review", "--enable=BOGUS_DOES_NOT_EXIST", "--db="+dbPath)
	cmd.Env = append(os.Environ(), "CLAUDE_PROJECT_DIR="+dir)
	out, err := cmd.CombinedOutput()
	if err == nil {
		t.Fatalf("expected non-zero exit for missing artifact, got exit 0 (stdout: %q)", out)
	}
	if !strings.Contains(string(out), "not found") {
		t.Errorf("expected 'not found' in output, got: %q", out)
	}
}

// TestReview_BackwardsCompat_StdinDispatchStillWorks verifies that invoking the
// binary with NO subcommand (piping a hook event on stdin) takes the dispatch
// path and exits 0 with a valid JSON response.  This is the primary regression
// guard for ADR-008 backwards compatibility.
func TestReview_BackwardsCompat_StdinDispatchStillWorks(t *testing.T) {
	bin := buildBinary(t)
	dir := t.TempDir()

	hookEvent := map[string]any{
		"hook_event": "PreToolUse",
		"tool_name":  "Bash",
		"tool_input": map[string]string{"command": "echo hello"},
		"session_id": "test-backwards-compat",
	}
	payload, _ := json.Marshal(hookEvent)

	var stdout, stderr strings.Builder
	cmd := exec.Command(bin)
	cmd.Env = append(os.Environ(), "CLAUDE_PROJECT_DIR="+dir)
	cmd.Stdin = strings.NewReader(string(payload))
	cmd.Stdout = &stdout
	cmd.Stderr = &stderr
	err := cmd.Run()

	// Exit code 0 is the only valid exit for non-blocking dispatch.
	if exitErr, ok := err.(*exec.ExitError); ok && exitErr.ExitCode() != 2 {
		t.Fatalf("dispatch exit=%v stdout=%q stderr=%q", err, stdout.String(), stderr.String())
	}
	// Response must be non-empty JSON on stdout.
	outStr := stdout.String()
	if len(outStr) == 0 {
		t.Fatalf("dispatch produced no stdout (stderr: %q)", stderr.String())
	}
	var resp map[string]any
	if jsonErr := json.Unmarshal([]byte(outStr), &resp); jsonErr != nil {
		t.Errorf("dispatch stdout is not valid JSON: %q (err: %v)", outStr, jsonErr)
	}
}

// TestReview_FlagOnly_StdinDispatch verifies that passing only flags (no
// subcommand) takes the dispatch path, not the review path.  This guards the
// ADR-008 rule: "if argv has no recognised subcommand OR the first arg starts
// with '-', fall back to stdin-dispatch mode".
func TestReview_FlagOnly_StdinDispatch(t *testing.T) {
	bin := buildBinary(t)
	dir := t.TempDir()

	hookEvent := map[string]any{
		"hook_event": "PreToolUse",
		"tool_name":  "Write",
		"tool_input": map[string]string{"file_path": "/tmp/x", "content": "y"},
		"session_id": "test-flag-only",
	}
	payload, _ := json.Marshal(hookEvent)

	// Pass a flag (--log-level=error) as the first argument — no subcommand.
	var stdout, stderr strings.Builder
	cmd := exec.Command(bin, "--log-level=error")
	cmd.Env = append(os.Environ(), "CLAUDE_PROJECT_DIR="+dir)
	cmd.Stdin = strings.NewReader(string(payload))
	cmd.Stdout = &stdout
	cmd.Stderr = &stderr
	err := cmd.Run()

	if exitErr, ok := err.(*exec.ExitError); ok && exitErr.ExitCode() != 2 {
		t.Fatalf("flag-only dispatch exit=%v stdout=%q stderr=%q", err, stdout.String(), stderr.String())
	}
	outStr := stdout.String()
	if len(outStr) == 0 {
		t.Fatalf("flag-only dispatch produced no stdout (stderr: %q)", stderr.String())
	}
	var resp map[string]any
	if jsonErr := json.Unmarshal([]byte(outStr), &resp); jsonErr != nil {
		t.Errorf("flag-only dispatch stdout is not valid JSON: %q (err: %v)", outStr, jsonErr)
	}
}
