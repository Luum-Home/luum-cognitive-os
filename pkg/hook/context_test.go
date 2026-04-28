package hook

import (
	"encoding/json"
	"testing"
)

func TestContextMarshalJSON(t *testing.T) {
	exitCode := 0
	ctx := &Context{
		Provider:   ProviderClaude,
		Event:      CanonicalEventBeforeTool,
		ToolName:   ToolBash,
		ToolInput:  ToolInput{Command: "go test ./..."},
		SessionID:  "sess-123",
		ProjectDir: "/workspace/project",
		CWD:        "/workspace/project/pkg",
		RawJSON:    []byte(`{"should":"be excluded"}`),
		ExitCode:   &exitCode,
		ToolOutput: "PASS",
		Metadata:   map[string]any{"key": "value"},
	}

	data, err := json.Marshal(ctx)
	if err != nil {
		t.Fatalf("MarshalJSON failed: %v", err)
	}

	// Verify RawJSON is excluded from output.
	var raw map[string]json.RawMessage
	if err := json.Unmarshal(data, &raw); err != nil {
		t.Fatalf("Unmarshal raw map failed: %v", err)
	}
	if _, ok := raw["RawJSON"]; ok {
		t.Error("RawJSON should be excluded from JSON output")
	}

	// Verify key fields survived the round trip.
	var decoded Context
	if err := json.Unmarshal(data, &decoded); err != nil {
		t.Fatalf("Unmarshal Context failed: %v", err)
	}
	if decoded.Provider != ProviderClaude {
		t.Errorf("Provider = %q, want %q", decoded.Provider, ProviderClaude)
	}
	if decoded.Event != CanonicalEventBeforeTool {
		t.Errorf("Event = %q, want %q", decoded.Event, CanonicalEventBeforeTool)
	}
	if decoded.ToolName != ToolBash {
		t.Errorf("ToolName = %q, want %q", decoded.ToolName, ToolBash)
	}
	if decoded.ToolInput.Command != "go test ./..." {
		t.Errorf("ToolInput.Command = %q, want %q", decoded.ToolInput.Command, "go test ./...")
	}
	if decoded.SessionID != "sess-123" {
		t.Errorf("SessionID = %q, want %q", decoded.SessionID, "sess-123")
	}
}

func TestContextUnmarshalJSON_CapturesRawJSON(t *testing.T) {
	input := `{"provider":"gemini","event":"after_tool","tool_name":"Edit","session_id":"s-1"}`

	var ctx Context
	if err := json.Unmarshal([]byte(input), &ctx); err != nil {
		t.Fatalf("UnmarshalJSON failed: %v", err)
	}

	if ctx.Provider != ProviderGemini {
		t.Errorf("Provider = %q, want %q", ctx.Provider, ProviderGemini)
	}
	if ctx.Event != CanonicalEventAfterTool {
		t.Errorf("Event = %q, want %q", ctx.Event, CanonicalEventAfterTool)
	}
	if ctx.ToolName != ToolEdit {
		t.Errorf("ToolName = %q, want %q", ctx.ToolName, ToolEdit)
	}
	if len(ctx.RawJSON) == 0 {
		t.Error("RawJSON should be populated after UnmarshalJSON")
	}
	if string(ctx.RawJSON) != input {
		t.Errorf("RawJSON = %q, want %q", string(ctx.RawJSON), input)
	}
}

func TestContextHelpers(t *testing.T) {
	ctx := &Context{
		Event:    CanonicalEventBeforeTool,
		ToolName: ToolBash,
		ToolInput: ToolInput{
			Command:  "ls -la",
			FilePath: "/tmp/foo.go",
			Content:  "package main",
		},
		SessionID: "abc",
	}

	if !ctx.IsBashTool() {
		t.Error("IsBashTool() should return true for ToolBash")
	}
	if ctx.IsFileTool() {
		t.Error("IsFileTool() should return false for ToolBash")
	}
	if !ctx.IsBeforeTool() {
		t.Error("IsBeforeTool() should return true for before_tool event")
	}
	if ctx.IsAfterTool() {
		t.Error("IsAfterTool() should return false for before_tool event")
	}
	if !ctx.HasSessionID() {
		t.Error("HasSessionID() should return true when SessionID is set")
	}
	if ctx.GetCommand() != "ls -la" {
		t.Errorf("GetCommand() = %q, want %q", ctx.GetCommand(), "ls -la")
	}
	if ctx.GetFilePath() != "/tmp/foo.go" {
		t.Errorf("GetFilePath() = %q, want %q", ctx.GetFilePath(), "/tmp/foo.go")
	}
	if ctx.GetContent() != "package main" {
		t.Errorf("GetContent() = %q, want %q", ctx.GetContent(), "package main")
	}
}

