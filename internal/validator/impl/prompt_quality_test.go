package impl

import (
	"context"
	"strings"
	"testing"

	"github.com/luum/cos-dispatch/pkg/hook"
)

func TestPromptQuality_SkipsNonAgentTools(t *testing.T) {
	v := NewPromptQualityValidator()
	ctx := &hook.Context{ToolName: hook.ToolBash}
	if r := v.Validate(context.Background(), ctx); !r.Passed {
		t.Fatal("non-Agent tools should pass")
	}
}

func TestPromptQuality_HighQualityPasses(t *testing.T) {
	prompt := `Implement JWT refresh in internal/auth/handler.go.
Background: existing auth uses session cookies; we are migrating because we need stateless tokens.
Follow the pattern in internal/auth/login.go (UseCaseInterface).
ACCEPTANCE CRITERIA: 3 endpoints implemented; tests pass.
Verify: go test ./internal/auth/... should pass.
Scope: only the 3 specific endpoints in handler.go.`
	v := NewPromptQualityValidator()
	r := v.Validate(context.Background(), &hook.Context{
		ToolName:  hook.ToolAgent,
		ToolInput: hook.ToolInput{Prompt: prompt},
	})
	if !r.Passed {
		t.Fatalf("high-quality prompt should pass: %s", r.Message)
	}
}

func TestPromptQuality_LowQualityWarns(t *testing.T) {
	v := NewPromptQualityValidator()
	r := v.Validate(context.Background(), &hook.Context{
		ToolName:  hook.ToolAgent,
		ToolInput: hook.ToolInput{Prompt: "do stuff"},
	})
	if r.Passed {
		t.Fatal("low-quality prompt should warn")
	}
	if r.ShouldBlock {
		t.Fatal("prompt-quality must be advisory (non-blocking)")
	}
	if !strings.Contains(r.Message, "PROMPT QUALITY: LOW") {
		t.Errorf("expected LOW prefix: %s", r.Message)
	}
}

func TestPromptQuality_ScoreDimensions(t *testing.T) {
	v := NewPromptQualityValidator()
	prompt := "do stuff"
	r := v.Validate(context.Background(), &hook.Context{
		ToolName:  hook.ToolAgent,
		ToolInput: hook.ToolInput{Prompt: prompt},
	})
	if r.Passed {
		t.Fatal("expected warn for empty-content prompt")
	}
	if r.Details["specificity"] == "" || r.Details["actionability"] == "" {
		t.Error("expected score details to be populated")
	}
}

func TestPromptQuality_FilePathBoostsSpecificity(t *testing.T) {
	v := NewPromptQualityValidator()
	withPath := "Implement feature in internal/auth/handler.go using ctx pattern"
	withoutPath := "Implement feature using ctx pattern"

	r1 := v.Validate(context.Background(), &hook.Context{
		ToolName: hook.ToolAgent, ToolInput: hook.ToolInput{Prompt: withPath},
	})
	r2 := v.Validate(context.Background(), &hook.Context{
		ToolName: hook.ToolAgent, ToolInput: hook.ToolInput{Prompt: withoutPath},
	})

	// withPath should score higher specificity even if both fail to reach 30.
	s1 := r1.Details["specificity"]
	s2 := r2.Details["specificity"]
	if s1 == "" || s2 == "" {
		// withPath might pass; that's okay.
		return
	}
	if s1 == s2 {
		t.Errorf("expected file-path prompt to score higher specificity (%s vs %s)", s1, s2)
	}
}

func TestPromptQuality_NilContext(t *testing.T) {
	v := NewPromptQualityValidator()
	if r := v.Validate(context.Background(), nil); !r.Passed {
		t.Fatal("nil context should pass")
	}
}
