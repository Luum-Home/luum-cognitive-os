// Package main — dispatch.go contains the stdin-dispatch logic extracted from
// main.go so it can be called from the subcommand router without nesting.
package main

import (
	"context"
	"encoding/json"
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
	fs.StringVar(&f.provider, "provider", "", "Override provider detection (claude|codex|gemini|cursor|devin)")
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

	// --disable NAME1,NAME2 — remove named validators from the registry before
	// the dispatcher is built.  We create a filtered registry so the dispatcher
	// never sees the disabled validators (they are not just skipped at runtime;
	// they are removed entirely so the tracker does not record them either).
	disabledNames := parseDisabledNames(f.disable)
	if len(disabledNames) > 0 {
		filteredReg := filterValidators(validatorReg, disabledNames, logger)
		validatorReg = filteredReg
	}

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
	// In --dry-run mode we still wire the tracker so execution data is collected
	// for production diagnosis — we just never emit a deny decision.
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

	// --dry-run: log the decision but always emit allow + dryRun:true marker.
	// The tracker has already recorded the execution above; only the response
	// written to stdout is replaced.
	if f.dryRun && containsDeny(resp) {
		logger.Printf("[cos-dispatch] dry-run: deny suppressed, emitting allow")
		resp = buildDryRunAllowResponse(resp)
	}

	os.Stdout.Write(resp)

	if !f.dryRun && containsDeny(resp) {
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
// It covers both the Claude/Codex/Gemini envelope (permissionDecision) and the
// Cursor envelope (action) and Devin envelope (cascadeDecision).
func containsDeny(resp []byte) bool {
	s := string(resp)
	return strings.Contains(s, `"permissionDecision":"deny"`) ||
		strings.Contains(s, `"action":"deny"`) ||
		strings.Contains(s, `"cascadeDecision":"deny"`)
}

// buildDryRunAllowResponse replaces a deny response with an allow response that
// includes a "dryRun":true field for observability.  The original deny reason is
// preserved inside a "dryRunDeniedReason" field so callers can audit what would
// have been blocked.
//
// The function attempts to parse the response as a generic JSON object and
// inject the dry-run markers.  If parsing fails (e.g. unexpected envelope), it
// returns a minimal fallback allow response.
func buildDryRunAllowResponse(denyResp []byte) []byte {
	var obj map[string]any
	if err := json.Unmarshal(denyResp, &obj); err != nil {
		// Unparseable response — return a safe fallback.
		return []byte(`{"hookSpecificOutput":{"permissionDecision":"allow","reason":"dry-run","additionalContext":""},"dryRun":true}`)
	}

	// Inject top-level dry-run marker.
	obj["dryRun"] = true

	// Flip the decision in whichever envelope is present.
	mutateDecision(obj, "permissionDecision", "deny", "allow")

	// Cursor envelope: {"action":"deny",...}
	if action, ok := obj["action"].(string); ok && action == "deny" {
		obj["action"] = "allow"
		obj["dryRunDeniedReason"] = obj["message"]
	}

	// Devin envelope: {"cascadeDecision":"deny",...}
	if cd, ok := obj["cascadeDecision"].(string); ok && cd == "deny" {
		obj["cascadeDecision"] = "allow"
		obj["dryRunDeniedReason"] = obj["reason"]
	}

	result, err := json.Marshal(obj)
	if err != nil {
		return []byte(`{"dryRun":true}`)
	}
	return result
}

// mutateDecision flips a nested string field inside a "hookSpecificOutput"
// sub-object from oldVal to newVal when the field is present.
func mutateDecision(obj map[string]any, field, oldVal, newVal string) {
	hso, ok := obj["hookSpecificOutput"].(map[string]any)
	if !ok {
		return
	}
	if v, ok := hso[field].(string); ok && v == oldVal {
		hso[field] = newVal
		obj["dryRunDeniedReason"] = hso["reason"]
	}
}

// parseDisabledNames splits a comma-separated validator disable list into a
// set of names.  Empty entries and surrounding whitespace are ignored.
func parseDisabledNames(raw string) map[string]struct{} {
	names := make(map[string]struct{})
	if raw == "" {
		return names
	}
	for _, part := range strings.Split(raw, ",") {
		name := strings.TrimSpace(part)
		if name != "" {
			names[name] = struct{}{}
		}
	}
	return names
}

// filterValidators returns a new Registry that contains only the validators
// from src whose names are NOT in the disabled set.  Skipped validators are
// logged at info level so operators can confirm the flag is working.
func filterValidators(src *validator.Registry, disabled map[string]struct{}, logger *log.Logger) *validator.Registry {
	dst := validator.NewRegistry()
	for _, reg := range src.Registrations() {
		name := reg.Validator.Name()
		if _, skip := disabled[name]; skip {
			logger.Printf("[cos-dispatch] --disable: skipping validator %q", name)
			continue
		}
		dst.Register(reg.Validator, reg.Predicate)
	}
	return dst
}
