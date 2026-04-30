package provider

import (
	"encoding/json"
	"testing"

	"github.com/luum/cos-dispatch/pkg/hook"
)

// --- Claude Provider Tests ---

func TestClaudeParse_BashTool(t *testing.T) {
	raw := []byte(`{
		"hook_event": "PreToolUse",
		"tool_name": "Bash",
		"tool_input": {"command": "git status"},
		"session_id": "abc123"
	}`)

	p := NewClaudeProvider()
	ctx, err := p.Parse(raw)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	if ctx.Provider != hook.ProviderClaude {
		t.Errorf("provider = %q, want %q", ctx.Provider, hook.ProviderClaude)
	}
	if ctx.Event != hook.CanonicalEventBeforeTool {
		t.Errorf("event = %q, want %q", ctx.Event, hook.CanonicalEventBeforeTool)
	}
	if ctx.ToolName != hook.ToolBash {
		t.Errorf("tool_name = %q, want %q", ctx.ToolName, hook.ToolBash)
	}
	if ctx.ToolInput.Command != "git status" {
		t.Errorf("command = %q, want %q", ctx.ToolInput.Command, "git status")
	}
	if ctx.SessionID != "abc123" {
		t.Errorf("session_id = %q, want %q", ctx.SessionID, "abc123")
	}
}

func TestClaudeParse_PostToolUse(t *testing.T) {
	exitCode := 0
	raw := []byte(`{
		"hook_event": "PostToolUse",
		"tool_name": "Bash",
		"tool_input": {"command": "echo hello"},
		"session_id": "sess-456",
		"exit_code": 0,
		"output": "hello\n"
	}`)

	p := NewClaudeProvider()
	ctx, err := p.Parse(raw)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	if ctx.Event != hook.CanonicalEventAfterTool {
		t.Errorf("event = %q, want %q", ctx.Event, hook.CanonicalEventAfterTool)
	}
	if ctx.ExitCode == nil || *ctx.ExitCode != exitCode {
		t.Errorf("exit_code = %v, want %d", ctx.ExitCode, exitCode)
	}
	if ctx.ToolOutput != "hello\n" {
		t.Errorf("tool_output = %q, want %q", ctx.ToolOutput, "hello\n")
	}
}

func TestClaudeParse_WriteToolWithFilePath(t *testing.T) {
	raw := []byte(`{
		"hook_event": "PreToolUse",
		"tool_name": "Write",
		"tool_input": {"file_path": "/tmp/test.go", "content": "package main"},
		"session_id": "sess-789"
	}`)

	p := NewClaudeProvider()
	ctx, err := p.Parse(raw)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	if ctx.ToolName != hook.ToolWrite {
		t.Errorf("tool_name = %q, want %q", ctx.ToolName, hook.ToolWrite)
	}
	if ctx.ToolInput.FilePath != "/tmp/test.go" {
		t.Errorf("file_path = %q, want %q", ctx.ToolInput.FilePath, "/tmp/test.go")
	}
	if ctx.ToolInput.Content != "package main" {
		t.Errorf("content = %q, want %q", ctx.ToolInput.Content, "package main")
	}
}

func TestClaudeParse_InvalidJSON(t *testing.T) {
	p := NewClaudeProvider()
	_, err := p.Parse([]byte(`{invalid`))
	if err == nil {
		t.Fatal("expected error for invalid JSON, got nil")
	}
}

func TestClaudeBuildResponse(t *testing.T) {
	p := NewClaudeProvider()
	resp := p.BuildResponse(nil, "allow", "looks safe", "no concerns")

	data, err := json.Marshal(resp)
	if err != nil {
		t.Fatalf("marshal response: %v", err)
	}

	var result map[string]any
	if err := json.Unmarshal(data, &result); err != nil {
		t.Fatalf("unmarshal response: %v", err)
	}

	output, ok := result["hookSpecificOutput"].(map[string]any)
	if !ok {
		t.Fatal("missing hookSpecificOutput")
	}
	if output["permissionDecision"] != "allow" {
		t.Errorf("decision = %q, want %q", output["permissionDecision"], "allow")
	}
	if output["reason"] != "looks safe" {
		t.Errorf("reason = %q, want %q", output["reason"], "looks safe")
	}
	if output["additionalContext"] != "no concerns" {
		t.Errorf("additionalContext = %q, want %q", output["additionalContext"], "no concerns")
	}
}

