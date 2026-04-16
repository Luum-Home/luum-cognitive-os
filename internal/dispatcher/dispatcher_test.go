package dispatcher

import (
	"context"
	"encoding/json"
	"log"
	"os"
	"testing"
	"time"

	"github.com/luum/cos-dispatch/internal/config"
	"github.com/luum/cos-dispatch/internal/executor"
	"github.com/luum/cos-dispatch/internal/provider"
	"github.com/luum/cos-dispatch/internal/transformer"
	"github.com/luum/cos-dispatch/internal/validator"
	"github.com/luum/cos-dispatch/pkg/hook"
)

// --- Fake validators for testing ---

type fakeValidator struct {
	name     string
	category validator.ValidatorCategory
	result   *validator.Result
}

func (f *fakeValidator) Name() string                     { return f.name }
func (f *fakeValidator) Category() validator.ValidatorCategory { return f.category }
func (f *fakeValidator) Validate(_ context.Context, _ *hook.Context) *validator.Result {
	return f.result
}

// --- Helper to build a dispatcher ---

func newTestDispatcher(t *testing.T, validators []validator.Validator, preds []validator.Predicate) *Dispatcher {
	t.Helper()
	t.Setenv("CLAUDE_PROJECT_DIR", "/tmp/test-project")

	providerReg := provider.NewRegistry()
	validatorReg := validator.NewRegistry()
	for i, v := range validators {
		pred := validator.Predicate(func(_ *hook.Context) bool { return true })
		if i < len(preds) && preds[i] != nil {
			pred = preds[i]
		}
		validatorReg.Register(v, pred)
	}
	pipeline := transformer.NewPipeline()
	exec := executor.NewSequentialExecutor(5 * time.Second)
	cfg := config.DefaultConfig()

	silentLogger := log.New(os.Stderr, "", 0)

	return New(providerReg, validatorReg, pipeline, exec, cfg,
		WithProviderOverride(hook.ProviderClaude),
		WithLogger(silentLogger),
	)
}

func claudeJSON(event, toolName, command string) []byte {
	payload := map[string]any{
		"hook_event": event,
		"tool_name":  toolName,
		"tool_input": map[string]string{"command": command},
		"session_id": "test-session",
	}
	data, _ := json.Marshal(payload)
	return data
}

// --- Tests ---

func TestDispatch_NoValidators(t *testing.T) {
	d := newTestDispatcher(t, nil, nil)
	raw := claudeJSON("PreToolUse", "Bash", "echo hello")

	resp, err := d.Dispatch(context.Background(), raw)
	if err != nil {
		t.Fatalf("Dispatch: %v", err)
	}

	var result map[string]any
	if err := json.Unmarshal(resp, &result); err != nil {
		t.Fatalf("unmarshal response: %v", err)
	}

	output := result["hookSpecificOutput"].(map[string]any)
	if output["permissionDecision"] != "allow" {
		t.Errorf("decision = %q, want %q", output["permissionDecision"], "allow")
	}
}

func TestDispatch_AllPass(t *testing.T) {
	validators := []validator.Validator{
		&fakeValidator{name: "v1", result: validator.Pass()},
		&fakeValidator{name: "v2", result: validator.Pass()},
	}
	d := newTestDispatcher(t, validators, nil)
	raw := claudeJSON("PreToolUse", "Bash", "echo hello")

	resp, err := d.Dispatch(context.Background(), raw)
	if err != nil {
		t.Fatalf("Dispatch: %v", err)
	}

	var result map[string]any
	if err := json.Unmarshal(resp, &result); err != nil {
		t.Fatalf("unmarshal response: %v", err)
	}

	output := result["hookSpecificOutput"].(map[string]any)
	if output["permissionDecision"] != "allow" {
		t.Errorf("decision = %q, want %q", output["permissionDecision"], "allow")
	}
}

