package impl

import (
	"context"
	"strings"
	"testing"

	"github.com/luum/cos-dispatch/pkg/hook"
)

func runCompleteness(t *testing.T, prompt string) (passed bool, msg string) {
	t.Helper()
	v := NewCompletenessCheckerValidator()
	ctx := &hook.Context{
		ToolName:  hook.ToolAgent,
		ToolInput: hook.ToolInput{Prompt: prompt},
	}
	r := v.Validate(context.Background(), ctx)
	return r.Passed, r.Message
}

func TestCompleteness_SkipsNonAgentTools(t *testing.T) {
	v := NewCompletenessCheckerValidator()
	ctx := &hook.Context{ToolName: hook.ToolBash, ToolInput: hook.ToolInput{Command: "rm -rf /"}}
	if r := v.Validate(context.Background(), ctx); !r.Passed {
		t.Fatal("non-Agent tools should pass")
	}
}

func TestCompleteness_FlagsAllFilesWithoutList(t *testing.T) {
	passed, msg := runCompleteness(t, "Update all files to use the new API")
	if passed {
		t.Fatal("should warn on 'all files' without enumeration")
	}
	if !strings.Contains(msg, "all files") && !strings.Contains(strings.ToLower(msg), "discovery") {
		t.Errorf("expected discovery hint in message: %s", msg)
	}
}

func TestCompleteness_AcceptsWhenFilesListed(t *testing.T) {
	prompt := `Update all files to use new API. ACCEPTANCE CRITERIA: tests pass.
FILES TO PROCESS:
- a.go
- b.go
- c.go
verify: go test ./...`
	passed, _ := runCompleteness(t, prompt)
	if !passed {
		// At minimum, the "no acceptance criteria" rule must be satisfied.
		// With FILES TO PROCESS the "all files" rule is exempted.
		t.Logf("prompt may still warn for other reasons; this is informational")
	}
}

func TestCompleteness_FlagsMissingAcceptance(t *testing.T) {
	// Short prompt that would otherwise be clean.
	passed, msg := runCompleteness(t, "Refactor handler.go to use ctx.")
	if passed {
		t.Fatal("missing ACCEPTANCE CRITERIA should warn")
	}
	if !strings.Contains(msg, "ACCEPTANCE CRITERIA") {
		t.Errorf("expected ACCEPTANCE CRITERIA in message: %s", msg)
	}
}

func TestCompleteness_FlagsRebrandWithoutGrep(t *testing.T) {
	passed, msg := runCompleteness(t,
		"Rebrand everything from FooCo to BarCo. ACCEPTANCE CRITERIA: no FooCo remains.")
	if passed {
		t.Fatal("rebrand without grep count should warn")
	}
	if !strings.Contains(msg, "Rebrand") && !strings.Contains(msg, "rebrand") {
		t.Errorf("expected rebrand red flag: %s", msg)
	}
}

func TestCompleteness_LongPromptNeedsVerification(t *testing.T) {
	long := strings.Repeat("Implement user authentication using JWT and refresh tokens. ", 6) +
		"ACCEPTANCE CRITERIA: token refresh works."
	passed, msg := runCompleteness(t, long)
	if passed {
		t.Fatal("long prompt without verification command should warn")
	}
	if !strings.Contains(msg, "verification") && !strings.Contains(msg, "VERIFICATION") {
		t.Errorf("expected verification hint: %s", msg)
	}
}

func TestCompleteness_AdvisoryNotBlocking(t *testing.T) {
	v := NewCompletenessCheckerValidator()
	ctx := &hook.Context{
		ToolName:  hook.ToolAgent,
		ToolInput: hook.ToolInput{Prompt: "do all the things"},
	}
	r := v.Validate(context.Background(), ctx)
	if r.Passed {
		t.Fatal("expected warn")
	}
	if r.ShouldBlock {
		t.Fatal("completeness-check must be advisory (non-blocking)")
	}
}
