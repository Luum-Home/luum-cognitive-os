package installer

import (
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
	"testing"

	"luum-agent-os/cmd/cos/internal/manifest"
	"luum-agent-os/cmd/cos/internal/resolver"
)

// ---------------------------------------------------------------------------
// ExportTarget mapping tests
// ---------------------------------------------------------------------------

func TestResolveTargets_Skill(t *testing.T) {
	dir := t.TempDir()
	projectRoot := t.TempDir()

	// Create source file.
	writeTestFile(t, dir, "SKILL.md", "# My Skill")

	exports := []manifest.Export{
		{Source: "SKILL.md", Type: "skill"},
	}

	targets, err := ResolveTargets(exports, projectRoot, dir, "my-pkg")
	if err != nil {
		t.Fatalf("ResolveTargets error: %v", err)
	}

	if len(targets) != 1 {
		t.Fatalf("expected 1 target, got %d", len(targets))
	}

	expected := filepath.Join(projectRoot, ".claude", "skills", "my-pkg", "SKILL.md")
	if targets[0].Target != expected {
		t.Errorf("expected target %q, got %q", expected, targets[0].Target)
	}
}

func TestResolveTargets_Rule(t *testing.T) {
	dir := t.TempDir()
	projectRoot := t.TempDir()

	writeTestFile(t, dir, "rules/safety.md", "# Safety Rule")

	exports := []manifest.Export{
		{Source: "rules/safety.md", Type: "rule"},
	}

	targets, err := ResolveTargets(exports, projectRoot, dir, "my-pkg")
	if err != nil {
		t.Fatalf("ResolveTargets error: %v", err)
	}

	if len(targets) != 1 {
		t.Fatalf("expected 1 target, got %d", len(targets))
	}

	expected := filepath.Join(projectRoot, ".claude", "rules", "cos", "my-pkg", "safety.md")
	if targets[0].Target != expected {
		t.Errorf("expected target %q, got %q", expected, targets[0].Target)
	}
}

func TestResolveTargets_Hook(t *testing.T) {
	dir := t.TempDir()
	projectRoot := t.TempDir()

	writeTestFile(t, dir, "hooks/check.sh", "#!/bin/bash\necho ok")

	exports := []manifest.Export{
		{Source: "hooks/check.sh", Type: "hook", HookEvent: "PostToolUse", HookMatcher: "Bash"},
	}

	targets, err := ResolveTargets(exports, projectRoot, dir, "my-pkg")
	if err != nil {
		t.Fatalf("ResolveTargets error: %v", err)
	}

	if len(targets) != 1 {
		t.Fatalf("expected 1 target, got %d", len(targets))
	}

	expected := filepath.Join(projectRoot, ".cognitive-os", "hooks", "cos", "my-pkg", "check.sh")
	if targets[0].Target != expected {
		t.Errorf("expected target %q, got %q", expected, targets[0].Target)
	}
}

func TestResolveTargets_Template(t *testing.T) {
	dir := t.TempDir()
	projectRoot := t.TempDir()

	writeTestFile(t, dir, "templates/preamble.md", "# Preamble")

	exports := []manifest.Export{
		{Source: "templates/preamble.md", Type: "template"},
	}

	targets, err := ResolveTargets(exports, projectRoot, dir, "my-pkg")
	if err != nil {
		t.Fatalf("ResolveTargets error: %v", err)
	}

	if len(targets) != 1 {
		t.Fatalf("expected 1 target, got %d", len(targets))
	}

	expected := filepath.Join(projectRoot, ".cognitive-os", "templates", "my-pkg", "preamble.md")
	if targets[0].Target != expected {
		t.Errorf("expected target %q, got %q", expected, targets[0].Target)
	}
}

func TestResolveTargets_Agent(t *testing.T) {
	dir := t.TempDir()
	projectRoot := t.TempDir()

	writeTestFile(t, dir, "agents/sre-agent.yaml", "name: sre-agent")

	exports := []manifest.Export{
		{Source: "agents/sre-agent.yaml", Type: "agent"},
	}

	targets, err := ResolveTargets(exports, projectRoot, dir, "my-pkg")
	if err != nil {
		t.Fatalf("ResolveTargets error: %v", err)
	}

	if len(targets) != 1 {
		t.Fatalf("expected 1 target, got %d", len(targets))
	}

	expected := filepath.Join(projectRoot, ".cognitive-os", "agents", "my-pkg", "sre-agent.yaml")
	if targets[0].Target != expected {
		t.Errorf("expected target %q, got %q", expected, targets[0].Target)
	}
}

