// review.go implements the "cos-dispatch review" subcommand (ADR-008).
// It provides a human-facing CLI for listing pending generated artifacts and
// recording feedback decisions (enable / disable / delete / modify).
//
// All flag parsing is scoped to a local flag.FlagSet so review flags never
// collide with the global dispatch flags.
package main

import (
	"database/sql"
	"flag"
	"fmt"
	"os"
	"os/exec"
	"text/tabwriter"
	"time"

	"github.com/luum/cos-dispatch/internal/config"
	"github.com/luum/cos-dispatch/internal/pattern"
	_ "modernc.org/sqlite" // register sqlite driver for sql.Open("sqlite", ...)
)

// runReview is the entry point for "cos-dispatch review [flags]".
// It returns an exit code (0 = success, 1 = error).
func runReview(args []string) int {
	fs := flag.NewFlagSet("cos-dispatch review", flag.ContinueOnError)

	// Action flags
	enableName := fs.String("enable", "", "Set artifact enabled=1 (supply artifact NAME)")
	disableName := fs.String("disable", "", "Set artifact enabled=0, feedback=disabled (supply artifact NAME)")
	deleteName := fs.String("delete", "", "Delete file; keep DB row with feedback=deleted (supply artifact NAME)")
	modifyName := fs.String("modify", "", "Open artifact in $EDITOR; set feedback=modified on save (supply artifact NAME)")

	// List flags
	listFlag := fs.Bool("list", false, "List artifacts (pending by default)")
	allFlag := fs.Bool("all", false, "Include already-reviewed artifacts in --list output")

	// Override flags
	dbPath := fs.String("db", "", "Override DB path (default: cfg.Patterns.DBPath)")
	outputDir := fs.String("output-dir", "", "Override output directory for file ops (default: cfg.AutoGenerate.OutputDir)")

	if err := fs.Parse(args); err != nil {
		// flag.ContinueOnError returns ErrHelp on -h; that is not a real error.
		return 1
	}

	// --- Resolve configuration ---
	projectDir := os.Getenv("CLAUDE_PROJECT_DIR")
	if projectDir == "" {
		projectDir, _ = os.Getwd()
	}
	cfg, err := config.Load(projectDir, "")
	if err != nil {
		cfg = config.DefaultConfig()
	}

	resolvedDB := cfg.Patterns.DBPath
	if *dbPath != "" {
		resolvedDB = *dbPath
	}
	if resolvedDB == "" {
		fmt.Fprintln(os.Stderr, "error: no DB path configured — run cos-dispatch dispatch first to initialize DB")
		return 1
	}

	resolvedOutputDir := cfg.Patterns.AutoGenerate.OutputDir
	if *outputDir != "" {
		resolvedOutputDir = *outputDir
	}
	if resolvedOutputDir == "" {
		resolvedOutputDir = "generated/"
	}

	// --- Open DB ---
	db, err := openReviewDB(resolvedDB)
	if err != nil {
		fmt.Fprintf(os.Stderr, "error: cannot open DB %q: %v\n", resolvedDB, err)
		fmt.Fprintln(os.Stderr, "hint: run cos-dispatch (dispatch mode) at least once to initialize the DB")
		return 1
	}
	defer db.Close()

	// Build generator for ApplyFeedback calls.
	autoCfg := cfg.Patterns.AutoGenerate
	if resolvedOutputDir != "" {
		autoCfg.OutputDir = resolvedOutputDir
	}
	gen, err := pattern.NewSQLGenerator(db, autoCfg)
	if err != nil {
		fmt.Fprintf(os.Stderr, "error: generator init: %v\n", err)
		return 1
	}

	// --- Dispatch action ---
	switch {
	case *enableName != "":
		return reviewApplyFeedback(gen, *enableName, pattern.FeedbackEnabled)

	case *disableName != "":
		return reviewApplyFeedback(gen, *disableName, pattern.FeedbackDisabled)

	case *deleteName != "":
		return reviewApplyFeedback(gen, *deleteName, pattern.FeedbackDeleted)

	case *modifyName != "":
		return reviewModify(db, gen, *modifyName, resolvedOutputDir)

	default:
		// --list is the default action when no action flag is supplied.
		return reviewList(db, *listFlag || true, *allFlag)
	}
}

// reviewApplyFeedback applies a feedback decision and prints a one-line confirmation.
func reviewApplyFeedback(gen *pattern.SQLGenerator, name string, decision pattern.FeedbackDecision) int {
	if err := gen.ApplyFeedback(name, decision); err != nil {
		fmt.Fprintf(os.Stderr, "error: %v\n", err)
		return 1
	}
	fmt.Printf("ok: %s → %s\n", name, string(decision))
	return 0
}

