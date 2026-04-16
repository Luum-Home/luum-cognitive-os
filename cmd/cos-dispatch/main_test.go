package main

import (
	"context"
	"encoding/json"
	"io"
	"log"
	"os"
	"path/filepath"
	"testing"
	"time"

	"github.com/luum/cos-dispatch/internal/config"
	"github.com/luum/cos-dispatch/internal/dispatcher"
	"github.com/luum/cos-dispatch/internal/executor"
	"github.com/luum/cos-dispatch/internal/pattern"
	"github.com/luum/cos-dispatch/internal/provider"
	"github.com/luum/cos-dispatch/internal/transformer"
	"github.com/luum/cos-dispatch/internal/validator"
	"github.com/luum/cos-dispatch/pkg/hook"
)

func TestContainsDeny(t *testing.T) {
	tests := []struct {
		name string
		resp string
		want bool
	}{
		{
			name: "allow response",
			resp: `{"hookSpecificOutput":{"permissionDecision":"allow","reason":"","additionalContext":""}}`,
			want: false,
		},
		{
			name: "deny response",
			resp: `{"hookSpecificOutput":{"permissionDecision":"deny","reason":"blocked","additionalContext":""}}`,
			want: true,
		},
		{
			name: "empty response",
			resp: `{}`,
			want: false,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got := containsDeny([]byte(tt.resp))
			if got != tt.want {
				t.Errorf("containsDeny(%q) = %v, want %v", tt.resp, got, tt.want)
			}
		})
	}
}

// --- E2E: SQLTracker wired through a real dispatcher ---

// fakeValidator is a minimal validator for testing.
type fakeValidator struct {
	name   string
	result *validator.Result
}

func (f *fakeValidator) Name() string                             { return f.name }
func (f *fakeValidator) Category() validator.ValidatorCategory   { return validator.CategoryCPU }
func (f *fakeValidator) Validate(_ context.Context, _ *hook.Context) *validator.Result {
	return f.result
}

// hookJSON builds a minimal PreToolUse JSON payload for the dispatcher.
func hookJSON(sessionID, toolName string) []byte {
	payload := map[string]any{
		"hook_event": "PreToolUse",
		"tool_name":  toolName,
		"tool_input": map[string]string{"command": "echo test"},
		"session_id": sessionID,
	}
	b, _ := json.Marshal(payload)
	return b
}

// buildDispatcher constructs a dispatcher backed by the given tracker and
// pre-registered validators. Uses a sequential executor and a silent logger
// so tests are deterministic and quiet.
func buildDispatcher(t *testing.T, tracker *pattern.SQLTracker, validators []validator.Validator) *dispatcher.Dispatcher {
	t.Helper()
	t.Setenv("CLAUDE_PROJECT_DIR", t.TempDir())

	providerReg := provider.NewRegistry()
	validatorReg := validator.NewRegistry()
	for _, v := range validators {
		vCopy := v
		validatorReg.Register(vCopy, func(_ *hook.Context) bool { return true })
	}
	pipeline := transformer.NewPipeline()
	exec := executor.NewSequentialExecutor(5 * time.Second)
	cfg := config.DefaultConfig()
	silentLog := log.New(io.Discard, "", 0)

	opts := []dispatcher.Option{
		dispatcher.WithProviderOverride(hook.ProviderClaude),
		dispatcher.WithLogger(silentLog),
	}
	if tracker != nil {
		opts = append(opts, dispatcher.WithTracker(tracker))
	}
	return dispatcher.New(providerReg, validatorReg, pipeline, exec, cfg, opts...)
}

