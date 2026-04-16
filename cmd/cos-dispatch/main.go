// Command cos-dispatch is the vendor-agnostic hook dispatcher for Cognitive OS.
// It reads JSON from stdin, dispatches validators, and writes JSON to stdout.
// Exit code is always 0 (fail-open); exit code 2 is used to block tool execution.
package main

import (
	"context"
	"flag"
	"fmt"
	"io"
	"log"
	"os"
	"runtime"
	"strings"
	"time"

	"github.com/luum/cos-dispatch/internal/config"
	"github.com/luum/cos-dispatch/internal/dispatcher"
	"github.com/luum/cos-dispatch/internal/executor"
	"github.com/luum/cos-dispatch/internal/pattern"
	"github.com/luum/cos-dispatch/internal/provider"
	"github.com/luum/cos-dispatch/internal/transformer"
	"github.com/luum/cos-dispatch/internal/validator"
	"github.com/luum/cos-dispatch/internal/validator/impl"
	"github.com/luum/cos-dispatch/pkg/hook"
)

var version = "dev"

func main() {
	os.Exit(run())
}

// run is the real entry point. It returns an exit code so deferred cleanup
// (tracker.Close) runs before os.Exit is called. Using os.Exit directly in
// main would skip defers and leave the tracker buffer unflushed.
func run() int {
	// Parse flags
	providerFlag := flag.String("provider", "", "Override provider detection (claude|codex|gemini|cursor|windsurf)")
	configFlag := flag.String("config", "", "Path to config file")
	logLevelFlag := flag.String("log-level", "", "Log level (debug|info|warn|error)")
	disableFlag := flag.String("disable", "", "Comma-separated validator names to disable")
	dryRun := flag.Bool("dry-run", false, "Log decisions without blocking")
	versionFlag := flag.Bool("version", false, "Print version and exit")
	flag.Parse()

	if *versionFlag {
		fmt.Fprintf(os.Stdout, "cos-dispatch %s\n", version)
		return 0
	}

	// Read stdin
	raw, err := io.ReadAll(os.Stdin)
	if err != nil {
		log.Printf("[cos-dispatch] error reading stdin: %v", err)
		return 0
	}
	if len(raw) == 0 {
		log.Printf("[cos-dispatch] empty stdin, nothing to do")
		return 0
	}

	// Determine project dir
	projectDir := os.Getenv("CLAUDE_PROJECT_DIR")
	if projectDir == "" {
		projectDir, _ = os.Getwd()
	}

	// Load config
	cfg, err := config.Load(projectDir, *configFlag)
	if err != nil {
		log.Printf("[cos-dispatch] config error (using defaults): %v", err)
		cfg = config.DefaultConfig()
	}

	// Apply flag overrides
	if *logLevelFlag != "" {
		cfg.Dispatch.LogLevel = *logLevelFlag
	}

	// Set up logger
	logger := log.New(os.Stderr, "", log.LstdFlags)
	if cfg.Dispatch.LogLevel == "error" || cfg.Dispatch.LogLevel == "warn" {
		logger = log.New(io.Discard, "", 0)
	}

	// Build components
	providerReg := provider.NewRegistry()
	validatorReg := validator.NewRegistry()
	// Register built-in Phase-3 validators (rate limiter, secret detector, etc.)
	// Phase left empty so the factory falls back to its "stabilization" default.
	impl.RegisterDefaults(validatorReg, impl.FactoryConfig{
		ProjectDir: projectDir,
	})
	pipeline := transformer.NewPipeline()

	// Choose executor
	timeout := time.Duration(cfg.Dispatch.TimeoutMs) * time.Millisecond
	var exec executor.Executor
	if cfg.Dispatch.Parallel {
		pools := cfg.ResolvedPools()
		exec = executor.NewParallelExecutor(pools.CPUWorkers, pools.IOWorkers, pools.GitWorkers, timeout)
	} else {
		exec = executor.NewSequentialExecutor(timeout)
	}

	// Build dispatcher options
	var opts []dispatcher.Option
	if *providerFlag != "" {
		opts = append(opts, dispatcher.WithProviderOverride(hook.Provider(*providerFlag)))
	}
	opts = append(opts, dispatcher.WithLogger(logger))

	// Optionally wire pattern tracker (non-fatal: dispatcher works without it).
	// Defer tracker.Close() here so it runs before run() returns and os.Exit
	// is called — defers in run() execute normally unlike defers in main()
	// when os.Exit is called directly.
	if cfg.Patterns.Enabled && cfg.Patterns.DBPath != "" {
		tracker, trackerErr := pattern.NewTracker(cfg.Patterns.DBPath)
		if trackerErr != nil {
			log.Printf("[cos-dispatch] pattern tracker unavailable (continuing without): %v", trackerErr)
		} else {
			defer func() {
				if closeErr := tracker.Close(); closeErr != nil {
					log.Printf("[cos-dispatch] tracker close: %v", closeErr)
				}
			}()
			opts = append(opts, dispatcher.WithTracker(tracker))
		}
	}

	// Handle --disable
	_ = *disableFlag // reserved for future validator filtering
	_ = *dryRun      // reserved for future dry-run support
	_ = runtime.NumCPU()

	// Create and run dispatcher
	d := dispatcher.New(providerReg, validatorReg, pipeline, exec, cfg, opts...)

	ctx := context.Background()
	resp, err := d.Dispatch(ctx, raw)
	if err != nil {
		log.Printf("[cos-dispatch] dispatch error: %v", err)
		// Fail-open: write empty allow response
		fmt.Fprint(os.Stdout, `{"hookSpecificOutput":{"permissionDecision":"allow","reason":"internal error","additionalContext":""}}`)
		return 0
	}

	os.Stdout.Write(resp)

	// Check if any blocking errors occurred — exit 2 to signal block
	if containsDeny(resp) {
		return 2
	}
	return 0
}

// containsDeny checks if the response JSON contains a deny decision.
func containsDeny(resp []byte) bool {
	return strings.Contains(string(resp), `"permissionDecision":"deny"`)
}
