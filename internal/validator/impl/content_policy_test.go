package impl

import (
	"context"
	"os"
	"path/filepath"
	"strings"
	"testing"

	"github.com/luum/cos-dispatch/pkg/hook"
)

func writePolicy(t *testing.T, body string) (projectDir, policyPath string) {
	t.Helper()
	projectDir = t.TempDir()
	if err := os.MkdirAll(filepath.Join(projectDir, ".cognitive-os"), 0o755); err != nil {
		t.Fatal(err)
	}
	policyPath = filepath.Join(projectDir, ".cognitive-os", "content-policy.yaml")
	if err := os.WriteFile(policyPath, []byte(body), 0o644); err != nil {
		t.Fatal(err)
	}
	return
}

func TestContentPolicy_BlocksOnTermMatch(t *testing.T) {
	projectDir, policyPath := writePolicy(t, `
prohibited:
  - term: "FORBIDDEN_TOKEN"
    reason: "Reserved internal identifier"
`)
	v := NewContentPolicyValidator(projectDir, policyPath)

	hookCtx := &hook.Context{
		Event:    hook.CanonicalEventAfterTool,
		ToolName: hook.ToolEdit,
		ToolInput: hook.ToolInput{
			FilePath: filepath.Join(projectDir, "code.go"),
			Content:  "// uses forbidden_token in lowercase",
		},
	}
	r := v.Validate(context.Background(), hookCtx)
	if r.Passed {
		t.Fatal("expected block on case-insensitive term match")
	}
	if !r.ShouldBlock {
		t.Fatal("expected ShouldBlock=true")
	}
	if !strings.Contains(r.Message, "FORBIDDEN_TOKEN") {
		t.Errorf("message should mention term: %s", r.Message)
	}
	if !strings.Contains(r.Message, "Reserved internal identifier") {
		t.Errorf("message should include reason: %s", r.Message)
	}
}

func TestContentPolicy_BlocksOnPatternMatch(t *testing.T) {
	projectDir, policyPath := writePolicy(t, `
prohibited:
  - pattern: "AKIA[0-9A-Z]{16}"
    reason: "AWS access key"
`)
	v := NewContentPolicyValidator(projectDir, policyPath)

	hookCtx := &hook.Context{
		Event:    hook.CanonicalEventAfterTool,
		ToolName: hook.ToolWrite,
		ToolInput: hook.ToolInput{
			FilePath: filepath.Join(projectDir, "secret.txt"),
			Content:  "key = AKIAABCDEFGHIJKLMNOP",
		},
	}
	r := v.Validate(context.Background(), hookCtx)
	if r.Passed {
		t.Fatal("expected block on regex pattern match")
	}
}

func TestContentPolicy_PassesWhenClean(t *testing.T) {
	projectDir, policyPath := writePolicy(t, `
prohibited:
  - term: "BAD_WORD"
    reason: "x"
`)
	v := NewContentPolicyValidator(projectDir, policyPath)

	hookCtx := &hook.Context{
		Event:    hook.CanonicalEventAfterTool,
		ToolName: hook.ToolEdit,
		ToolInput: hook.ToolInput{
			FilePath: filepath.Join(projectDir, "fine.go"),
			Content:  "this content is fine",
		},
	}
	if r := v.Validate(context.Background(), hookCtx); !r.Passed {
		t.Fatalf("expected pass: %s", r.Message)
	}
}

func TestContentPolicy_SkipsNonFileTools(t *testing.T) {
	projectDir, policyPath := writePolicy(t, `
prohibited:
  - term: "BAD"
    reason: "x"
`)
	v := NewContentPolicyValidator(projectDir, policyPath)

	hookCtx := &hook.Context{
		Event:     hook.CanonicalEventAfterTool,
		ToolName:  hook.ToolBash,
		ToolInput: hook.ToolInput{Command: "echo BAD"},
	}
	if r := v.Validate(context.Background(), hookCtx); !r.Passed {
		t.Fatal("Bash tool should not be policy-checked")
	}
}

func TestContentPolicy_NoPolicyFilePassesThrough(t *testing.T) {
	dir := t.TempDir()
	v := NewContentPolicyValidator(dir, filepath.Join(dir, "missing.yaml"))

	hookCtx := &hook.Context{
		Event:     hook.CanonicalEventAfterTool,
		ToolName:  hook.ToolWrite,
		ToolInput: hook.ToolInput{FilePath: "x.go", Content: "anything"},
	}
	if r := v.Validate(context.Background(), hookCtx); !r.Passed {
		t.Fatal("missing policy file should pass through")
	}
}

func TestContentPolicy_ParsesMixedQuotes(t *testing.T) {
	projectDir, policyPath := writePolicy(t, `
prohibited:
  - term: "double_quoted"
    reason: "first"
  - term: 'single_quoted'
    reason: 'second'
  - term: bare_term
    reason: third
`)
	v := NewContentPolicyValidator(projectDir, policyPath)

	for _, needle := range []string{"double_quoted", "single_quoted", "bare_term"} {
		hookCtx := &hook.Context{
			Event:    hook.CanonicalEventAfterTool,
			ToolName: hook.ToolEdit,
			ToolInput: hook.ToolInput{
				FilePath: filepath.Join(projectDir, needle+".go"),
				Content:  needle,
			},
		}
		r := v.Validate(context.Background(), hookCtx)
		if r.Passed {
			t.Errorf("expected block for term %q", needle)
		}
	}
}