func TestResolveTargets_SkillPreservesDir(t *testing.T) {
	dir := t.TempDir()
	projectRoot := t.TempDir()

	writeTestFile(t, dir, "skills/my-skill/SKILL.md", "# My Skill")

	exports := []manifest.Export{
		{Source: "skills/my-skill/SKILL.md", Type: "skill"},
	}

	targets, err := ResolveTargets(exports, projectRoot, dir, "my-pkg")
	if err != nil {
		t.Fatalf("ResolveTargets error: %v", err)
	}

	if len(targets) != 1 {
		t.Fatalf("expected 1 target, got %d", len(targets))
	}

	// Should preserve "my-skill" directory, not use package name.
	expected := filepath.Join(projectRoot, ".claude", "skills", "my-skill", "SKILL.md")
	if targets[0].Target != expected {
		t.Errorf("expected target %q, got %q", expected, targets[0].Target)
	}
}

func TestResolveTargets_EmptyExports(t *testing.T) {
	dir := t.TempDir()
	projectRoot := t.TempDir()

	targets, err := ResolveTargets(nil, projectRoot, dir, "my-pkg")
	if err != nil {
		t.Fatalf("ResolveTargets error: %v", err)
	}

	if len(targets) != 0 {
		t.Errorf("expected 0 targets for empty exports, got %d", len(targets))
	}
}

func TestResolveTargets_InvalidType(t *testing.T) {
	dir := t.TempDir()
	projectRoot := t.TempDir()

	writeTestFile(t, dir, "something.txt", "content")

	exports := []manifest.Export{
		{Source: "something.txt", Type: "unknown-type"},
	}

	_, err := ResolveTargets(exports, projectRoot, dir, "my-pkg")
	if err == nil {
		t.Fatal("expected error for unsupported export type")
	}
	if !strings.Contains(err.Error(), "unsupported export type") {
		t.Errorf("expected 'unsupported export type' in error, got: %v", err)
	}
}

func TestResolveTargets_MissingSource(t *testing.T) {
	dir := t.TempDir()
	projectRoot := t.TempDir()

	exports := []manifest.Export{
		{Source: "nonexistent.md", Type: "rule"},
	}

	_, err := ResolveTargets(exports, projectRoot, dir, "my-pkg")
	if err == nil {
		t.Fatal("expected error for missing source file")
	}
}

// ---------------------------------------------------------------------------
// Install / Uninstall tests
// ---------------------------------------------------------------------------

func TestInstall_CopiesFiles(t *testing.T) {
	srcDir := t.TempDir()
	projectRoot := t.TempDir()

	content := "# Test Skill Content"
	writeTestFile(t, srcDir, "SKILL.md", content)

	targets := []ExportTarget{
		{
			Export: manifest.Export{Source: "SKILL.md", Type: "skill"},
			Source: filepath.Join(srcDir, "SKILL.md"),
			Target: filepath.Join(projectRoot, ".claude", "skills", "test-pkg", "SKILL.md"),
		},
	}

	if err := Install(targets); err != nil {
		t.Fatalf("Install error: %v", err)
	}

	data, err := os.ReadFile(targets[0].Target)
	if err != nil {
		t.Fatalf("expected target file to exist: %v", err)
	}
	if string(data) != content {
		t.Errorf("expected content %q, got %q", content, string(data))
	}
}

func TestInstall_PreservesPermissions(t *testing.T) {
	srcDir := t.TempDir()
	projectRoot := t.TempDir()

	srcPath := filepath.Join(srcDir, "check.sh")
	if err := os.WriteFile(srcPath, []byte("#!/bin/bash\necho ok"), 0755); err != nil {
		t.Fatal(err)
	}

	targets := []ExportTarget{
		{
			Export: manifest.Export{Source: "check.sh", Type: "hook"},
			Source: srcPath,
			Target: filepath.Join(projectRoot, "hooks", "check.sh"),
		},
	}

	if err := Install(targets); err != nil {
		t.Fatalf("Install error: %v", err)
	}

	info, err := os.Stat(targets[0].Target)
	if err != nil {
		t.Fatalf("expected target file to exist: %v", err)
	}

	// Check executable bit is set.
	if info.Mode()&0111 == 0 {
		t.Errorf("expected executable permissions, got %v", info.Mode())
	}
}