// reviewList prints a table of generated artifacts.  When showAll is false,
// only pending (unreviewed) artifacts are shown.
func reviewList(db *sql.DB, _ bool, showAll bool) int {
	query := `SELECT name, artifact_type, confidence, enabled, COALESCE(feedback,''), generated_at
	          FROM generated_artifacts`
	if !showAll {
		query += ` WHERE (feedback IS NULL OR feedback = '')`
	}
	query += ` ORDER BY generated_at DESC`

	rows, err := db.Query(query)
	if err != nil {
		fmt.Fprintf(os.Stderr, "error: query artifacts: %v\n", err)
		return 1
	}
	defer rows.Close()

	tw := tabwriter.NewWriter(os.Stdout, 2, 8, 2, ' ', 0)
	fmt.Fprintln(tw, "NAME\tTYPE\tCONFIDENCE\tENABLED\tFEEDBACK\tGENERATED_AT")

	count := 0
	for rows.Next() {
		var name, artifactType, feedback, generatedAtStr string
		var confidence float64
		var enabled int
		if scanErr := rows.Scan(&name, &artifactType, &confidence, &enabled, &feedback, &generatedAtStr); scanErr != nil {
			fmt.Fprintf(os.Stderr, "error: scan row: %v\n", scanErr)
			return 1
		}

		// Format generated_at for readability.
		genAt := generatedAtStr
		if t, parseErr := time.Parse(time.RFC3339, generatedAtStr); parseErr == nil {
			genAt = t.Format("2006-01-02 15:04")
		} else if t, parseErr2 := time.Parse("2006-01-02T15:04:05Z", generatedAtStr); parseErr2 == nil {
			genAt = t.Format("2006-01-02 15:04")
		}

		enabledStr := "no"
		if enabled != 0 {
			enabledStr = "yes"
		}
		feedbackStr := feedback
		if feedbackStr == "" {
			feedbackStr = "(pending)"
		}

		fmt.Fprintf(tw, "%s\t%s\t%.2f\t%s\t%s\t%s\n",
			name, artifactType, confidence, enabledStr, feedbackStr, genAt)
		count++
	}
	if err := rows.Err(); err != nil {
		fmt.Fprintf(os.Stderr, "error: row iteration: %v\n", err)
		return 1
	}

	if count == 0 {
		fmt.Fprintln(tw, "(no artifacts)")
	}
	tw.Flush()
	return 0
}

// reviewModify opens the artifact's .go file in $EDITOR and, when the editor
// exits with code 0, records FeedbackModified.
func reviewModify(db *sql.DB, gen *pattern.SQLGenerator, name, outputDir string) int {
	// Look up the code to confirm the artifact exists.
	var code string
	err := db.QueryRow(`SELECT code FROM generated_artifacts WHERE name = ?`, name).Scan(&code)
	if err == sql.ErrNoRows {
		fmt.Fprintf(os.Stderr, "error: artifact %q not found\n", name)
		return 1
	}
	if err != nil {
		fmt.Fprintf(os.Stderr, "error: query artifact: %v\n", err)
		return 1
	}

	// Resolve the file path (same derivation as SQLGenerator.ApplyFeedback).
	fileName := camelToSnakeReview(name) + ".go"
	filePath := outputDir
	if len(filePath) > 0 && filePath[len(filePath)-1] != '/' {
		filePath += "/"
	}
	filePath += fileName

	editor := os.Getenv("EDITOR")
	if editor == "" {
		editor = "vi"
	}

	cmd := exec.Command(editor, filePath)
	cmd.Stdin = os.Stdin
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr
	if runErr := cmd.Run(); runErr != nil {
		fmt.Fprintf(os.Stderr, "editor exited non-zero (%v) — skipping feedback update\n", runErr)
		return 0 // not a cos-dispatch error; the editor may have returned non-zero intentionally
	}

	return reviewApplyFeedback(gen, name, pattern.FeedbackModified)
}

// camelToSnakeReview converts CamelCase (with underscores) to lower_snake_case
// for deriving file names from struct names.  This mirrors the unexported
// camelToSnake in internal/pattern/generator.go; keep in sync if that
// function changes.
func camelToSnakeReview(s string) string {
	var b []byte
	for i := 0; i < len(s); i++ {
		c := s[i]
		if c >= 'A' && c <= 'Z' {
			if i > 0 {
				prev := s[i-1]
				if (prev >= 'a' && prev <= 'z') || prev == '_' {
					b = append(b, '_')
				}
			}
			b = append(b, c+32) // toLower
		} else {
			b = append(b, c)
		}
	}
	return string(b)
}

// openReviewDB opens an existing SQLite DB read-write.  It does NOT apply the
// schema — the DB must already exist (created by the dispatch path).
func openReviewDB(dbPath string) (*sql.DB, error) {
	db, err := sql.Open("sqlite", dbPath)
	if err != nil {
		return nil, err
	}
	// Quick connectivity check.
	if pingErr := db.Ping(); pingErr != nil {
		_ = db.Close()
		return nil, pingErr
	}
	return db, nil
}
