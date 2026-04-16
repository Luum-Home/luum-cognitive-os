package plugin

import (
	"context"
	"os"
	"path/filepath"
	"testing"
	"time"

	"github.com/luum/cos-dispatch/internal/validator"
	"github.com/luum/cos-dispatch/pkg/hook"
)

func TestBashAdapter_PassingScript(t *testing.T) {
	dir := t.TempDir()
	script := filepath.Join(dir, "pass.sh")
	if err := os.WriteFile(script, []byte(`#!/bin/bash
cat <<'EOF'
{"passed": true, "message": "all good"}
EOF
`), 0755); err != nil {
		t.Fatalf("write script: %v", err)
	}

	adapter := NewBashAdapter("test-pass", script, validator.CategoryIO, 5*time.Second)

	if adapter.Name() != "test-pass" {
		t.Errorf("Name() = %q, want %q", adapter.Name(), "test-pass")
	}
	if adapter.Category() != validator.CategoryIO {
		t.Errorf("Category() = %v, want IO", adapter.Category())
	}

	hookCtx := &hook.Context{
		Provider: hook.ProviderClaude,
		Event:    hook.CanonicalEventBeforeTool,
		ToolName: hook.ToolBash,
		ToolInput: hook.ToolInput{
			Command: "echo hello",
		},
	}

	result := adapter.Validate(context.Background(), hookCtx)
	if !result.Passed {
		t.Errorf("expected pass, got fail: %s", result.Message)
	}
}

func TestBashAdapter_FailingScript(t *testing.T) {
	dir := t.TempDir()
	script := filepath.Join(dir, "fail.sh")
	if err := os.WriteFile(script, []byte(`#!/bin/bash
cat <<'EOF'
{"passed": false, "should_block": true, "message": "blocked by policy", "error_code": "COS-TEST-001", "fix_hint": "don't do that"}
EOF
`), 0755); err != nil {
		t.Fatalf("write script: %v", err)
	}

	adapter := NewBashAdapter("test-fail", script, validator.CategoryCPU, 5*time.Second)
	hookCtx := &hook.Context{
		Provider: hook.ProviderClaude,
		Event:    hook.CanonicalEventBeforeTool,
		ToolName: hook.ToolBash,
	}

	result := adapter.Validate(context.Background(), hookCtx)
	if result.Passed {
		t.Fatal("expected fail, got pass")
	}
	if !result.ShouldBlock {
		t.Error("expected should_block = true")
	}
	if result.Message != "blocked by policy" {
		t.Errorf("message = %q, want %q", result.Message, "blocked by policy")
	}
	if result.Reference.Code != "COS-TEST-001" {
		t.Errorf("error_code = %q, want %q", result.Reference.Code, "COS-TEST-001")
	}
	if result.FixHint != "don't do that" {
		t.Errorf("fix_hint = %q, want %q", result.FixHint, "don't do that")
	}
}

func TestBashAdapter_ExitCode2Block(t *testing.T) {
	dir := t.TempDir()
	script := filepath.Join(dir, "block.sh")
	if err := os.WriteFile(script, []byte(`#!/bin/bash
echo "blocked by exit code"
exit 2
`), 0755); err != nil {
		t.Fatalf("write script: %v", err)
	}

	adapter := NewBashAdapter("test-block", script, validator.CategoryIO, 5*time.Second)
	hookCtx := &hook.Context{
		Provider: hook.ProviderClaude,
		Event:    hook.CanonicalEventBeforeTool,
		ToolName: hook.ToolBash,
	}

	result := adapter.Validate(context.Background(), hookCtx)
	if result.Passed {
		t.Fatal("expected fail for exit code 2")
	}
	if !result.ShouldBlock {
		t.Error("exit code 2 should block")
	}
}

func TestBashAdapter_NoOutput(t *testing.T) {
	dir := t.TempDir()
	script := filepath.Join(dir, "silent.sh")
	if err := os.WriteFile(script, []byte(`#!/bin/bash
# No output = pass
exit 0
`), 0755); err != nil {
		t.Fatalf("write script: %v", err)
	}

	adapter := NewBashAdapter("test-silent", script, validator.CategoryCPU, 5*time.Second)
	hookCtx := &hook.Context{
		Provider: hook.ProviderClaude,
		Event:    hook.CanonicalEventBeforeTool,
		ToolName: hook.ToolBash,
	}

	result := adapter.Validate(context.Background(), hookCtx)
	if !result.Passed {
		t.Errorf("expected pass for silent script, got: %s", result.Message)
	}
}

func TestBashAdapter_InvalidJSON(t *testing.T) {
	dir := t.TempDir()
	script := filepath.Join(dir, "bad_json.sh")
	if err := os.WriteFile(script, []byte(`#!/bin/bash
echo "not json"
exit 0
`), 0755); err != nil {
		t.Fatalf("write script: %v", err)
	}

	adapter := NewBashAdapter("test-badjson", script, validator.CategoryCPU, 5*time.Second)
	hookCtx := &hook.Context{
		Provider: hook.ProviderClaude,
		Event:    hook.CanonicalEventBeforeTool,
		ToolName: hook.ToolBash,
	}

	result := adapter.Validate(context.Background(), hookCtx)
	// Invalid JSON from a passing script should be treated as warn
	if result.Passed {
		t.Error("expected non-pass for invalid JSON")
	}
	if result.ShouldBlock {
		t.Error("invalid JSON should not block (just warn)")
	}
}

func TestBashAdapter_ScriptError(t *testing.T) {
	dir := t.TempDir()
	script := filepath.Join(dir, "error.sh")
	if err := os.WriteFile(script, []byte(`#!/bin/bash
echo "something went wrong" >&2
exit 1
`), 0755); err != nil {
		t.Fatalf("write script: %v", err)
	}

	adapter := NewBashAdapter("test-error", script, validator.CategoryIO, 5*time.Second)
	hookCtx := &hook.Context{
		Provider: hook.ProviderClaude,
		Event:    hook.CanonicalEventBeforeTool,
		ToolName: hook.ToolBash,
	}

	result := adapter.Validate(context.Background(), hookCtx)
	// Non-zero exit (not 2) should warn, not block
	if result.Passed {
		t.Error("expected non-pass for script error")
	}
	if result.ShouldBlock {
		t.Error("exit code 1 should not block (only exit code 2 blocks)")
	}
}

func TestCategoryFromString(t *testing.T) {
	tests := []struct {
		input string
		want  validator.ValidatorCategory
	}{
		{"io", validator.CategoryIO},
		{"git", validator.CategoryGit},
		{"cpu", validator.CategoryCPU},
		{"", validator.CategoryCPU},
		{"unknown", validator.CategoryCPU},
	}

	for _, tt := range tests {
		got := CategoryFromString(tt.input)
		if got != tt.want {
			t.Errorf("CategoryFromString(%q) = %v, want %v", tt.input, got, tt.want)
		}
	}
}