func TestInstall_CreatesDirectories(t *testing.T) {
	srcDir := t.TempDir()
	projectRoot := t.TempDir()

	writeTestFile(t, srcDir, "rule.md", "# Rule")

	deepTarget := filepath.Join(projectRoot, "a", "b", "c", "rule.md")
	targets := []ExportTarget{
		{
			Export: manifest.Export{Source: "rule.md", Type: "rule"},
			Source: filepath.Join(srcDir, "rule.md"),
			Target: deepTarget,
		},
	}

	if err := Install(targets); err != nil {
		t.Fatalf("Install error: %v", err)
	}

	if _, err := os.Stat(deepTarget); err != nil {
		t.Errorf("expected deep target to be created: %v", err)
	}
}

func TestInstall_OverwritesExisting(t *testing.T) {
	srcDir := t.TempDir()
	projectRoot := t.TempDir()

	targetPath := filepath.Join(projectRoot, "skill", "SKILL.md")
	if err := os.MkdirAll(filepath.Dir(targetPath), 0755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(targetPath, []byte("old content"), 0644); err != nil {
		t.Fatal(err)
	}

	newContent := "new content"
	writeTestFile(t, srcDir, "SKILL.md", newContent)

	targets := []ExportTarget{
		{
			Export: manifest.Export{Source: "SKILL.md", Type: "skill"},
			Source: filepath.Join(srcDir, "SKILL.md"),
			Target: targetPath,
		},
	}

	if err := Install(targets); err != nil {
		t.Fatalf("Install error: %v", err)
	}

	data, err := os.ReadFile(targetPath)
	if err != nil {
		t.Fatal(err)
	}
	if string(data) != newContent {
		t.Errorf("expected %q, got %q", newContent, string(data))
	}
}

func TestUninstall_RemovesFiles(t *testing.T) {
	srcDir := t.TempDir()
	projectRoot := t.TempDir()

	writeTestFile(t, srcDir, "SKILL.md", "# Skill")
	targetPath := filepath.Join(projectRoot, "skills", "pkg", "SKILL.md")

	targets := []ExportTarget{
		{
			Export: manifest.Export{Source: "SKILL.md", Type: "skill"},
			Source: filepath.Join(srcDir, "SKILL.md"),
			Target: targetPath,
		},
	}

	if err := Install(targets); err != nil {
		t.Fatalf("Install error: %v", err)
	}

	if _, err := os.Stat(targetPath); err != nil {
		t.Fatalf("file should exist after install: %v", err)
	}

	if err := Uninstall(targets); err != nil {
		t.Fatalf("Uninstall error: %v", err)
	}

	if _, err := os.Stat(targetPath); !os.IsNotExist(err) {
		t.Error("expected file to be removed after uninstall")
	}
}

func TestUninstall_CleansEmptyDirs(t *testing.T) {
	projectRoot := t.TempDir()

	targetPath := filepath.Join(projectRoot, "a", "b", "c", "file.md")
	if err := os.MkdirAll(filepath.Dir(targetPath), 0755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(targetPath, []byte("content"), 0644); err != nil {
		t.Fatal(err)
	}

	targets := []ExportTarget{
		{
			Export: manifest.Export{Source: "file.md", Type: "rule"},
			Source: "/dev/null", // not used in uninstall
			Target: targetPath,
		},
	}

	if err := Uninstall(targets); err != nil {
		t.Fatalf("Uninstall error: %v", err)
	}

	// The empty directories "c", "b", "a" should be cleaned up.
	if _, err := os.Stat(filepath.Join(projectRoot, "a")); !os.IsNotExist(err) {
		t.Error("expected empty parent dirs to be removed")
	}
}

func TestUninstall_MissingFilesNoError(t *testing.T) {
	targets := []ExportTarget{
		{
			Export: manifest.Export{Source: "gone.md", Type: "rule"},
			Source: "/dev/null",
			Target: "/tmp/cos-test-nonexistent-file-" + t.Name(),
		},
	}

	// Should not error when files are already gone.
	if err := Uninstall(targets); err != nil {
		t.Errorf("Uninstall should not error for missing files, got: %v", err)
	}
}

// ---------------------------------------------------------------------------
// Hook registration tests
// ---------------------------------------------------------------------------

func TestRegisterHooks_CreatesSettingsJson(t *testing.T) {
	projectRoot := t.TempDir()
	settingsPath := filepath.Join(projectRoot, ".claude", "settings.json")

	exports := []manifest.Export{
		{Source: "hooks/check.sh", Type: "hook", HookEvent: "PostToolUse", HookMatcher: "Bash"},
	}

	if err := RegisterHooks(settingsPath, exports, ".cognitive-os/hooks/cos/my-pkg"); err != nil {
		t.Fatalf("RegisterHooks error: %v", err)
	}

	if _, err := os.Stat(settingsPath); err != nil {
		t.Fatalf("expected settings.json to be created: %v", err)
	}

	data, err := os.ReadFile(settingsPath)
	if err != nil {
		t.Fatal(err)
	}

	if !strings.Contains(string(data), "check.sh") {
		t.Error("expected settings.json to contain hook command")
	}
}

func TestRegisterHooks_AddsToExisting(t *testing.T) {
	projectRoot := t.TempDir()
	settingsDir := filepath.Join(projectRoot, ".claude")
	if err := os.MkdirAll(settingsDir, 0755); err != nil {
		t.Fatal(err)
	}

	settingsPath := filepath.Join(settingsDir, "settings.json")

	// Write existing settings with an existing hook.
	existing := map[string]interface{}{
		"hooks": map[string]interface{}{
			"PostToolUse": []interface{}{
				map[string]interface{}{
					"matcher": "Bash",
					"hooks": []interface{}{
						map[string]interface{}{
							"type":    "command",
							"command": "bash existing-hook.sh",
						},
					},
				},
			},
		},
	}
	data, _ := json.MarshalIndent(existing, "", "  ")
	if err := os.WriteFile(settingsPath, data, 0644); err != nil {
		t.Fatal(err)
	}

	exports := []manifest.Export{
		{Source: "hooks/new-hook.sh", Type: "hook", HookEvent: "PostToolUse", HookMatcher: "Bash"},
	}

	if err := RegisterHooks(settingsPath, exports, ".cognitive-os/hooks/cos/my-pkg"); err != nil {
		t.Fatalf("RegisterHooks error: %v", err)
	}

	result, err := os.ReadFile(settingsPath)
	if err != nil {
		t.Fatal(err)
	}

	content := string(result)
	if !strings.Contains(content, "existing-hook.sh") {
		t.Error("expected existing hook to be preserved")
	}
	if !strings.Contains(content, "new-hook.sh") {
		t.Error("expected new hook to be added")
	}
}

func TestRegisterHooks_Deduplication(t *testing.T) {
	projectRoot := t.TempDir()
	settingsPath := filepath.Join(projectRoot, ".claude", "settings.json")

	exports := []manifest.Export{
		{Source: "hooks/check.sh", Type: "hook", HookEvent: "PostToolUse", HookMatcher: "Bash"},
	}

	// Register twice.
	if err := RegisterHooks(settingsPath, exports, ".cognitive-os/hooks/cos/my-pkg"); err != nil {
		t.Fatalf("first RegisterHooks error: %v", err)
	}
	if err := RegisterHooks(settingsPath, exports, ".cognitive-os/hooks/cos/my-pkg"); err != nil {
		t.Fatalf("second RegisterHooks error: %v", err)
	}

	data, err := os.ReadFile(settingsPath)
	if err != nil {
		t.Fatal(err)
	}

	// Count occurrences of the hook command.
	count := strings.Count(string(data), "check.sh")
	if count != 1 {
		t.Errorf("expected hook to appear once (dedup), appeared %d times", count)
	}
}

func TestRegisterHooks_CorrectEvent(t *testing.T) {
	projectRoot := t.TempDir()
	settingsPath := filepath.Join(projectRoot, ".claude", "settings.json")

	exports := []manifest.Export{
		{Source: "hooks/pre.sh", Type: "hook", HookEvent: "PreToolUse", HookMatcher: "Agent"},
	}

	if err := RegisterHooks(settingsPath, exports, ".cognitive-os/hooks/cos/my-pkg"); err != nil {
		t.Fatalf("RegisterHooks error: %v", err)
	}

	data, err := os.ReadFile(settingsPath)
	if err != nil {
		t.Fatal(err)
	}

	var settings map[string]interface{}
	if err := json.Unmarshal(data, &settings); err != nil {
		t.Fatalf("failed to parse settings: %v", err)
	}

	hooks, ok := settings["hooks"].(map[string]interface{})
	if !ok {
		t.Fatal("expected hooks map")
	}

	if _, ok := hooks["PreToolUse"]; !ok {
		t.Error("expected hook to be under PreToolUse event")
	}
}

func TestRegisterHooks_CorrectMatcher(t *testing.T) {
	projectRoot := t.TempDir()
	settingsPath := filepath.Join(projectRoot, ".claude", "settings.json")

	exports := []manifest.Export{
		{Source: "hooks/check.sh", Type: "hook", HookEvent: "PostToolUse", HookMatcher: "Edit|Write"},
	}

	if err := RegisterHooks(settingsPath, exports, ".cognitive-os/hooks/cos/my-pkg"); err != nil {
		t.Fatalf("RegisterHooks error: %v", err)
	}

	data, err := os.ReadFile(settingsPath)
	if err != nil {
		t.Fatal(err)
	}

	if !strings.Contains(string(data), "Edit|Write") {
		t.Error("expected matcher 'Edit|Write' in settings")
	}
}

func TestUnregisterHooks_RemovesEntries(t *testing.T) {
	projectRoot := t.TempDir()
	settingsPath := filepath.Join(projectRoot, ".claude", "settings.json")

	exports := []manifest.Export{
		{Source: "hooks/check.sh", Type: "hook", HookEvent: "PostToolUse", HookMatcher: "Bash"},
	}

	hookBasePath := ".cognitive-os/hooks/cos/my-pkg"

	if err := RegisterHooks(settingsPath, exports, hookBasePath); err != nil {
		t.Fatalf("RegisterHooks error: %v", err)
	}

	if err := UnregisterHooks(settingsPath, exports, hookBasePath); err != nil {
		t.Fatalf("UnregisterHooks error: %v", err)
	}

	data, err := os.ReadFile(settingsPath)
	if err != nil {
		t.Fatal(err)
	}

	if strings.Contains(string(data), "check.sh") {
		t.Error("expected hook to be removed after UnregisterHooks")
	}
}

func TestUnregisterHooks_PreservesOthers(t *testing.T) {
	projectRoot := t.TempDir()
	settingsPath := filepath.Join(projectRoot, ".claude", "settings.json")

	// Register two different packages.
	exports1 := []manifest.Export{
		{Source: "hooks/first.sh", Type: "hook", HookEvent: "PostToolUse", HookMatcher: "Bash"},
	}
	exports2 := []manifest.Export{
		{Source: "hooks/second.sh", Type: "hook", HookEvent: "PostToolUse", HookMatcher: "Bash"},
	}

	if err := RegisterHooks(settingsPath, exports1, ".cognitive-os/hooks/cos/pkg1"); err != nil {
		t.Fatal(err)
	}
	if err := RegisterHooks(settingsPath, exports2, ".cognitive-os/hooks/cos/pkg2"); err != nil {
		t.Fatal(err)
	}

	// Unregister only the first.
	if err := UnregisterHooks(settingsPath, exports1, ".cognitive-os/hooks/cos/pkg1"); err != nil {
		t.Fatal(err)
	}

	data, err := os.ReadFile(settingsPath)
	if err != nil {
		t.Fatal(err)
	}

	content := string(data)
	if strings.Contains(content, "first.sh") {
		t.Error("expected first hook to be removed")
	}
	if !strings.Contains(content, "second.sh") {
		t.Error("expected second hook to be preserved")
	}
}

func TestBuildHookCommand(t *testing.T) {
	exp := manifest.Export{Source: "hooks/check.sh"}
	cmd := buildHookCommand(".cognitive-os/hooks/cos/my-pkg", exp)

	expected := `bash "$CLAUDE_PROJECT_DIR/.cognitive-os/hooks/cos/my-pkg/check.sh"`
	if cmd != expected {
		t.Errorf("expected %q, got %q", expected, cmd)
	}
}

func TestRegisterHooks_DefaultsEvent(t *testing.T) {
	projectRoot := t.TempDir()
	settingsPath := filepath.Join(projectRoot, ".claude", "settings.json")

	// Hook with no explicit event should default to PostToolUse.
	exports := []manifest.Export{
		{Source: "hooks/check.sh", Type: "hook"},
	}

	if err := RegisterHooks(settingsPath, exports, ".cognitive-os/hooks/cos/my-pkg"); err != nil {
		t.Fatalf("RegisterHooks error: %v", err)
	}

	data, err := os.ReadFile(settingsPath)
	if err != nil {
		t.Fatal(err)
	}

	var settings map[string]interface{}
	if err := json.Unmarshal(data, &settings); err != nil {
		t.Fatal(err)
	}

	hooks := settings["hooks"].(map[string]interface{})
	if _, ok := hooks["PostToolUse"]; !ok {
		t.Error("expected default event PostToolUse")
	}
}

func TestRegisterHooks_NoHookExports(t *testing.T) {
	projectRoot := t.TempDir()
	settingsPath := filepath.Join(projectRoot, ".claude", "settings.json")

	// Non-hook exports should be ignored.
	exports := []manifest.Export{
		{Source: "SKILL.md", Type: "skill"},
		{Source: "rules/r.md", Type: "rule"},
	}

	if err := RegisterHooks(settingsPath, exports, ".cognitive-os/hooks/cos/my-pkg"); err != nil {
		t.Fatalf("RegisterHooks error: %v", err)
	}

	// Settings file should not be created since there are no hooks.
	if _, err := os.Stat(settingsPath); !os.IsNotExist(err) {
		t.Error("expected no settings.json when no hook exports")
	}
}

// ---------------------------------------------------------------------------
// Generate manifest tests
// ---------------------------------------------------------------------------

func TestGenerateManifest_DetectsSkills(t *testing.T) {
	dir := t.TempDir()
	writeTestFile(t, dir, "skills/my-skill/SKILL.md", "# Skill")

	m := generateManifest(dir)

	if len(m.Exports) == 0 {
		t.Fatal("expected at least one export")
	}

	found := false
	for _, e := range m.Exports {
		if e.Type == "skill" && strings.Contains(e.Source, "SKILL.md") {
			found = true
		}
	}
	if !found {
		t.Error("expected skill export to be detected")
	}
}

func TestGenerateManifest_DetectsRules(t *testing.T) {
	dir := t.TempDir()
	writeTestFile(t, dir, "rules/safety.md", "# Safety")

	m := generateManifest(dir)

	found := false
	for _, e := range m.Exports {
		if e.Type == "rule" {
			found = true
		}
	}
	if !found {
		t.Error("expected rule export to be detected")
	}
}

func TestGenerateManifest_DetectsHooks(t *testing.T) {
	dir := t.TempDir()
	writeTestFile(t, dir, "hooks/check.sh", "#!/bin/bash\necho ok")

	m := generateManifest(dir)

	found := false
	for _, e := range m.Exports {
		if e.Type == "hook" {
			found = true
			if e.HookEvent != "PostToolUse" {
				t.Errorf("expected default HookEvent 'PostToolUse', got %q", e.HookEvent)
			}
		}
	}
	if !found {
		t.Error("expected hook export to be detected")
	}
}

func TestGenerateManifest_DetectsTemplates(t *testing.T) {
	dir := t.TempDir()
	writeTestFile(t, dir, "templates/preamble.md", "# Preamble")

	m := generateManifest(dir)

	found := false
	for _, e := range m.Exports {
		if e.Type == "template" {
			found = true
		}
	}
	if !found {
		t.Error("expected template export to be detected")
	}
}

func TestGenerateManifest_EmptyDir(t *testing.T) {
	dir := t.TempDir()

	m := generateManifest(dir)

	if len(m.Exports) != 0 {
		t.Errorf("expected 0 exports for empty dir, got %d", len(m.Exports))
	}
	if m.Version != "0.0.0" {
		t.Errorf("expected version '0.0.0', got %q", m.Version)
	}
	if m.License != "UNKNOWN" {
		t.Errorf("expected license 'UNKNOWN', got %q", m.License)
	}
}

func TestGenerateManifest_DetectsRootSkill(t *testing.T) {
	dir := t.TempDir()
	writeTestFile(t, dir, "SKILL.md", "# Root Skill")

	m := generateManifest(dir)

	found := false
	for _, e := range m.Exports {
		if e.Type == "skill" && e.Source == "SKILL.md" {
			found = true
		}
	}
	if !found {
		t.Error("expected root SKILL.md to be detected")
	}
}

// ---------------------------------------------------------------------------
// Helper functions tests
// ---------------------------------------------------------------------------

func TestSourceTypeName(t *testing.T) {
	tests := []struct {
		input    resolver.SourceType
		expected string
	}{
		{resolver.SourceLocal, "local"},
		{resolver.SourceGitHub, "github"},
		{resolver.SourceURL, "url"},
		{resolver.SourceType(99), "unknown"},
	}

	for _, tt := range tests {
		got := sourceTypeName(tt.input)
		if got != tt.expected {
			t.Errorf("sourceTypeName(%d) = %q, want %q", tt.input, got, tt.expected)
		}
	}
}

func TestBuildLockedExports(t *testing.T) {
	targets := []ExportTarget{
		{
			Export: manifest.Export{
				Source:      "hooks/check.sh",
				Type:        "hook",
				HookEvent:   "PostToolUse",
				HookMatcher: "Bash",
			},
			Source: "/tmp/src/hooks/check.sh",
			Target: "/project/.cognitive-os/hooks/cos/pkg/check.sh",
		},
	}

	locked := buildLockedExports(targets)

	if len(locked) != 1 {
		t.Fatalf("expected 1 locked export, got %d", len(locked))
	}
	if locked[0].Source != "hooks/check.sh" {
		t.Errorf("expected source 'hooks/check.sh', got %q", locked[0].Source)
	}
	if locked[0].Type != "hook" {
		t.Errorf("expected type 'hook', got %q", locked[0].Type)
	}
	if locked[0].HookEvent != "PostToolUse" {
		t.Errorf("expected HookEvent 'PostToolUse', got %q", locked[0].HookEvent)
	}
	if locked[0].HookMatcher != "Bash" {
		t.Errorf("expected HookMatcher 'Bash', got %q", locked[0].HookMatcher)
	}
}

func TestDeriveProvides(t *testing.T) {
	exports := []manifest.Export{
		{Type: "skill"},
		{Type: "rule"},
		{Type: "skill"}, // duplicate
		{Type: "hook"},
	}

	provides := deriveProvides(exports)

	if len(provides) != 3 {
		t.Errorf("expected 3 unique provides, got %d: %v", len(provides), provides)
	}
}

func TestComputeManifestIntegrity(t *testing.T) {
	dir := t.TempDir()
	writeTestFile(t, dir, "cos-package.yaml", "name: test\nversion: 1.0.0")

	integrity := computeManifestIntegrity(dir)
	if !strings.HasPrefix(integrity, "sha256:") {
		t.Errorf("expected sha256: prefix, got %q", integrity)
	}
	if len(integrity) < 10 {
		t.Errorf("integrity hash too short: %q", integrity)
	}
}

func TestComputeManifestIntegrity_Missing(t *testing.T) {
	dir := t.TempDir()
	integrity := computeManifestIntegrity(dir)
	if integrity != "" {
		t.Errorf("expected empty integrity for missing manifest, got %q", integrity)
	}
}

// ---------------------------------------------------------------------------
// Skill path resolution edge cases
// ---------------------------------------------------------------------------

func TestResolveSkillTarget_TwoPartPath(t *testing.T) {
	// "skills/SKILL.md" (two parts) should use packageName.
	target := resolveSkillTarget("skills/SKILL.md", "/project", "my-pkg")
	expected := filepath.Join("/project", ".claude", "skills", "my-pkg", "SKILL.md")
	if target != expected {
		t.Errorf("expected %q, got %q", expected, target)
	}
}

func TestResolveSkillTarget_ThreePartPath(t *testing.T) {
	// "skills/deep-skill/SKILL.md" preserves directory.
	target := resolveSkillTarget("skills/deep-skill/SKILL.md", "/project", "my-pkg")
	expected := filepath.Join("/project", ".claude", "skills", "deep-skill", "SKILL.md")
	if target != expected {
		t.Errorf("expected %q, got %q", expected, target)
	}
}

func TestResolveSkillTarget_RootSkill(t *testing.T) {
	// "SKILL.md" at root uses packageName.
	target := resolveSkillTarget("SKILL.md", "/project", "my-pkg")
	expected := filepath.Join("/project", ".claude", "skills", "my-pkg", "SKILL.md")
	if target != expected {
		t.Errorf("expected %q, got %q", expected, target)
	}
}

// ---------------------------------------------------------------------------
// cos_version compatibility tests
// ---------------------------------------------------------------------------

func TestCheckCosVersionCompat_NoConstraint(t *testing.T) {
	m := &manifest.Manifest{Name: "test-pkg", Version: "1.0.0"}
	warn := CheckCosVersionCompat(m, t.TempDir())
	if warn != "" {
		t.Errorf("expected no warning for empty cos_version, got: %q", warn)
	}
}

func TestCheckCosVersionCompat_VersionFileMissing(t *testing.T) {
	m := &manifest.Manifest{Name: "test-pkg", Version: "1.0.0", CosVersion: ">=0.1.0"}
	warn := CheckCosVersionCompat(m, t.TempDir())
	if warn == "" {
		t.Error("expected warning when VERSION file is missing")
	}
	if !strings.Contains(warn, "VERSION file not found") {
		t.Errorf("expected 'VERSION file not found' in warning, got: %q", warn)
	}
}

func TestCheckCosVersionCompat_Compatible(t *testing.T) {
	dir := t.TempDir()
	writeTestFile(t, dir, "VERSION", "0.2.0")

	m := &manifest.Manifest{Name: "test-pkg", Version: "1.0.0", CosVersion: ">=0.1.0"}
	warn := CheckCosVersionCompat(m, dir)
	if warn != "" {
		t.Errorf("expected no warning for compatible version, got: %q", warn)
	}
}

func TestCheckCosVersionCompat_Incompatible(t *testing.T) {
	dir := t.TempDir()
	writeTestFile(t, dir, "VERSION", "0.1.0")

	m := &manifest.Manifest{Name: "test-pkg", Version: "1.0.0", CosVersion: ">=0.2.0"}
	warn := CheckCosVersionCompat(m, dir)
	if warn == "" {
		t.Error("expected warning for incompatible version")
	}
	if !strings.Contains(warn, "may not work correctly") {
		t.Errorf("expected 'may not work correctly' in warning, got: %q", warn)
	}
}

func TestCheckCosVersionCompat_ExactMatch(t *testing.T) {
	dir := t.TempDir()
	writeTestFile(t, dir, "VERSION", "1.0.0")

	m := &manifest.Manifest{Name: "test-pkg", Version: "1.0.0", CosVersion: "1.0.0"}
	warn := CheckCosVersionCompat(m, dir)
	if warn != "" {
		t.Errorf("expected no warning for exact match, got: %q", warn)
	}
}

func TestCheckCosVersionCompat_CaretConstraint(t *testing.T) {
	dir := t.TempDir()
	writeTestFile(t, dir, "VERSION", "0.1.5")

	m := &manifest.Manifest{Name: "test-pkg", Version: "1.0.0", CosVersion: "^0.1.0"}
	warn := CheckCosVersionCompat(m, dir)
	if warn != "" {
		t.Errorf("expected no warning for ^0.1.0 with 0.1.5, got: %q", warn)
	}
}

func TestCheckCosVersionCompat_CaretConstraintFail(t *testing.T) {
	dir := t.TempDir()
	writeTestFile(t, dir, "VERSION", "0.2.0")

	m := &manifest.Manifest{Name: "test-pkg", Version: "1.0.0", CosVersion: "^0.1.0"}
	warn := CheckCosVersionCompat(m, dir)
	if warn == "" {
		t.Error("expected warning for ^0.1.0 with 0.2.0")
	}
}

// ---------------------------------------------------------------------------
// Test helpers
// ---------------------------------------------------------------------------

func writeTestFile(t *testing.T, dir, name, content string) {
	t.Helper()
	path := filepath.Join(dir, name)
	if err := os.MkdirAll(filepath.Dir(path), 0755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(path, []byte(content), 0644); err != nil {
		t.Fatal(err)
	}
}