// TestE2E_TrackerWired verifies the full happy path: two hook events dispatched
// through a real dispatcher backed by a real SQLite file, both recorded in
// the executions table.
func TestE2E_TrackerWired(t *testing.T) {
	dbPath := filepath.Join(t.TempDir(), "test.db")

	tracker, err := pattern.NewTracker(dbPath)
	if err != nil {
		t.Fatalf("NewTracker: %v", err)
	}
	defer tracker.Close()

	v := []validator.Validator{
		&fakeValidator{name: "v-pass", result: validator.Pass()},
		&fakeValidator{name: "v-fail", result: &validator.Result{
			Passed:      false,
			Message:     "synthetic failure",
			ShouldBlock: false,
			Reference:   validator.Reference{Code: "COS-T-001"},
		}},
	}
	d := buildDispatcher(t, tracker, v)

	ctx := context.Background()
	for i := 0; i < 2; i++ {
		_, dispatchErr := d.Dispatch(ctx, hookJSON("sess-e2e", "Bash"))
		if dispatchErr != nil {
			t.Fatalf("Dispatch[%d]: %v", i, dispatchErr)
		}
	}

	// Flush all buffered records to disk before querying.
	if err := tracker.Flush(); err != nil {
		t.Fatalf("Flush: %v", err)
	}

	var execCount int
	if err := tracker.DB().QueryRow(`SELECT COUNT(*) FROM executions`).Scan(&execCount); err != nil {
		t.Fatalf("count executions: %v", err)
	}
	// 2 dispatches × 2 validators = 4 rows
	if execCount < 2 {
		t.Errorf("executions count = %d, want >= 2", execCount)
	}
}

// TestE2E_FailureSequencesPopulated verifies that two consecutive dispatch
// calls that both produce fail records for the same session_id result in
// a row in failure_sequences.
func TestE2E_FailureSequencesPopulated(t *testing.T) {
	dbPath := filepath.Join(t.TempDir(), "seq.db")

	tracker, err := pattern.NewTracker(dbPath)
	if err != nil {
		t.Fatalf("NewTracker: %v", err)
	}
	// Force buffer flush on every Record so consecutive calls land in the
	// same flush batch (buffer size 1 causes auto-flush after each record,
	// but that means each pair is in a separate batch). Set size to large so
	// both events land in one manual Flush call.
	tracker.SetBufferSize(100)
	defer tracker.Close()

	// Both validators fail with distinct error codes so a sequence pair is formed.
	v1 := &fakeValidator{name: "v-fail-A", result: &validator.Result{
		Passed:      false,
		Message:     "failure A",
		ShouldBlock: false,
		Reference:   validator.Reference{Code: "COS-T-A01"},
	}}
	v2 := &fakeValidator{name: "v-fail-B", result: &validator.Result{
		Passed:      false,
		Message:     "failure B",
		ShouldBlock: false,
		Reference:   validator.Reference{Code: "COS-T-B01"},
	}}

	d := buildDispatcher(t, tracker, []validator.Validator{v1, v2})

	ctx := context.Background()
	// Two dispatches in the same session so the two fail records are adjacent
	// in the flush buffer with matching session_id.
	for i := 0; i < 2; i++ {
		if _, dispErr := d.Dispatch(ctx, hookJSON("sess-seq-e2e", "Write")); dispErr != nil {
			t.Fatalf("Dispatch[%d]: %v", i, dispErr)
		}
	}

	if err := tracker.Flush(); err != nil {
		t.Fatalf("Flush: %v", err)
	}

	var execCount int
	if err := tracker.DB().QueryRow(`SELECT COUNT(*) FROM executions`).Scan(&execCount); err != nil {
		t.Fatalf("count executions: %v", err)
	}
	if execCount < 2 {
		t.Errorf("executions = %d, want >= 2", execCount)
	}

	// There must be at least one failure_sequences row (both validators fail
	// and are adjacent within the same session, with different error codes).
	var seqCount int
	if err := tracker.DB().QueryRow(`SELECT COUNT(*) FROM failure_sequences`).Scan(&seqCount); err != nil {
		t.Fatalf("count failure_sequences: %v", err)
	}
	if seqCount < 1 {
		t.Errorf("failure_sequences count = %d, want >= 1", seqCount)
	}

	_ = os.Remove(dbPath) // cleanup; t.TempDir also cleans up on test end
}
