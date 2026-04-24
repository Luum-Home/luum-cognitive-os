package validator

import (
	"context"
	"testing"

	"github.com/luum/cos-dispatch/pkg/hook"
)

// --- Helper: stub validator for registry tests ---

type stubValidator struct {
	name     string
	category ValidatorCategory
}

func (s *stubValidator) Name() string                                        { return s.name }
func (s *stubValidator) Validate(_ context.Context, _ *hook.Context) *Result { return Pass() }
func (s *stubValidator) Category() ValidatorCategory                         { return s.category }

func newStub(name string) *stubValidator {
	return &stubValidator{name: name, category: CategoryCPU}
}

// ============================================================
// Combinator tests
// ============================================================

func TestAnd_AllTrue(t *testing.T) {
	pred := And(
		func(*hook.Context) bool { return true },
		func(*hook.Context) bool { return true },
	)
	if !pred(&hook.Context{}) {
		t.Fatal("And with all-true predicates should return true")
	}
}

func TestAnd_OneFalse(t *testing.T) {
	pred := And(
		func(*hook.Context) bool { return true },
		func(*hook.Context) bool { return false },
	)
	if pred(&hook.Context{}) {
		t.Fatal("And should return false when any predicate is false")
	}
}

func TestAnd_Empty(t *testing.T) {
	pred := And()
	if !pred(&hook.Context{}) {
		t.Fatal("And with no predicates should return true (vacuous truth)")
	}
}

func TestOr_OneTrue(t *testing.T) {
	pred := Or(
		func(*hook.Context) bool { return false },
		func(*hook.Context) bool { return true },
	)
	if !pred(&hook.Context{}) {
		t.Fatal("Or should return true when any predicate is true")
	}
}

func TestOr_AllFalse(t *testing.T) {
	pred := Or(
		func(*hook.Context) bool { return false },
		func(*hook.Context) bool { return false },
	)
	if pred(&hook.Context{}) {
		t.Fatal("Or with all-false predicates should return false")
	}
}

func TestOr_Empty(t *testing.T) {
	pred := Or()
	if pred(&hook.Context{}) {
		t.Fatal("Or with no predicates should return false")
	}
}

func TestNot(t *testing.T) {
	trueP := func(*hook.Context) bool { return true }
	falseP := func(*hook.Context) bool { return false }

	if Not(trueP)(&hook.Context{}) {
		t.Fatal("Not(true) should be false")
	}
	if !Not(falseP)(&hook.Context{}) {
		t.Fatal("Not(false) should be true")
	}
}

func TestCombinators_Nested(t *testing.T) {
	// (A AND B) OR (NOT C) -> with A=true, B=false, C=false -> true
	pred := Or(
		And(
			func(*hook.Context) bool { return true },
			func(*hook.Context) bool { return false },
		),
		Not(func(*hook.Context) bool { return false }),
	)
	if !pred(&hook.Context{}) {
		t.Fatal("nested combinator should return true")
	}
}

// ============================================================
// Matcher tests
// ============================================================

func TestEventIs(t *testing.T) {
	ctx := &hook.Context{Event: hook.CanonicalEventBeforeTool}

	if !EventIs(hook.CanonicalEventBeforeTool)(ctx) {
		t.Fatal("EventIs should match the event")
	}
	if EventIs(hook.CanonicalEventAfterTool)(ctx) {
		t.Fatal("EventIs should not match a different event")
	}
}

func TestEventIs_NilContext(t *testing.T) {
	if EventIs(hook.CanonicalEventBeforeTool)(nil) {
		t.Fatal("EventIs should return false for nil context")
	}
}

func TestToolTypeIs(t *testing.T) {
	ctx := &hook.Context{ToolName: hook.ToolBash}

	if !ToolTypeIs(hook.ToolBash)(ctx) {
		t.Fatal("ToolTypeIs should match the tool type")
	}
	if ToolTypeIs(hook.ToolEdit)(ctx) {
		t.Fatal("ToolTypeIs should not match a different tool type")
	}
}

func TestToolTypeIs_NilContext(t *testing.T) {
	if ToolTypeIs(hook.ToolBash)(nil) {
		t.Fatal("ToolTypeIs should return false for nil context")
	}
}