func TestClaudeConfigPaths(t *testing.T) {
	p := NewClaudeProvider()
	paths := p.ConfigPaths("/workspace/project")
	if len(paths) != 1 {
		t.Fatalf("expected 1 config path, got %d", len(paths))
	}
	if paths[0] != "/workspace/project/.claude/settings.json" {
		t.Errorf("config path = %q, want %q", paths[0], "/workspace/project/.claude/settings.json")
	}
}

// --- Codex Provider Tests ---

func TestCodexParse_BashTool(t *testing.T) {
	raw := []byte(`{
		"hook_event": "PreToolUse",
		"tool_name": "Bash",
		"tool_input": {"command": "npm test"},
		"session_id": "codex-001"
	}`)

	p := NewCodexProvider()
	ctx, err := p.Parse(raw)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	if ctx.Provider != hook.ProviderCodex {
		t.Errorf("provider = %q, want %q", ctx.Provider, hook.ProviderCodex)
	}
	if ctx.Event != hook.CanonicalEventBeforeTool {
		t.Errorf("event = %q, want %q", ctx.Event, hook.CanonicalEventBeforeTool)
	}
	if ctx.ToolInput.Command != "npm test" {
		t.Errorf("command = %q, want %q", ctx.ToolInput.Command, "npm test")
	}
}

func TestCodexConfigPaths(t *testing.T) {
	p := NewCodexProvider()
	paths := p.ConfigPaths("/project")
	if len(paths) != 1 || paths[0] != "/project/.codex/hooks.json" {
		t.Errorf("config paths = %v, want [/project/.codex/hooks.json]", paths)
	}
}

func TestCodexParse_UserPromptSubmit(t *testing.T) {
	raw := []byte(`{
		"hook_event": "UserPromptSubmit",
		"tool_input": {"prompt": "ship ADR-081"},
		"session_id": "codex-002"
	}`)

	p := NewCodexProvider()
	ctx, err := p.Parse(raw)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if ctx.Event != hook.CanonicalEventPromptSubmit {
		t.Errorf("event = %q, want %q", ctx.Event, hook.CanonicalEventPromptSubmit)
	}
	if ctx.ToolInput.Prompt != "ship ADR-081" {
		t.Errorf("prompt = %q, want %q", ctx.ToolInput.Prompt, "ship ADR-081")
	}
}

func TestCodexParse_StopMapsToSessionEnd(t *testing.T) {
	raw := []byte(`{"hook_event":"Stop","session_id":"codex-stop"}`)
	p := NewCodexProvider()
	ctx, err := p.Parse(raw)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if ctx.Event != hook.CanonicalEventSessionEnd {
		t.Errorf("event = %q, want %q", ctx.Event, hook.CanonicalEventSessionEnd)
	}
}

func TestCodexParse_NonBashToolCoverageGapIsExplicit(t *testing.T) {
	raw := []byte(`{"hook_event":"PreToolUse","tool_name":"Edit","session_id":"codex-gap"}`)
	p := NewCodexProvider()
	ctx, err := p.Parse(raw)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if ctx.Metadata["parse_error_reason"] != "codex_tool_coverage_gap" {
		t.Fatalf("metadata = %v, want codex_tool_coverage_gap", ctx.Metadata)
	}
}

func TestCodexSupportedEvents(t *testing.T) {
	p := NewCodexProvider()
	supported := p.SupportedEvents()
	for _, event := range []string{"SessionStart", "UserPromptSubmit", "PreToolUse", "PostToolUse", "Stop"} {
		if !supported[event] {
			t.Fatalf("expected Codex event %s to be supported", event)
		}
	}
	if supported["PreCompact"] {
		t.Fatal("PreCompact must not be advertised for Codex")
	}
}

// --- Gemini Provider Tests ---

