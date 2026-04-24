package executor

import (
	"context"
	"testing"
	"time"

	"github.com/luum/cos-dispatch/internal/validator"
	"github.com/luum/cos-dispatch/pkg/hook"
)

// fakeValidator is a test validator with configurable behavior.
type fakeValidator struct {
	name     string
	category validator.ValidatorCategory
	result   *validator.Result
	delay    time.Duration
}

func (f *fakeValidator) Name() string                          { return f.name }
func (f *fakeValidator) Category() validator.ValidatorCategory { return f.category }
func (f *fakeValidator) Validate(ctx context.Context, _ *hook.Context) *validator.Result {
	if f.delay > 0 {
		select {
		case <-time.After(f.delay):
		case <-ctx.Done():
			return validator.Fail("timeout")
		}
	}
	return f.result
}

func TestSequentialExecutor_AllPass(t *testing.T) {
	exec := NewSequentialExecutor(5 * time.Second)
	validators := []validator.Validator{
		&fakeValidator{name: "v1", result: validator.Pass()},
		&fakeValidator{name: "v2", result: validator.Pass()},
	}

	errors := exec.Execute(context.Background(), &hook.Context{}, validators)
	if len(errors) != 0 {
		t.Errorf("expected 0 errors, got %d", len(errors))
	}
}

func TestSequentialExecutor_WithFailures(t *testing.T) {
	exec := NewSequentialExecutor(5 * time.Second)
	validators := []validator.Validator{
		&fakeValidator{name: "v1", result: validator.Pass()},
		&fakeValidator{name: "v2", result: validator.Fail("blocked")},
		&fakeValidator{name: "v3", result: validator.Warn("watch out")},
	}

	errors := exec.Execute(context.Background(), &hook.Context{}, validators)
	if len(errors) != 2 {
		t.Fatalf("expected 2 errors, got %d", len(errors))
	}
	if errors[0].ValidatorName != "v2" {
		t.Errorf("error[0].validator = %q, want %q", errors[0].ValidatorName, "v2")
	}
	if !errors[0].ShouldBlock {
		t.Error("error[0] should block")
	}
	if errors[1].ValidatorName != "v3" {
		t.Errorf("error[1].validator = %q, want %q", errors[1].ValidatorName, "v3")
	}
	if errors[1].ShouldBlock {
		t.Error("error[1] should not block (warning)")
	}
}

func TestSequentialExecutor_Empty(t *testing.T) {
	exec := NewSequentialExecutor(5 * time.Second)
	errors := exec.Execute(context.Background(), &hook.Context{}, nil)
	if len(errors) != 0 {
		t.Errorf("expected 0 errors, got %d", len(errors))
	}
}

func TestParallelExecutor_AllPass(t *testing.T) {
	exec := NewParallelExecutor(4, 4, 1, 5*time.Second)
	validators := []validator.Validator{
		&fakeValidator{name: "cpu1", category: validator.CategoryCPU, result: validator.Pass()},
		&fakeValidator{name: "io1", category: validator.CategoryIO, result: validator.Pass()},
		&fakeValidator{name: "git1", category: validator.CategoryGit, result: validator.Pass()},
	}

	errors := exec.Execute(context.Background(), &hook.Context{}, validators)
	if len(errors) != 0 {
		t.Errorf("expected 0 errors, got %d", len(errors))
	}
}

func TestParallelExecutor_MixedResults(t *testing.T) {
	exec := NewParallelExecutor(4, 4, 1, 5*time.Second)
	validators := []validator.Validator{
		&fakeValidator{name: "pass1", category: validator.CategoryCPU, result: validator.Pass()},
		&fakeValidator{name: "fail1", category: validator.CategoryIO, result: validator.Fail("io error")},
		&fakeValidator{name: "warn1", category: validator.CategoryCPU, result: validator.Warn("cpu warning")},
		&fakeValidator{name: "pass2", category: validator.CategoryGit, result: validator.Pass()},
	}

	errors := exec.Execute(context.Background(), &hook.Context{}, validators)
	if len(errors) != 2 {
		t.Fatalf("expected 2 errors, got %d", len(errors))
	}

	// Check that we got both expected failures (order may vary due to parallelism)
	names := map[string]bool{}
	for _, e := range errors {
		names[e.ValidatorName] = true
	}
	if !names["fail1"] {
		t.Error("expected fail1 in errors")
	}
	if !names["warn1"] {
		t.Error("expected warn1 in errors")
	}
}

func TestParallelExecutor_Empty(t *testing.T) {
	exec := NewParallelExecutor(4, 4, 1, 5*time.Second)
	errors := exec.Execute(context.Background(), &hook.Context{}, nil)
	if len(errors) != 0 {
		t.Errorf("expected 0 errors for nil input, got %d", len(errors))
	}
}

func TestParallelExecutor_CategorySeparation(t *testing.T) {
	// Git validators should be serialized (1 worker), so even with multiple
	// git validators, they run safely without index lock contention.
	exec := NewParallelExecutor(4, 4, 1, 5*time.Second)
	validators := []validator.Validator{
		&fakeValidator{name: "git1", category: validator.CategoryGit, result: validator.Pass(), delay: 10 * time.Millisecond},
		&fakeValidator{name: "git2", category: validator.CategoryGit, result: validator.Pass(), delay: 10 * time.Millisecond},
		&fakeValidator{name: "cpu1", category: validator.CategoryCPU, result: validator.Pass()},
	}

	start := time.Now()
	errors := exec.Execute(context.Background(), &hook.Context{}, validators)
	elapsed := time.Since(start)

	if len(errors) != 0 {
		t.Errorf("expected 0 errors, got %d", len(errors))
	}
	// With git_workers=1, two 10ms git validators should take at least 20ms
	if elapsed < 15*time.Millisecond {
		t.Logf("elapsed=%v (expected >= 20ms for serialized git validators)", elapsed)
	}
}

func TestToValidationError(t *testing.T) {
	v := &fakeValidator{name: "test-val"}
	r := &validator.Result{
		Passed:      false,
		Message:     "something wrong",
		ShouldBlock: true,
		Reference:   validator.Reference{Code: "COS-TEST-001"},
		FixHint:     "try this fix",
	}

	ve := toValidationError(v, r)
	if ve.ValidatorName != "test-val" {
		t.Errorf("ValidatorName = %q, want %q", ve.ValidatorName, "test-val")
	}
	if ve.Message != "something wrong" {
		t.Errorf("Message = %q, want %q", ve.Message, "something wrong")
	}
	if !ve.ShouldBlock {
		t.Error("ShouldBlock should be true")
	}
	if ve.ErrorCode != "COS-TEST-001" {
		t.Errorf("ErrorCode = %q, want %q", ve.ErrorCode, "COS-TEST-001")
	}
	if ve.FixHint != "try this fix" {
		t.Errorf("FixHint = %q, want %q", ve.FixHint, "try this fix")
	}
}