func TestCommandContains(t *testing.T) {
	ctx := &hook.Context{
		ToolInput: hook.ToolInput{Command: "npm install --save-dev jest"},
	}

	if !CommandContains("install")(ctx) {
		t.Fatal("should match substring")
	}
	if CommandContains("uninstall")(ctx) {
		t.Fatal("should not match absent substring")
	}
}

func TestCommandContains_NilContext(t *testing.T) {
	if CommandContains("anything")(nil) {
		t.Fatal("should return false for nil context")
	}
}

func TestFilePathMatches(t *testing.T) {
	ctx := &hook.Context{
		ToolInput: hook.ToolInput{FilePath: "src/main.go"},
	}

	if !FilePathMatches("src/*.go")(ctx) {
		t.Fatal("should match glob pattern")
	}
	if FilePathMatches("pkg/*.go")(ctx) {
		t.Fatal("should not match non-matching glob pattern")
	}
}

func TestFilePathMatches_NilContext(t *testing.T) {
	if FilePathMatches("*.go")(nil) {
		t.Fatal("should return false for nil context")
	}
}

func TestFileExtensionIs(t *testing.T) {
	ctx := &hook.Context{
		ToolInput: hook.ToolInput{FilePath: "config/settings.yaml"},
	}

	// With dot prefix
	if !FileExtensionIs(".yaml")(ctx) {
		t.Fatal("should match extension with dot")
	}
	// Without dot prefix
	if !FileExtensionIs("yaml")(ctx) {
		t.Fatal("should match extension without dot")
	}
	// Wrong extension
	if FileExtensionIs(".json")(ctx) {
		t.Fatal("should not match different extension")
	}
}

func TestFileExtensionIs_NilContext(t *testing.T) {
	if FileExtensionIs("go")(nil) {
		t.Fatal("should return false for nil context")
	}
}

func TestFileExtensionIs_NoExtension(t *testing.T) {
	ctx := &hook.Context{
		ToolInput: hook.ToolInput{FilePath: "Makefile"},
	}
	if FileExtensionIs(".go")(ctx) {
		t.Fatal("should not match file without extension")
	}
}

func TestProviderIs(t *testing.T) {
	ctx := &hook.Context{Provider: hook.ProviderClaude}

	if !ProviderIs(hook.ProviderClaude)(ctx) {
		t.Fatal("should match provider")
	}
	if ProviderIs(hook.ProviderCodex)(ctx) {
		t.Fatal("should not match different provider")
	}
}

func TestProviderIs_NilContext(t *testing.T) {
	if ProviderIs(hook.ProviderClaude)(nil) {
		t.Fatal("should return false for nil context")
	}
}

// ============================================================
// Registry tests
// ============================================================

func TestRegistry_EmptyFindsNothing(t *testing.T) {
	reg := NewRegistry()
	validators := reg.FindValidators(&hook.Context{})
	if len(validators) != 0 {
		t.Fatalf("expected 0 validators, got %d", len(validators))
	}
}

func TestRegistry_SingleMatch(t *testing.T) {
	reg := NewRegistry()
	v := newStub("bash-guard")
	reg.Register(v, ToolTypeIs(hook.ToolBash))

	ctx := &hook.Context{ToolName: hook.ToolBash}
	validators := reg.FindValidators(ctx)
	if len(validators) != 1 {
		t.Fatalf("expected 1 validator, got %d", len(validators))
	}
	if validators[0].Name() != "bash-guard" {
		t.Fatalf("expected bash-guard, got %s", validators[0].Name())
	}
}

func TestRegistry_NoMatch(t *testing.T) {
	reg := NewRegistry()
	reg.Register(newStub("bash-guard"), ToolTypeIs(hook.ToolBash))

	ctx := &hook.Context{ToolName: hook.ToolEdit}
	validators := reg.FindValidators(ctx)
	if len(validators) != 0 {
		t.Fatalf("expected 0 validators, got %d", len(validators))
	}
}