func TestContextHelpers_FileTool(t *testing.T) {
	for _, tool := range []ToolType{ToolWrite, ToolEdit} {
		ctx := &Context{ToolName: tool}
		if !ctx.IsFileTool() {
			t.Errorf("IsFileTool() should return true for %q", tool)
		}
		if ctx.IsBashTool() {
			t.Errorf("IsBashTool() should return false for %q", tool)
		}
	}
}

func TestContextSetMetadata(t *testing.T) {
	ctx := &Context{}
	if ctx.Metadata != nil {
		t.Error("Metadata should be nil initially")
	}

	ctx.SetMetadata("validated", true)
	if ctx.Metadata == nil {
		t.Fatal("Metadata should be initialized after SetMetadata")
	}
	if v, ok := ctx.Metadata["validated"]; !ok || v != true {
		t.Errorf("Metadata[validated] = %v, want true", v)
	}

	ctx.SetMetadata("count", 42)
	if v, ok := ctx.Metadata["count"]; !ok || v != 42 {
		t.Errorf("Metadata[count] = %v, want 42", v)
	}
}

func TestContextUnmarshalJSON_WithToolInput(t *testing.T) {
	input := `{
		"provider": "claude",
		"event": "before_tool",
		"tool_name": "Bash",
		"tool_input": {
			"command": "echo hello",
			"description": "Print hello"
		},
		"session_id": "test-session",
		"project_dir": "/workspace",
		"cwd": "/workspace/src"
	}`

	var ctx Context
	if err := json.Unmarshal([]byte(input), &ctx); err != nil {
		t.Fatalf("UnmarshalJSON failed: %v", err)
	}

	if ctx.ToolInput.Command != "echo hello" {
		t.Errorf("ToolInput.Command = %q, want %q", ctx.ToolInput.Command, "echo hello")
	}
	if ctx.ToolInput.Description != "Print hello" {
		t.Errorf("ToolInput.Description = %q, want %q", ctx.ToolInput.Description, "Print hello")
	}
	if ctx.ProjectDir != "/workspace" {
		t.Errorf("ProjectDir = %q, want %q", ctx.ProjectDir, "/workspace")
	}
	if ctx.CWD != "/workspace/src" {
		t.Errorf("CWD = %q, want %q", ctx.CWD, "/workspace/src")
	}
}

func TestProviderConstants(t *testing.T) {
	providers := []Provider{
		ProviderClaude, ProviderCodex, ProviderGemini,
		ProviderCursor, ProviderWindsurf,
	}
	seen := make(map[Provider]bool)
	for _, p := range providers {
		if p == "" {
			t.Errorf("Provider constant should not be empty string")
		}
		if seen[p] {
			t.Errorf("Duplicate provider constant: %q", p)
		}
		seen[p] = true
	}
}

func TestCanonicalEventConstants(t *testing.T) {
	events := []CanonicalEvent{
		CanonicalEventBeforeTool, CanonicalEventAfterTool,
		CanonicalEventSessionStart, CanonicalEventSessionEnd,
		CanonicalEventPromptSubmit, CanonicalEventSubagentStart,
		CanonicalEventCompact,
	}
	seen := make(map[CanonicalEvent]bool)
	for _, e := range events {
		if e == "" {
			t.Errorf("CanonicalEvent constant should not be empty string")
		}
		if seen[e] {
			t.Errorf("Duplicate CanonicalEvent constant: %q", e)
		}
		seen[e] = true
	}
}

func TestToolTypeConstants(t *testing.T) {
	tools := []ToolType{
		ToolBash, ToolEdit, ToolWrite, ToolRead,
		ToolAgent, ToolGlob, ToolGrep,
	}
	seen := make(map[ToolType]bool)
	for _, tt := range tools {
		if tt == "" {
			t.Errorf("ToolType constant should not be empty string")
		}
		if seen[tt] {
			t.Errorf("Duplicate ToolType constant: %q", tt)
		}
		seen[tt] = true
	}
}

func TestContextExitCode(t *testing.T) {
	// Nil exit code (before_tool event).
	ctx := &Context{Event: CanonicalEventBeforeTool}
	if ctx.ExitCode != nil {
		t.Error("ExitCode should be nil for before_tool events")
	}

	// Non-nil exit code (after_tool event).
	code := 1
	ctx = &Context{
		Event:    CanonicalEventAfterTool,
		ExitCode: &code,
	}
	if ctx.ExitCode == nil || *ctx.ExitCode != 1 {
		t.Errorf("ExitCode = %v, want 1", ctx.ExitCode)
	}

	// Verify exit_code marshals correctly.
	data, err := json.Marshal(ctx)
	if err != nil {
		t.Fatalf("MarshalJSON failed: %v", err)
	}
	var decoded Context
	if err := json.Unmarshal(data, &decoded); err != nil {
		t.Fatalf("UnmarshalJSON failed: %v", err)
	}
	if decoded.ExitCode == nil || *decoded.ExitCode != 1 {
		t.Errorf("Decoded ExitCode = %v, want 1", decoded.ExitCode)
	}
}