func TestGeminiParse_BeforeTool(t *testing.T) {
	raw := []byte(`{
		"hook_event": "BeforeTool",
		"tool_name": "Bash",
		"tool_input": {"command": "ls -la"},
		"session_id": "gem-session"
	}`)

	p := NewGeminiProvider()
	ctx, err := p.Parse(raw)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	if ctx.Provider != hook.ProviderGemini {
		t.Errorf("provider = %q, want %q", ctx.Provider, hook.ProviderGemini)
	}
	if ctx.Event != hook.CanonicalEventBeforeTool {
		t.Errorf("event = %q, want %q", ctx.Event, hook.CanonicalEventBeforeTool)
	}
}

func TestGeminiConfigPaths(t *testing.T) {
	p := NewGeminiProvider()
	paths := p.ConfigPaths("/workspace/myapp")
	if len(paths) != 1 || paths[0] != "/workspace/myapp/.gemini/settings.json" {
		t.Errorf("config paths = %v, want [/workspace/myapp/.gemini/settings.json]", paths)
	}
}

// --- Cursor Provider Tests ---

func TestCursorParse_BeforeShellExecution(t *testing.T) {
	raw := []byte(`{
		"hook_event": "beforeShellExecution",
		"tool_name": "Bash",
		"tool_input": {"command": "docker build ."},
		"session_id": "cursor-123"
	}`)

	p := NewCursorProvider()
	ctx, err := p.Parse(raw)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	if ctx.Provider != hook.ProviderCursor {
		t.Errorf("provider = %q, want %q", ctx.Provider, hook.ProviderCursor)
	}
	if ctx.Event != hook.CanonicalEventBeforeTool {
		t.Errorf("event = %q, want %q", ctx.Event, hook.CanonicalEventBeforeTool)
	}
	if ctx.ToolInput.Command != "docker build ." {
		t.Errorf("command = %q, want %q", ctx.ToolInput.Command, "docker build .")
	}
}

func TestCursorParse_AfterFileEdit(t *testing.T) {
	raw := []byte(`{
		"hook_event": "afterFileEdit",
		"tool_name": "Edit",
		"tool_input": {"file_path": "/src/main.go"},
		"session_id": "cursor-456"
	}`)

	p := NewCursorProvider()
	ctx, err := p.Parse(raw)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	if ctx.Event != hook.CanonicalEventAfterTool {
		t.Errorf("event = %q, want %q", ctx.Event, hook.CanonicalEventAfterTool)
	}
}

func TestCursorConfigPaths(t *testing.T) {
	p := NewCursorProvider()
	paths := p.ConfigPaths("/workspace")
	if len(paths) != 1 || paths[0] != "/workspace/.cursor/hooks.json" {
		t.Errorf("config paths = %v, want [/workspace/.cursor/hooks.json]", paths)
	}
}

// --- Windsurf Provider Tests ---

func TestWindsurfParse_PreCascadeAction(t *testing.T) {
	raw := []byte(`{
		"hook_event": "PreCascadeAction",
		"tool_name": "Bash",
		"tool_input": {"command": "make build"},
		"session_id": "ws-session"
	}`)

	p := NewWindsurfProvider()
	ctx, err := p.Parse(raw)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	if ctx.Provider != hook.ProviderWindsurf {
		t.Errorf("provider = %q, want %q", ctx.Provider, hook.ProviderWindsurf)
	}
	if ctx.Event != hook.CanonicalEventBeforeTool {
		t.Errorf("event = %q, want %q", ctx.Event, hook.CanonicalEventBeforeTool)
	}
}

func TestWindsurfParse_PostCascadeAction(t *testing.T) {
	raw := []byte(`{
		"hook_event": "PostCascadeAction",
		"tool_name": "Write",
		"tool_input": {"file_path": "/out/result.txt", "content": "done"},
		"session_id": "ws-session-2"
	}`)

	p := NewWindsurfProvider()
	ctx, err := p.Parse(raw)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	if ctx.Event != hook.CanonicalEventAfterTool {
		t.Errorf("event = %q, want %q", ctx.Event, hook.CanonicalEventAfterTool)
	}
}

func TestWindsurfConfigPaths(t *testing.T) {
	p := NewWindsurfProvider()
	paths := p.ConfigPaths("/myproject")
	if len(paths) != 1 || paths[0] != "/myproject/.windsurf/hooks.json" {
		t.Errorf("config paths = %v, want [/myproject/.windsurf/hooks.json]", paths)
	}
}