func TestDispatch_WithBlockingError(t *testing.T) {
	validators := []validator.Validator{
		&fakeValidator{name: "v1", result: validator.Pass()},
		&fakeValidator{name: "v2", result: validator.Fail("dangerous command")},
	}
	d := newTestDispatcher(t, validators, nil)
	raw := claudeJSON("PreToolUse", "Bash", "rm -rf /")

	resp, err := d.Dispatch(context.Background(), raw)
	if err != nil {
		t.Fatalf("Dispatch: %v", err)
	}

	var result map[string]any
	if err := json.Unmarshal(resp, &result); err != nil {
		t.Fatalf("unmarshal response: %v", err)
	}

	output := result["hookSpecificOutput"].(map[string]any)
	if output["permissionDecision"] != "deny" {
		t.Errorf("decision = %q, want %q", output["permissionDecision"], "deny")
	}
	if output["reason"] != "dangerous command" {
		t.Errorf("reason = %q, want %q", output["reason"], "dangerous command")
	}
}

func TestDispatch_WarningsOnly(t *testing.T) {
	validators := []validator.Validator{
		&fakeValidator{name: "v1", result: validator.Warn("be careful")},
	}
	d := newTestDispatcher(t, validators, nil)
	raw := claudeJSON("PreToolUse", "Bash", "echo test")

	resp, err := d.Dispatch(context.Background(), raw)
	if err != nil {
		t.Fatalf("Dispatch: %v", err)
	}

	var result map[string]any
	if err := json.Unmarshal(resp, &result); err != nil {
		t.Fatalf("unmarshal response: %v", err)
	}

	output := result["hookSpecificOutput"].(map[string]any)
	if output["permissionDecision"] != "allow" {
		t.Errorf("decision = %q, want %q (warnings should not block)", output["permissionDecision"], "allow")
	}
}

func TestDispatch_DisabledErrorCode(t *testing.T) {
	validators := []validator.Validator{
		&fakeValidator{name: "v1", result: &validator.Result{
			Passed:      false,
			Message:     "should be suppressed",
			ShouldBlock: true,
			Reference:   validator.Reference{Code: "COS-DISABLED-001"},
		}},
	}
	d := newTestDispatcher(t, validators, nil)
	d.config.Overrides.DisabledCodes = []string{"COS-DISABLED-001"}

	raw := claudeJSON("PreToolUse", "Bash", "echo test")
	resp, err := d.Dispatch(context.Background(), raw)
	if err != nil {
		t.Fatalf("Dispatch: %v", err)
	}

	var result map[string]any
	if err := json.Unmarshal(resp, &result); err != nil {
		t.Fatalf("unmarshal response: %v", err)
	}

	output := result["hookSpecificOutput"].(map[string]any)
	if output["permissionDecision"] != "allow" {
		t.Errorf("decision = %q, want %q (disabled code should not block)", output["permissionDecision"], "allow")
	}
}

func TestDispatch_InvalidJSON(t *testing.T) {
	d := newTestDispatcher(t, nil, nil)

	// Invalid JSON should fail-open
	resp, err := d.Dispatch(context.Background(), []byte(`{invalid`))
	if err != nil {
		t.Fatalf("Dispatch should not error (fail-open): %v", err)
	}

	var result map[string]any
	if err := json.Unmarshal(resp, &result); err != nil {
		t.Fatalf("unmarshal response: %v", err)
	}

	output := result["hookSpecificOutput"].(map[string]any)
	if output["permissionDecision"] != "allow" {
		t.Errorf("decision = %q, want %q (fail-open on parse error)", output["permissionDecision"], "allow")
	}
}

func TestDispatch_ProviderOverride(t *testing.T) {
	d := newTestDispatcher(t, nil, nil)

	// Even without CLAUDE_PROJECT_DIR set, the override forces Claude provider
	raw := claudeJSON("PreToolUse", "Bash", "ls")
	resp, err := d.Dispatch(context.Background(), raw)
	if err != nil {
		t.Fatalf("Dispatch: %v", err)
	}

	// Should get valid response (no error)
	var result map[string]any
	if err := json.Unmarshal(resp, &result); err != nil {
		t.Fatalf("unmarshal response: %v", err)
	}
	if _, ok := result["hookSpecificOutput"]; !ok {
		t.Error("expected hookSpecificOutput in response")
	}
}
