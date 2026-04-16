// Package main — dispatch.go contains the stdin-dispatch logic extracted from
// main.go so it can be called from the subcommand router without nesting.
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

// dispatchFlags holds the parsed values of the global flags that belong to the
// stdin-dispatch path.  They are separated here so runDispatch can be called
// with an already-parsed *flag.FlagSet from the tests as well as from main.
type dispatchFlags struct {
	provider string
	config   string
	logLevel string
	disable  string
	dryRun   bool
	version  bool
}

// registerDispatchFlags adds dispatch-path flags to fs and returns a pointer to
// the values struct so the caller can read them after fs.Parse.
func registerDispatchFlags(fs *flag.FlagSet) *dispatchFlags {
	f := &dispatchFlags{}
	fs.StringVar(&f.provider, "provider", "", "Override provider detection (claude|codex|gemini|cursor|windsurf)")
	fs.StringVar(&f.config, "config", "", "Path to config file")
	fs.StringVar(&f.logLevel, "log-level", "", "Log level (debug|info|warn|error)")
	fs.StringVar(&f.disable, "disable", "", "Comma-separated validator names to disable")
	fs.BoolVar(&f.dryRun, "dry-run", false, "Log decisions without blocking")
	fs.BoolVar(&f.version, "version", false, "Print version and exit")
	return f
}

// runDispatch is the stdin-dispatch entry point.  It reads a JSON hook event
// from stdin, dispatches it through the full validator pipeline, and writes the
// provider-specific JSON response to stdout.  It returns an exit code (0 or 2).
// All flag parsing uses the supplied FlagSet so callers can inject their own
// parsed values (e.g. in integration tests).
func runDispatch(fs *flag.FlagSet, f *dispatchFlags) int {
	if f.version {
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
	cfg, err := config.Load(projectDir, f.config)
	if err != nil {
		log.Printf("[cos-dispatch] config error (using defaults): %v", err)
		cfg = config.DefaultConfig()
	}

	// Apply flag overrides
	if f.logLevel != "" {
		cfg.Dispatch.LogLevel = f.logLevel
	}

	// Set up logger
	logger := log.New(os.Stderr, "", log.LstdFlags)
	if cfg.Dispatch.LogLevel == "error" || cfg.Dispatch.LogLevel == "warn" {
		logger = log.New(io.Discard, "", 0)
	}

	// Build components
	providerReg := provider.NewRegistry()
	validatorReg := validator.NewRegistry()
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
	if f.provider != "" {
		opts = append(opts, dispatcher.WithProviderOverride(hook.Provider(f.provider)))
	}
	opts = append(opts, dispatcher.WithLogger(logger))

	// Optionally wire pattern tracker (non-fatal: dispatcher works without it).
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

			// Wire generator if auto-generate is enabled (Phase 5.3).
			if cfg.Patterns.AutoGenerate.Enabled {
				if gen, genErr := newGeneratorForDispatch(tracker, cfg, projectDir); genErr != nil {
					log.Printf("[cos-dispatch] generator unavailable (continuing without): %v", genErr)
				} else {
					opts = append(opts, dispatcher.WithGenerator(gen))
				}
			}
		}
	}

	// Reserved for future use
	_ = f.disable
	_ = f.dryRun
	_ = runtime.NumCPU()
	_ = fs

	// Create and run dispatcher
	d := dispatcher.New(providerReg, validatorReg, pipeline, exec, cfg, opts...)

	ctx := context.Background()
	resp, err := d.Dispatch(ctx, raw)
	if err != nil {
		log.Printf("[cos-dispatch] dispatch error: %v", err)
		fmt.Fprint(os.Stdout, `{"hookSpecificOutput":{"permissionDecision":"allow","reason":"internal error","additionalContext":""}}`)
		return 0
	}

	os.Stdout.Write(resp)

	if containsDeny(resp) {
		return 2
	}
	return 0
}

// newGeneratorForDispatch constructs an SQLGenerator using the tracker's DB
// and resolves the output dir relative to projectDir when it is relative.
func newGeneratorForDispatch(tracker *pattern.SQLTracker, cfg *config.Config, projectDir string) (*pattern.SQLGenerator, error) {
	autoCfg := cfg.Patterns.AutoGenerate
	if autoCfg.OutputDir != "" && !strings.HasPrefix(autoCfg.OutputDir, "/") {
		autoCfg.OutputDir = strings.TrimSuffix(projectDir, "/") + "/" + autoCfg.OutputDir
	}
	return pattern.NewSQLGeneratorWithModuleDir(tracker.DB(), autoCfg, projectDir)
}

// containsDeny checks if the response JSON contains a deny decision.
func containsDeny(resp []byte) bool {
	return strings.Contains(string(resp), `"permissionDecision":"deny"`)
}