func TestRegistry_MultipleRegistrations(t *testing.T) {
	reg := NewRegistry()
	reg.Register(newStub("bash-guard"), ToolTypeIs(hook.ToolBash))
	reg.Register(newStub("file-guard"), Or(ToolTypeIs(hook.ToolEdit), ToolTypeIs(hook.ToolWrite)))
	reg.Register(newStub("all-guard"), func(*hook.Context) bool { return true })

	// Bash context: bash-guard + all-guard
	bashCtx := &hook.Context{ToolName: hook.ToolBash}
	validators := reg.FindValidators(bashCtx)
	if len(validators) != 2 {
		t.Fatalf("expected 2 validators for Bash, got %d", len(validators))
	}

	// Edit context: file-guard + all-guard
	editCtx := &hook.Context{ToolName: hook.ToolEdit}
	validators = reg.FindValidators(editCtx)
	if len(validators) != 2 {
		t.Fatalf("expected 2 validators for Edit, got %d", len(validators))
	}

	// Read context: only all-guard
	readCtx := &hook.Context{ToolName: hook.ToolRead}
	validators = reg.FindValidators(readCtx)
	if len(validators) != 1 {
		t.Fatalf("expected 1 validator for Read, got %d", len(validators))
	}
}

func TestRegistry_AllMatch(t *testing.T) {
	reg := NewRegistry()
	reg.Register(newStub("v1"), func(*hook.Context) bool { return true })
	reg.Register(newStub("v2"), func(*hook.Context) bool { return true })
	reg.Register(newStub("v3"), func(*hook.Context) bool { return true })

	validators := reg.FindValidators(&hook.Context{})
	if len(validators) != 3 {
		t.Fatalf("expected 3 validators, got %d", len(validators))
	}
}

func TestRegistry_CompoundPredicate(t *testing.T) {
	reg := NewRegistry()
	reg.Register(newStub("before-bash"),
		And(
			EventIs(hook.CanonicalEventBeforeTool),
			ToolTypeIs(hook.ToolBash),
			CommandContains("rm"),
		),
	)

	// Should match
	ctx := &hook.Context{
		Event:     hook.CanonicalEventBeforeTool,
		ToolName:  hook.ToolBash,
		ToolInput: hook.ToolInput{Command: "rm -rf /tmp/test"},
	}
	if len(reg.FindValidators(ctx)) != 1 {
		t.Fatal("compound predicate should match")
	}

	// Wrong event
	ctx2 := &hook.Context{
		Event:     hook.CanonicalEventAfterTool,
		ToolName:  hook.ToolBash,
		ToolInput: hook.ToolInput{Command: "rm -rf /tmp/test"},
	}
	if len(reg.FindValidators(ctx2)) != 0 {
		t.Fatal("compound predicate should not match wrong event")
	}
}

func TestRegistry_PreservesOrder(t *testing.T) {
	reg := NewRegistry()
	always := func(*hook.Context) bool { return true }
	reg.Register(newStub("first"), always)
	reg.Register(newStub("second"), always)
	reg.Register(newStub("third"), always)

	validators := reg.FindValidators(&hook.Context{})
	expected := []string{"first", "second", "third"}
	for i, v := range validators {
		if v.Name() != expected[i] {
			t.Fatalf("expected %s at index %d, got %s", expected[i], i, v.Name())
		}
	}
}

// ============================================================
// Result constructor tests
// ============================================================

func TestPass(t *testing.T) {
	r := Pass()
	if !r.Passed {
		t.Fatal("Pass() should have Passed=true")
	}
	if r.ShouldBlock {
		t.Fatal("Pass() should not block")
	}
}

func TestFail(t *testing.T) {
	r := Fail("bad command")
	if r.Passed {
		t.Fatal("Fail() should have Passed=false")
	}
	if !r.ShouldBlock {
		t.Fatal("Fail() should block")
	}
	if r.Message != "bad command" {
		t.Fatalf("expected message 'bad command', got '%s'", r.Message)
	}
}

func TestWarn(t *testing.T) {
	r := Warn("risky pattern")
	if r.Passed {
		t.Fatal("Warn() should have Passed=false")
	}
	if r.ShouldBlock {
		t.Fatal("Warn() should not block")
	}
	if r.Message != "risky pattern" {
		t.Fatalf("expected message 'risky pattern', got '%s'", r.Message)
	}
}

// ============================================================
// ValidatorCategory stringer
// ============================================================

func TestValidatorCategory_String(t *testing.T) {
	tests := []struct {
		cat  ValidatorCategory
		want string
	}{
		{CategoryCPU, "CPU"},
		{CategoryIO, "IO"},
		{CategoryGit, "Git"},
		{ValidatorCategory(99), "Unknown"},
	}
	for _, tt := range tests {
		if got := tt.cat.String(); got != tt.want {
			t.Errorf("ValidatorCategory(%d).String() = %q, want %q", tt.cat, got, tt.want)
		}
	}
}
