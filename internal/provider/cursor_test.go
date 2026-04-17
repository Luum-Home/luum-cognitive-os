// cursor_test.go — Phase 5.4 tests for the Cursor provider adapter.
//
// Per ADR-010 + test-strategy 5.4:
//   - Unit: Detect() env var logic, Parse() against fixture JSON, BuildResponse()
//     compared against golden files (regenerate with -update flag).
//   - Negative: malformed JSON returns provider error; no panic.
package provider

import (
	"encoding/json"
	"flag"
	"os"
	"path/filepath"
	"testing"

	"github.com/luum/cos-dispatch/pkg/hook"
)

// updateGolden, when set via -update, regenerates the golden response files
// instead of asserting against them.
var updateGolden = flag.Bool("update", false, "Regenerate golden files")

const cursorTestdataDir = "testdata/providers"

// ---- Detect() tests ----------------------------------------------------------

func TestCursorDetect_SessionID(t *testing.T) {
	t.Setenv("CURSOR_SESSION_ID", "sess-abc")
	p := NewCursorProvider()
	if !p.Detect() {
		t.Error("Detect() = false with CURSOR_SESSION_ID set, want true")
	}
}

func TestCursorDetect_ProjectDir(t *testing.T) {
	t.Setenv("CURSOR_PROJECT_DIR", "/tmp/cursor-proj")
	p := NewCursorProvider()
	if !p.Detect() {
		t.Error("Detect() = false with CURSOR_PROJECT_DIR set, want true")
	}
}

func TestCursorDetect_NoEnv_NoCursorDir(t *testing.T) {
	// Unset all Cursor env vars and ensure we are not in a .cursor/ directory.
	t.Setenv("CURSOR_SESSION_ID", "")
	t.Setenv("CURSOR_PROJECT_DIR", "")
	// Change CWD to a temp dir that has no .cursor sub-directory.
	orig, _ := os.Getwd()
	dir := t.TempDir()
	if err := os.Chdir(dir); err != nil {
		t.Skipf("cannot chdir: %v", err)
	}
	defer func() { _ = os.Chdir(orig) }()

	p := NewCursorProvider()
	if p.Detect() {
		t.Error("Detect() = true with no Cursor signals, want false")
	}
}

// ---- Parse() tests against fixture JSON --------------------------------------

func TestCursorParse_FixtureBeforeShellExecution(t *testing.T) {
	raw := readFixture(t, filepath.Join(cursorTestdataDir, "cursor-beforeshellexecution.json"))

	p := NewCursorProvider()
	ctx, err := p.Parse(raw)
	if err != nil {
		t.Fatalf("Parse: %v", err)
	}

	if ctx.Provider != hook.ProviderCursor {
		t.Errorf("Provider = %q, want %q", ctx.Provider, hook.ProviderCursor)
	}
	if ctx.Event != hook.CanonicalEventBeforeTool {
		t.Errorf("Event = %q, want %q", ctx.Event, hook.CanonicalEventBeforeTool)
	}
	if ctx.ToolName != hook.ToolBash {
		t.Errorf("ToolName = %q, want %q", ctx.ToolName, hook.ToolBash)
	}
	if ctx.ToolInput.Command != "git push origin main" {
		t.Errorf("Command = %q, want %q", ctx.ToolInput.Command, "git push origin main")
	}
	if ctx.SessionID != "cursor-session-abc123" {
		t.Errorf("SessionID = %q, want %q", ctx.SessionID, "cursor-session-abc123")
	}
}

func TestCursorParse_FixtureAfterFileEdit(t *testing.T) {
	raw := readFixture(t, filepath.Join(cursorTestdataDir, "cursor-afterfileedit.json"))

	p := NewCursorProvider()
	ctx, err := p.Parse(raw)
	if err != nil {
		t.Fatalf("Parse: %v", err)
	}

	if ctx.Event != hook.CanonicalEventAfterTool {
		t.Errorf("Event = %q, want %q", ctx.Event, hook.CanonicalEventAfterTool)
	}
	if ctx.ToolInput.FilePath != "/src/main.go" {
		t.Errorf("FilePath = %q, want %q", ctx.ToolInput.FilePath, "/src/main.go")
	}
}

func TestCursorParse_ModelIDPreservedInMetadata(t *testing.T) {
	raw := readFixture(t, filepath.Join(cursorTestdataDir, "cursor-beforeshellexecution.json"))

	p := NewCursorProvider()
	ctx, err := p.Parse(raw)
	if err != nil {
		t.Fatalf("Parse: %v", err)
	}

	// model_id from fixture is "claude-4-opus"
	if ctx.Metadata == nil {
		t.Fatal("Metadata is nil, expected cursor_model_id entry")
	}
	if ctx.Metadata["cursor_model_id"] != "claude-4-opus" {
		t.Errorf("cursor_model_id = %v, want %q", ctx.Metadata["cursor_model_id"], "claude-4-opus")
	}
}

