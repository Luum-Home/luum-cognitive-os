package pattern

import (
	"database/sql"
	"fmt"
	"os"
	"path/filepath"
	"runtime"
	"testing"

	"github.com/luum/cos-dispatch/internal/config"
	_ "modernc.org/sqlite"
)

// moduleRoot returns the project's module root directory (the one containing
// go.mod) so tests can create outputDirs inside the module for `go vet` to
// resolve imports correctly.
func moduleRoot() string {
	// runtime.Caller(0) gives the path of this source file.
	// From internal/pattern/generator_test.go go up two levels.
	_, file, _, _ := runtime.Caller(0)
	return filepath.Join(filepath.Dir(file), "..", "..")
}

// openTestDB opens a real SQLite database at dir/patterns.db, applies the
// schema, and returns a *sql.DB ready for component-level tests (ADR-010).
func openTestDB(t *testing.T) *sql.DB {
	t.Helper()
	path := filepath.Join(t.TempDir(), "patterns.db")
	db, err := sql.Open("sqlite", path)
	if err != nil {
		t.Fatalf("open db: %v", err)
	}
	if _, err := db.Exec(schemaSQL); err != nil {
		t.Fatalf("apply schema: %v", err)
	}
	t.Cleanup(func() { db.Close() })
	return db
}

// generatedTestDir creates a temporary output directory INSIDE the module tree
// (under generated/) so that `go vet` from the module root can resolve imports.
// The directory is removed on test cleanup.
func generatedTestDir(t *testing.T) string {
	t.Helper()
	root := moduleRoot()
	parent := filepath.Join(root, "generated")
	if err := os.MkdirAll(parent, 0o755); err != nil {
		t.Fatalf("create generated parent dir: %v", err)
	}
	dir, err := os.MkdirTemp(parent, "test-*")
	if err != nil {
		t.Fatalf("create test output dir: %v", err)
	}
	t.Cleanup(func() { os.RemoveAll(dir) })
	return dir
}

// defaultTestCfg returns an AutoGenerateConfig suitable for most tests.
// outputDir is inside the module tree so compile checks work.
func defaultTestCfg(t *testing.T) config.AutoGenerateConfig {
	t.Helper()
	return config.AutoGenerateConfig{
		Enabled:             true,
		OutputDir:           generatedTestDir(t),
		ConfidenceThreshold: 0.7,
		RequireReview:       true,
		MaxPerSession:       10,
	}
}

// newTestGenerator creates a SQLGenerator with moduleDir set to the project root.
func newTestGenerator(t *testing.T, db *sql.DB, cfg config.AutoGenerateConfig) *SQLGenerator {
	t.Helper()
	gen, err := NewSQLGeneratorWithModuleDir(db, cfg, moduleRoot())
	if err != nil {
		t.Fatalf("NewSQLGeneratorWithModuleDir: %v", err)
	}
	return gen
}

// syntheticPattern creates a minimal DetectedPattern for the given type.
func syntheticPattern(pt PatternType, confidence float64) DetectedPattern {
	return DetectedPattern{
		Type:        pt,
		Description: "test pattern",
		Confidence:  confidence,
		Suggestion:  "implement remediation logic",
		AutoFixable: true,
	}
}

// ---- Tests ---------------------------------------------------------------

// TestGenerate_ProducesCompilableGo feeds a single RepeatFail pattern with
// confidence=0.9 and asserts: one .go file is written AND `go build` on the
// outputDir exits 0 (ADR-010: generated Go must compile, not just string-diff).
func TestGenerate_ProducesCompilableGo(t *testing.T) {
	db := openTestDB(t)
	cfg := defaultTestCfg(t)

	gen := newTestGenerator(t, db, cfg)

	patterns := []DetectedPattern{syntheticPattern(PatternRepeatedFailure, 0.9)}
	artifacts, err := gen.Generate(patterns)
	if err != nil {
		t.Fatalf("Generate: %v", err)
	}
	if len(artifacts) != 1 {
		t.Fatalf("expected 1 artifact, got %d", len(artifacts))
	}

	// Verify .go file exists on disk.
	entries, err := os.ReadDir(cfg.OutputDir)
	if err != nil {
		t.Fatalf("readdir outputDir: %v", err)
	}
	goFiles := 0
	for _, e := range entries {
		if filepath.Ext(e.Name()) == ".go" {
			goFiles++
		}
	}
	if goFiles != 1 {
		t.Errorf("expected 1 .go file, found %d", goFiles)
	}

	// `go vet` from module root must succeed — the core ADR-010 requirement.
	// The artifact was already compile-verified inside Generate(); this is the
	// test-layer independent check confirming the on-disk file is correct.
	_, fname := artifactNameFromStructName(artifacts[0].Name)
	if err := verifyCompiles(moduleRoot(), filepath.Join(cfg.OutputDir, fname)); err != nil {
		t.Errorf("generated code does not compile: %v", err)
	}
}

