// devin_test.go — Phase 5.4 tests for the Devin provider adapter.
//
// Per ADR-010 + test-strategy 5.4:
//   - Unit: Detect() env var logic, Parse() against fixture JSON, BuildResponse()
//     compared against golden files (regenerate with -update flag).
//   - Negative: malformed JSON returns provider error; no panic.
package provider

import (
	"encoding/json"
	"path/filepath"
	"testing"

	"github.com/luum/cos-dispatch/pkg/hook"
)

const devinTestdataDir = "testdata/providers"

// ---- Detect() tests ----------------------------------------------------------

func TestDevinDetect_SessionID(t *testing.T) {
	t.Setenv("DEVIN_SESSION_ID", "ws-sess-001")
	p := NewDevinProvider()
	if !p.Detect() {
		t.Error("Detect() = false with DEVIN_SESSION_ID set, want true")
	}
}

func TestDevinDetect_CascadeContext(t *testing.T) {
	t.Setenv("CASCADE_CONTEXT", "active")
	p := NewDevinProvider()
	if !p.Detect() {
		t.Error("Detect() = false with CASCADE_CONTEXT set, want true")
	}
}

func TestDevinDetect_NoEnv(t *testing.T) {
	t.Setenv("DEVIN_SESSION_ID", "")
	t.Setenv("CASCADE_CONTEXT", "")
	p := NewDevinProvider()
	if p.Detect() {
		t.Error("Detect() = true with no Devin signals, want false")
	}
}

// ---- Parse() tests against fixture JSON --------------------------------------

func TestDevinParse_FixturePreTool(t *testing.T) {
	raw := readFixture(t, filepath.Join(devinTestdataDir, "devin-pretool.json"))

	p := NewDevinProvider()
	ctx, err := p.Parse(raw)
	if err != nil {
		t.Fatalf("Parse: %v", err)
	}

	if ctx.Provider != hook.ProviderDevin {
		t.Errorf("Provider = %q, want %q", ctx.Provider, hook.ProviderDevin)
	}
	if ctx.Event != hook.CanonicalEventBeforeTool {
		t.Errorf("Event = %q, want %q", ctx.Event, hook.CanonicalEventBeforeTool)
	}
	if ctx.ToolName != hook.ToolBash {
		t.Errorf("ToolName = %q, want %q", ctx.ToolName, hook.ToolBash)
	}
	if ctx.ToolInput.Command != "rm -rf /tmp/data" {
		t.Errorf("Command = %q, want %q", ctx.ToolInput.Command, "rm -rf /tmp/data")
	}
	if ctx.SessionID != "devin-sess-xyz789" {
		t.Errorf("SessionID = %q, want %q", ctx.SessionID, "devin-sess-xyz789")
	}
}

func TestDevinParse_FixturePostTool(t *testing.T) {
	raw := readFixture(t, filepath.Join(devinTestdataDir, "devin-posttool.json"))

	p := NewDevinProvider()
	ctx, err := p.Parse(raw)
	if err != nil {
		t.Fatalf("Parse: %v", err)
	}

	if ctx.Event != hook.CanonicalEventAfterTool {
		t.Errorf("Event = %q, want %q", ctx.Event, hook.CanonicalEventAfterTool)
	}
	if ctx.ToolInput.FilePath != "/src/config.yaml" {
		t.Errorf("FilePath = %q, want %q", ctx.ToolInput.FilePath, "/src/config.yaml")
	}
}

func TestDevinParse_CascadeContextPreservedInMetadata(t *testing.T) {
	raw := readFixture(t, filepath.Join(devinTestdataDir, "devin-pretool.json"))

	p := NewDevinProvider()
	ctx, err := p.Parse(raw)
	if err != nil {
		t.Fatalf("Parse: %v", err)
	}

	if ctx.Metadata == nil {
		t.Fatal("Metadata is nil, expected cascade_workspace entry")
	}
	if ctx.Metadata["cascade_workspace"] != "/workspace/project" {
		t.Errorf("cascade_workspace = %v, want %q", ctx.Metadata["cascade_workspace"], "/workspace/project")
	}
	if ctx.Metadata["cascade_active_file"] != "main.go" {
		t.Errorf("cascade_active_file = %v, want %q", ctx.Metadata["cascade_active_file"], "main.go")
	}
}