// --- Registry Tests ---

func TestRegistryDetect_Fallback(t *testing.T) {
	// With no env vars set, should fall back to Claude.
	reg := NewRegistry()
	p := reg.Detect()
	if p.Name() != hook.ProviderClaude {
		t.Errorf("fallback provider = %q, want %q", p.Name(), hook.ProviderClaude)
	}
}

func TestRegistryDetect_WithClaudeEnv(t *testing.T) {
	t.Setenv("CLAUDE_PROJECT_DIR", "/tmp/project")
	reg := NewRegistry()
	p := reg.Detect()
	if p.Name() != hook.ProviderClaude {
		t.Errorf("detected provider = %q, want %q", p.Name(), hook.ProviderClaude)
	}
}

func TestRegistryDetect_WithCodexEnv(t *testing.T) {
	t.Setenv("CODEX_PROJECT_DIR", "/tmp/codex-proj")
	reg := NewRegistry()
	p := reg.Detect()
	if p.Name() != hook.ProviderCodex {
		t.Errorf("detected provider = %q, want %q", p.Name(), hook.ProviderCodex)
	}
}

func TestRegistryDetect_WithGeminiEnv(t *testing.T) {
	t.Setenv("GEMINI_CWD", "/tmp/gemini-proj")
	reg := NewRegistry()
	p := reg.Detect()
	if p.Name() != hook.ProviderGemini {
		t.Errorf("detected provider = %q, want %q", p.Name(), hook.ProviderGemini)
	}
}

func TestRegistryDetect_WithWindsurfEnv(t *testing.T) {
	t.Setenv("WINDSURF_SESSION_ID", "ws-abc")
	reg := NewRegistry()
	p := reg.Detect()
	if p.Name() != hook.ProviderWindsurf {
		t.Errorf("detected provider = %q, want %q", p.Name(), hook.ProviderWindsurf)
	}
}

func TestRegistryGet_Found(t *testing.T) {
	reg := NewRegistry()
	p, ok := reg.Get(hook.ProviderGemini)
	if !ok {
		t.Fatal("expected to find Gemini provider")
	}
	if p.Name() != hook.ProviderGemini {
		t.Errorf("provider name = %q, want %q", p.Name(), hook.ProviderGemini)
	}
}

func TestRegistryGet_NotFound(t *testing.T) {
	reg := NewRegistry()
	_, ok := reg.Get(hook.Provider("nonexistent"))
	if ok {
		t.Fatal("expected not to find nonexistent provider")
	}
}

func TestRegistryDetect_PriorityOrder(t *testing.T) {
	// When multiple env vars are set, the first match in registration order wins.
	// Claude is registered first, so it should win over Codex.
	t.Setenv("CLAUDE_SESSION_ID", "claude-sess")
	t.Setenv("CODEX_PROJECT_DIR", "/codex")

	reg := NewRegistry()
	p := reg.Detect()
	if p.Name() != hook.ProviderClaude {
		t.Errorf("priority provider = %q, want %q (Claude should win over Codex)", p.Name(), hook.ProviderClaude)
	}
}

// --- BuildResponse format tests for all providers ---

// TestBuildResponse_Claude_Codex_Gemini verifies that the Claude-compatible
// providers (Claude, Codex, Gemini) emit the hookSpecificOutput envelope.
func TestBuildResponse_Claude_Codex_Gemini(t *testing.T) {
	providers := []Provider{
		NewClaudeProvider(),
		NewCodexProvider(),
		NewGeminiProvider(),
	}

	for _, p := range providers {
		t.Run(string(p.Name()), func(t *testing.T) {
			resp := p.BuildResponse(nil, "deny", "blocked by policy", "see docs")

			data, err := json.Marshal(resp)
			if err != nil {
				t.Fatalf("marshal: %v", err)
			}

			var result map[string]any
			if err := json.Unmarshal(data, &result); err != nil {
				t.Fatalf("unmarshal: %v", err)
			}

			output, ok := result["hookSpecificOutput"].(map[string]any)
			if !ok {
				t.Fatalf("missing hookSpecificOutput key in response: %s", data)
			}
			if output["permissionDecision"] != "deny" {
				t.Errorf("decision = %q, want %q", output["permissionDecision"], "deny")
			}
			if output["reason"] != "blocked by policy" {
				t.Errorf("reason = %q, want %q", output["reason"], "blocked by policy")
			}
		})
	}
}