func TestCursorParse_ProjectDirFromEnv(t *testing.T) {
	t.Setenv("CURSOR_PROJECT_DIR", "/workspace/myproject")
	raw := readFixture(t, filepath.Join(cursorTestdataDir, "cursor-beforeshellexecution.json"))

	p := NewCursorProvider()
	ctx, err := p.Parse(raw)
	if err != nil {
		t.Fatalf("Parse: %v", err)
	}

	if ctx.ProjectDir != "/workspace/myproject" {
		t.Errorf("ProjectDir = %q, want %q", ctx.ProjectDir, "/workspace/myproject")
	}
}

// ---- BuildResponse() golden file tests ---------------------------------------

func TestCursorBuildResponse_GoldenAllow(t *testing.T) {
	p := NewCursorProvider()
	resp := p.BuildResponse(nil, "allow", "", "")

	data, err := json.Marshal(resp)
	if err != nil {
		t.Fatalf("marshal: %v", err)
	}

	goldenPath := filepath.Join(cursorTestdataDir, "cursor-response-allow.golden.json")
	assertOrUpdateGolden(t, goldenPath, data)
}

func TestCursorBuildResponse_GoldenDeny(t *testing.T) {
	p := NewCursorProvider()
	resp := p.BuildResponse(nil, "deny", "blocked by policy", "")

	data, err := json.Marshal(resp)
	if err != nil {
		t.Fatalf("marshal: %v", err)
	}

	goldenPath := filepath.Join(cursorTestdataDir, "cursor-response-deny.golden.json")
	assertOrUpdateGolden(t, goldenPath, data)
}

func TestCursorBuildResponse_AdditionalContext(t *testing.T) {
	p := NewCursorProvider()
	resp := p.BuildResponse(nil, "deny", "blocked", "see rule COS-001")

	data, err := json.Marshal(resp)
	if err != nil {
		t.Fatalf("marshal: %v", err)
	}

	var result map[string]any
	if err := json.Unmarshal(data, &result); err != nil {
		t.Fatalf("unmarshal: %v", err)
	}
	// message must combine both parts
	msg, _ := result["message"].(string)
	if msg == "" {
		t.Error("message is empty, want combined message+additionalContext")
	}
	if len(msg) < len("blocked") {
		t.Errorf("message = %q; expected to contain both parts", msg)
	}
}

// ---- Negative tests ----------------------------------------------------------

func TestCursorParse_MalformedJSON(t *testing.T) {
	p := NewCursorProvider()
	_, err := p.Parse([]byte(`{bad json`))
	if err == nil {
		t.Fatal("expected error for malformed JSON, got nil")
	}
}

func TestCursorParse_EmptyToolInput(t *testing.T) {
	raw := []byte(`{
		"hook_event": "beforeShellExecution",
		"tool_name":  "Bash",
		"session_id": "cursor-empty"
	}`)

	p := NewCursorProvider()
	ctx, err := p.Parse(raw)
	if err != nil {
		t.Fatalf("Parse: %v", err)
	}
	if ctx.ToolInput.Command != "" {
		t.Errorf("Command = %q, want empty", ctx.ToolInput.Command)
	}
}

// ---- helpers -----------------------------------------------------------------

func readFixture(t *testing.T, path string) []byte {
	t.Helper()
	data, err := os.ReadFile(path)
	if err != nil {
		t.Fatalf("read fixture %s: %v", path, err)
	}
	return data
}

// assertOrUpdateGolden compares actual to the contents of goldenPath.
// When -update is passed, it writes actual to goldenPath instead.
// The comparison is JSON-normalised (re-marshal+unmarshal) to be whitespace-agnostic.
func assertOrUpdateGolden(t *testing.T, goldenPath string, actual []byte) {
	t.Helper()

	// Normalise: unmarshal then re-marshal for consistent whitespace.
	var v any
	if err := json.Unmarshal(actual, &v); err != nil {
		t.Fatalf("normalise actual JSON: %v", err)
	}
	normalised, err := json.Marshal(v)
	if err != nil {
		t.Fatalf("re-marshal actual JSON: %v", err)
	}

	if *updateGolden {
		if writeErr := os.WriteFile(goldenPath, append(normalised, '\n'), 0o644); writeErr != nil {
			t.Fatalf("update golden %s: %v", goldenPath, writeErr)
		}
		t.Logf("updated golden: %s", goldenPath)
		return
	}

	goldenRaw, err := os.ReadFile(goldenPath)
	if err != nil {
		t.Fatalf("read golden %s: %v (run with -update to create)", goldenPath, err)
	}

	var goldenV any
	if err := json.Unmarshal(goldenRaw, &goldenV); err != nil {
		t.Fatalf("parse golden %s: %v", goldenPath, err)
	}
	goldenNorm, _ := json.Marshal(goldenV)

	if string(normalised) != string(goldenNorm) {
		t.Errorf("BuildResponse output differs from golden %s:\ngot:  %s\nwant: %s",
			goldenPath, normalised, goldenNorm)
	}
}