func TestDevinParse_ProjectDirFromCascadeContext(t *testing.T) {
	// When DEVIN_PROJECT_DIR is not set, the workspace field from
	// cascade_context should populate ProjectDir.
	t.Setenv("DEVIN_PROJECT_DIR", "")
	raw := readFixture(t, filepath.Join(devinTestdataDir, "devin-pretool.json"))

	p := NewDevinProvider()
	ctx, err := p.Parse(raw)
	if err != nil {
		t.Fatalf("Parse: %v", err)
	}

	if ctx.ProjectDir != "/workspace/project" {
		t.Errorf("ProjectDir = %q, want %q (from cascade_context.workspace)", ctx.ProjectDir, "/workspace/project")
	}
}

func TestDevinParse_ProjectDirFromEnvTakesPriority(t *testing.T) {
	t.Setenv("DEVIN_PROJECT_DIR", "/explicit/path")
	raw := readFixture(t, filepath.Join(devinTestdataDir, "devin-pretool.json"))

	p := NewDevinProvider()
	ctx, err := p.Parse(raw)
	if err != nil {
		t.Fatalf("Parse: %v", err)
	}

	if ctx.ProjectDir != "/explicit/path" {
		t.Errorf("ProjectDir = %q, want %q (env should take priority over cascade_context)", ctx.ProjectDir, "/explicit/path")
	}
}

// ---- BuildResponse() golden file tests ---------------------------------------

func TestDevinBuildResponse_GoldenAllow(t *testing.T) {
	p := NewDevinProvider()
	resp := p.BuildResponse(nil, "allow", "", "")

	data, err := json.Marshal(resp)
	if err != nil {
		t.Fatalf("marshal: %v", err)
	}

	goldenPath := filepath.Join(devinTestdataDir, "devin-response-allow.golden.json")
	assertOrUpdateGolden(t, goldenPath, data)
}

func TestDevinBuildResponse_GoldenDeny(t *testing.T) {
	p := NewDevinProvider()
	resp := p.BuildResponse(nil, "deny", "blocked by policy", "")

	data, err := json.Marshal(resp)
	if err != nil {
		t.Fatalf("marshal: %v", err)
	}

	goldenPath := filepath.Join(devinTestdataDir, "devin-response-deny.golden.json")
	assertOrUpdateGolden(t, goldenPath, data)
}

func TestDevinBuildResponse_AdditionalContext(t *testing.T) {
	p := NewDevinProvider()
	resp := p.BuildResponse(nil, "deny", "blocked", "see rule COS-002")

	data, err := json.Marshal(resp)
	if err != nil {
		t.Fatalf("marshal: %v", err)
	}

	var result map[string]any
	if err := json.Unmarshal(data, &result); err != nil {
		t.Fatalf("unmarshal: %v", err)
	}
	reason, _ := result["reason"].(string)
	if reason == "" {
		t.Error("reason is empty, want combined message+additionalContext")
	}
}

// ---- Negative tests ----------------------------------------------------------

func TestDevinParse_MalformedJSON(t *testing.T) {
	p := NewDevinProvider()
	_, err := p.Parse([]byte(`{{invalid`))
	if err == nil {
		t.Fatal("expected error for malformed JSON, got nil")
	}
}

func TestDevinParse_EmptyToolInput(t *testing.T) {
	raw := []byte(`{
		"hook_event": "PreCascadeAction",
		"tool_name":  "Bash",
		"session_id": "ws-empty"
	}`)

	p := NewDevinProvider()
	ctx, err := p.Parse(raw)
	if err != nil {
		t.Fatalf("Parse: %v", err)
	}
	if ctx.ToolInput.Command != "" {
		t.Errorf("Command = %q, want empty", ctx.ToolInput.Command)
	}
}

func TestDevinParse_NoCascadeContext(t *testing.T) {
	raw := []byte(`{
		"hook_event": "PreCascadeAction",
		"tool_name":  "Bash",
		"tool_input": {"command": "ls"},
		"session_id": "ws-nocc"
	}`)

	p := NewDevinProvider()
	ctx, err := p.Parse(raw)
	if err != nil {
		t.Fatalf("Parse: %v", err)
	}
	// No cascade_context → metadata should not have cascade keys or be nil/empty.
	if ctx.Metadata != nil {
		if _, ok := ctx.Metadata["cascade_workspace"]; ok {
			t.Error("cascade_workspace present in metadata without cascade_context in payload")
		}
	}
}