// TestGenerate_RespectsConfidenceThreshold ensures patterns below threshold
// are skipped.  Three patterns at 0.9 / 0.5 / 0.6 with threshold=0.7 → only
// one artifact.
func TestGenerate_RespectsConfidenceThreshold(t *testing.T) {
	db := openTestDB(t)
	cfg := defaultTestCfg(t)
	cfg.ConfidenceThreshold = 0.7

	gen := newTestGenerator(t, db, cfg)

	patterns := []DetectedPattern{
		syntheticPattern(PatternRepeatedFailure, 0.9),
		syntheticPattern(PatternErrorCluster, 0.5),
		syntheticPattern(PatternMissingCoverage, 0.6),
	}
	artifacts, err := gen.Generate(patterns)
	if err != nil {
		t.Fatalf("Generate: %v", err)
	}
	if len(artifacts) != 1 {
		t.Errorf("expected 1 artifact (only 0.9 >= 0.7), got %d", len(artifacts))
	}
}

// TestGenerate_RespectsMaxPerSession asserts that MaxPerSession caps output
// even when more patterns qualify.  Each pattern has a unique suggestion so
// that artifact names are distinct (the hash includes suggestion text).
func TestGenerate_RespectsMaxPerSession(t *testing.T) {
	db := openTestDB(t)
	cfg := defaultTestCfg(t)
	cfg.MaxPerSession = 2
	cfg.ConfidenceThreshold = 0.5

	gen := newTestGenerator(t, db, cfg)

	patternTypes := []PatternType{
		PatternRepeatedFailure,
		PatternErrorCluster,
		PatternMissingCoverage,
		PatternRepeatedFailure,
		PatternErrorCluster,
	}
	var patterns []DetectedPattern
	for i, pt := range patternTypes {
		p := syntheticPattern(pt, 0.9)
		p.Suggestion = fmt.Sprintf("suggestion-%d", i)
		patterns = append(patterns, p)
	}

	artifacts, err := gen.Generate(patterns)
	if err != nil {
		t.Fatalf("Generate: %v", err)
	}
	if len(artifacts) != 2 {
		t.Errorf("expected 2 artifacts (MaxPerSession=2), got %d", len(artifacts))
	}
}

// TestGenerate_SkipsUnsupportedPatternTypes verifies that unsupported patterns
// (FalsePositive, SlowValidator, SequenceCorrelation) produce no file and no
// DB row.
func TestGenerate_SkipsUnsupportedPatternTypes(t *testing.T) {
	db := openTestDB(t)
	cfg := defaultTestCfg(t)
	cfg.ConfidenceThreshold = 0.0 // accept anything

	gen := newTestGenerator(t, db, cfg)

	unsupported := []DetectedPattern{
		syntheticPattern(PatternFalsePositive, 0.95),
		syntheticPattern(PatternPerfRegression, 0.95),
		syntheticPattern(PatternSequenceCorrelation, 0.95),
	}
	artifacts, err := gen.Generate(unsupported)
	if err != nil {
		t.Fatalf("Generate: %v", err)
	}
	if len(artifacts) != 0 {
		t.Errorf("expected 0 artifacts for unsupported types, got %d", len(artifacts))
	}

	// Verify no files written.
	entries, _ := os.ReadDir(cfg.OutputDir)
	for _, e := range entries {
		if filepath.Ext(e.Name()) == ".go" {
			t.Errorf("unexpected .go file: %s", e.Name())
		}
	}

	// Verify no DB rows.
	var count int
	if err := db.QueryRow("SELECT COUNT(*) FROM generated_artifacts").Scan(&count); err != nil {
		t.Fatalf("count query: %v", err)
	}
	if count != 0 {
		t.Errorf("expected 0 DB rows, got %d", count)
	}
}

// TestGenerate_InsertsDisabledArtifact confirms enabled=0 and feedback=” in
// the DB row after generation (ADR-004 mandate).
func TestGenerate_InsertsDisabledArtifact(t *testing.T) {
	db := openTestDB(t)
	cfg := defaultTestCfg(t)

	gen := newTestGenerator(t, db, cfg)
	artifacts, err := gen.Generate([]DetectedPattern{syntheticPattern(PatternRepeatedFailure, 0.9)})
	if err != nil || len(artifacts) != 1 {
		t.Fatalf("Generate returned unexpected result: err=%v len=%d", err, len(artifacts))
	}

	name := artifacts[0].Name
	var enabled int
	var feedback string
	err = db.QueryRow(
		"SELECT enabled, COALESCE(feedback,'') FROM generated_artifacts WHERE name = ?",
		name,
	).Scan(&enabled, &feedback)
	if err != nil {
		t.Fatalf("query artifact: %v", err)
	}
	if enabled != 0 {
		t.Errorf("expected enabled=0, got %d", enabled)
	}
	if feedback != "" {
		t.Errorf("expected empty feedback, got %q", feedback)
	}
}