// TestCursorBuildResponse_VendorEnvelope verifies that Cursor emits its
// vendor-conformant {"action","message"} envelope (not hookSpecificOutput).
func TestCursorBuildResponse_VendorEnvelope(t *testing.T) {
	p := NewCursorProvider()

	t.Run("deny", func(t *testing.T) {
		resp := p.BuildResponse(nil, "deny", "blocked by policy", "")
		data, err := json.Marshal(resp)
		if err != nil {
			t.Fatalf("marshal: %v", err)
		}

		var result map[string]any
		if err := json.Unmarshal(data, &result); err != nil {
			t.Fatalf("unmarshal: %v", err)
		}

		if _, hasHSO := result["hookSpecificOutput"]; hasHSO {
			t.Error("cursor response must NOT have hookSpecificOutput (wrong envelope)")
		}
		if result["action"] != "deny" {
			t.Errorf("action = %q, want %q", result["action"], "deny")
		}
		if result["message"] != "blocked by policy" {
			t.Errorf("message = %q, want %q", result["message"], "blocked by policy")
		}
	})

	t.Run("allow", func(t *testing.T) {
		resp := p.BuildResponse(nil, "allow", "", "")
		data, err := json.Marshal(resp)
		if err != nil {
			t.Fatalf("marshal: %v", err)
		}

		var result map[string]any
		if err := json.Unmarshal(data, &result); err != nil {
			t.Fatalf("unmarshal: %v", err)
		}

		if result["action"] != "allow" {
			t.Errorf("action = %q, want %q", result["action"], "allow")
		}
	})
}

// TestWindsurfBuildResponse_VendorEnvelope verifies that Windsurf emits its
// vendor-conformant {"cascadeDecision","reason"} envelope.
func TestWindsurfBuildResponse_VendorEnvelope(t *testing.T) {
	p := NewWindsurfProvider()

	t.Run("deny", func(t *testing.T) {
		resp := p.BuildResponse(nil, "deny", "blocked by policy", "")
		data, err := json.Marshal(resp)
		if err != nil {
			t.Fatalf("marshal: %v", err)
		}

		var result map[string]any
		if err := json.Unmarshal(data, &result); err != nil {
			t.Fatalf("unmarshal: %v", err)
		}

		if _, hasHSO := result["hookSpecificOutput"]; hasHSO {
			t.Error("windsurf response must NOT have hookSpecificOutput (wrong envelope)")
		}
		if result["cascadeDecision"] != "deny" {
			t.Errorf("cascadeDecision = %q, want %q", result["cascadeDecision"], "deny")
		}
		if result["reason"] != "blocked by policy" {
			t.Errorf("reason = %q, want %q", result["reason"], "blocked by policy")
		}
	})

	t.Run("allow", func(t *testing.T) {
		resp := p.BuildResponse(nil, "allow", "", "")
		data, err := json.Marshal(resp)
		if err != nil {
			t.Fatalf("marshal: %v", err)
		}

		var result map[string]any
		if err := json.Unmarshal(data, &result); err != nil {
			t.Fatalf("unmarshal: %v", err)
		}

		if result["cascadeDecision"] != "allow" {
			t.Errorf("cascadeDecision = %q, want %q", result["cascadeDecision"], "allow")
		}
	})
}

// --- Provider Name tests ---

func TestProviderNames(t *testing.T) {
	tests := []struct {
		provider Provider
		want     hook.Provider
	}{
		{NewClaudeProvider(), hook.ProviderClaude},
		{NewCodexProvider(), hook.ProviderCodex},
		{NewGeminiProvider(), hook.ProviderGemini},
		{NewCursorProvider(), hook.ProviderCursor},
		{NewWindsurfProvider(), hook.ProviderWindsurf},
	}

	for _, tt := range tests {
		t.Run(string(tt.want), func(t *testing.T) {
			if got := tt.provider.Name(); got != tt.want {
				t.Errorf("Name() = %q, want %q", got, tt.want)
			}
		})
	}
}