// TestApplyFeedback_Enable generates one artifact, enables it, and verifies
// DB shows enabled=1 and feedback='enabled'.
func TestApplyFeedback_Enable(t *testing.T) {
	db := openTestDB(t)
	cfg := defaultTestCfg(t)
	gen := newTestGenerator(t, db, cfg)

	artifacts, err := gen.Generate([]DetectedPattern{syntheticPattern(PatternRepeatedFailure, 0.9)})
	if err != nil || len(artifacts) == 0 {
		t.Fatalf("Generate: err=%v len=%d", err, len(artifacts))
	}

	name := artifacts[0].Name
	if err := gen.ApplyFeedback(name, FeedbackEnabled); err != nil {
		t.Fatalf("ApplyFeedback: %v", err)
	}

	var enabled int
	var feedback string
	if err := db.QueryRow(
		"SELECT enabled, feedback FROM generated_artifacts WHERE name = ?", name,
	).Scan(&enabled, &feedback); err != nil {
		t.Fatalf("query: %v", err)
	}
	if enabled != 1 {
		t.Errorf("expected enabled=1, got %d", enabled)
	}
	if feedback != "enabled" {
		t.Errorf("expected feedback='enabled', got %q", feedback)
	}
}

// TestApplyFeedback_Delete generates one artifact, deletes it, and verifies:
// (a) the .go file is removed, (b) the DB row is kept with feedback='deleted'
// (audit record per ADR-004).
func TestApplyFeedback_Delete(t *testing.T) {
	db := openTestDB(t)
	cfg := defaultTestCfg(t)
	gen := newTestGenerator(t, db, cfg)

	artifacts, err := gen.Generate([]DetectedPattern{syntheticPattern(PatternRepeatedFailure, 0.9)})
	if err != nil || len(artifacts) == 0 {
		t.Fatalf("Generate: %v / %d", err, len(artifacts))
	}

	name := artifacts[0].Name
	_, fileName := artifactNameFromStructName(name)
	filePath := filepath.Join(cfg.OutputDir, fileName)

	// File must exist before delete.
	if _, err := os.Stat(filePath); err != nil {
		t.Fatalf("expected file to exist before delete: %v", err)
	}

	if err := gen.ApplyFeedback(name, FeedbackDeleted); err != nil {
		t.Fatalf("ApplyFeedback(delete): %v", err)
	}

	// File must be gone.
	if _, err := os.Stat(filePath); !os.IsNotExist(err) {
		t.Errorf("expected file to be removed, stat err=%v", err)
	}

	// DB row must still exist (audit record).
	var feedback string
	if err := db.QueryRow(
		"SELECT feedback FROM generated_artifacts WHERE name = ?", name,
	).Scan(&feedback); err != nil {
		t.Fatalf("DB row missing after delete: %v", err)
	}
	if feedback != "deleted" {
		t.Errorf("expected feedback='deleted', got %q", feedback)
	}
}

// TestApplyFeedback_NotFound verifies that an error is returned for a bogus
// artifact name and the DB remains unchanged.
func TestApplyFeedback_NotFound(t *testing.T) {
	db := openTestDB(t)
	cfg := defaultTestCfg(t)
	gen := newTestGenerator(t, db, cfg)

	err := gen.ApplyFeedback("NonExistent_Artifact_000000ff", FeedbackEnabled)
	if err == nil {
		t.Error("expected error for unknown artifact, got nil")
	}
}

// TestGenerate_CompileFailureRollback injects a malformed pattern suggestion
// that produces an unparseable template (by temporarily replacing the template)
// and verifies: no .go file on disk AND no DB row inserted.
//
// We simulate compile failure by writing a file with a deliberate syntax error
// before calling Generate, so the `go build ./...` check rejects the output.
func TestGenerate_CompileFailureRollback(t *testing.T) {
	db := openTestDB(t)
	cfg := defaultTestCfg(t)

	gen := newTestGenerator(t, db, cfg)

	// Pre-seed the outputDir with a file that already breaks compilation.
	// This causes verifyCompiles to fail for ANY file written there.
	badFile := filepath.Join(cfg.OutputDir, "bad_seed.go")
	if err := os.WriteFile(badFile, []byte("package generated\nthis is not valid go syntax\n"), 0o644); err != nil {
		t.Fatalf("write bad seed file: %v", err)
	}

	artifacts, err := gen.Generate([]DetectedPattern{syntheticPattern(PatternRepeatedFailure, 0.9)})
	if err != nil {
		t.Fatalf("Generate should not propagate compilation errors: %v", err)
	}
	if len(artifacts) != 0 {
		t.Errorf("expected 0 artifacts when compilation fails, got %d", len(artifacts))
	}

	// The bad seed exists but no NEW generated file should be present.
	entries, _ := os.ReadDir(cfg.OutputDir)
	count := 0
	for _, e := range entries {
		if filepath.Ext(e.Name()) == ".go" && e.Name() != "bad_seed.go" {
			count++
		}
	}
	if count != 0 {
		t.Errorf("expected 0 generated .go files after rollback, found %d", count)
	}

	// No DB row should have been inserted.
	var rowCount int
	if err := db.QueryRow("SELECT COUNT(*) FROM generated_artifacts").Scan(&rowCount); err != nil {
		t.Fatalf("count: %v", err)
	}
	if rowCount != 0 {
		t.Errorf("expected 0 DB rows after rollback, got %d", rowCount)
	}
}
