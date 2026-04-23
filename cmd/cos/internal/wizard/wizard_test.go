package wizard

import (
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestApplyPresetSoloDev(t *testing.T) {
	env := DetectedEnv{ProjectName: "test"}
	cfg := ApplyPreset(PresetSoloDev, env)

	if cfg.Profile != ProfileMinimal {
		t.Errorf("solo-dev preset: expected minimal profile, got %s", cfg.Profile)
	}
	if cfg.Phase != PhaseReconstruction {
		t.Errorf("solo-dev preset: expected reconstruction phase, got %s", cfg.Phase)
	}
	if !cfg.Features.Engram {
		t.Error("solo-dev preset: expected Engram enabled")
	}
	if cfg.Features.AgentTeams {
		t.Error("solo-dev preset: expected AgentTeams disabled")
	}
	if !cfg.Proceed {
		t.Error("solo-dev preset: expected Proceed=true")
	}
}

func TestApplyPresetTeam(t *testing.T) {
	env := DetectedEnv{ProjectName: "test"}
	cfg := ApplyPreset(PresetTeam, env)

	if cfg.Profile != ProfileStandard {
		t.Errorf("team preset: expected standard profile, got %s", cfg.Profile)
	}
	if cfg.Phase != PhaseStabilization {
		t.Errorf("team preset: expected stabilization phase, got %s", cfg.Phase)
	}
	if !cfg.Features.AutoSkills {
		t.Error("team preset: expected AutoSkills enabled")
	}
}

func TestApplyPresetEnterprise(t *testing.T) {
	env := DetectedEnv{ProjectName: "test"}
	cfg := ApplyPreset(PresetEnterprise, env)

	if cfg.Profile != ProfileParanoid {
		t.Errorf("enterprise preset: expected paranoid profile, got %s", cfg.Profile)
	}
	if cfg.Phase != PhaseProduction {
		t.Errorf("enterprise preset: expected production phase, got %s", cfg.Phase)
	}
	if !cfg.Features.AgentTeams {
		t.Error("enterprise preset: expected AgentTeams enabled")
	}
}

func TestDefaultConfigUsesTeamPreset(t *testing.T) {
	env := DetectedEnv{ProjectName: "test"}
	cfg := DefaultConfig(env)

	if cfg.Profile != ProfileStandard {
		t.Errorf("default config: expected standard profile, got %s", cfg.Profile)
	}
	if cfg.Phase != PhaseStabilization {
		t.Errorf("default config: expected stabilization phase, got %s", cfg.Phase)
	}
}

func TestFormatSummaryContainsProfile(t *testing.T) {
	cfg := SetupConfig{
		Env:     DetectedEnv{ProjectName: "test"},
		Profile: ProfileStandard,
		Phase:   PhaseStabilization,
		Features: Features{
			Engram:     true,
			AutoSkills: true,
			SmartRead:  true,
		},
	}

	summary := FormatSummary(cfg)

	checks := []string{
		"Standard",
		"stabilization",
		"Engram",
		"Auto-skills",
		"Smart reader",
	}

	for _, check := range checks {
		if !strings.Contains(summary, check) {
			t.Errorf("FormatSummary missing %q.\nGot:\n%s", check, summary)
		}
	}
}

func TestFormatSummaryMinimalProfile(t *testing.T) {
	cfg := SetupConfig{
		Env:     DetectedEnv{ProjectName: "test"},
		Profile: ProfileMinimal,
		Phase:   PhaseReconstruction,
		Features: Features{
			Engram: true,
		},
	}

	summary := FormatSummary(cfg)
	if !strings.Contains(summary, "Minimal") {
		t.Errorf("expected 'Minimal' in summary, got:\n%s", summary)
	}
	if !strings.Contains(summary, "reconstruction") {
		t.Errorf("expected 'reconstruction' in summary, got:\n%s", summary)
	}
}

func TestWriteCognitiveOSYaml(t *testing.T) {
	dir := t.TempDir()
	path := filepath.Join(dir, "cognitive-os.yaml")

	cfg := SetupConfig{
		Env:     DetectedEnv{ProjectName: "my-project"},
		Profile: ProfileStandard,
		Phase:   PhaseStabilization,
		Features: Features{
			Engram:     true,
			AutoSkills: true,
			AgentTeams: false,
			SmartRead:  true,
		},
	}

	err := writeCognitiveOSYaml(path, cfg)
	if err != nil {
		t.Fatalf("writeCognitiveOSYaml: %v", err)
	}

	content, err := os.ReadFile(path)
	if err != nil {
		t.Fatal(err)
	}

	s := string(content)
	checks := []struct {
		label string
		want  string
	}{
		{"project name", "name: my-project"},
		{"phase", "phase: stabilization"},
		{"profile", "profile: standard"},
		{"engram", "engram: true"},
		{"auto_skills", "auto_skills: true"},
		{"agent_teams", "agent_teams: false"},
		{"smart_reader", "smart_reader: true"},
	}

	for _, c := range checks {
		if !strings.Contains(s, c.want) {
			t.Errorf("cognitive-os.yaml missing %s (%q).\nGot:\n%s", c.label, c.want, s)
		}
	}
}

func TestWriteSettingsJSON(t *testing.T) {
	dir := t.TempDir()
	path := filepath.Join(dir, "settings.json")

	cfg := SetupConfig{
		Profile: ProfileStandard,
	}

	err := writeSettingsJSON(path, cfg)
	if err != nil {
		t.Fatalf("writeSettingsJSON: %v", err)
	}

	content, err := os.ReadFile(path)
	if err != nil {
		t.Fatal(err)
	}

	if !strings.Contains(string(content), "permissions") {
		t.Errorf("settings.json missing 'permissions' key.\nGot:\n%s", content)
	}
}

func TestCountInstalledRules(t *testing.T) {
	dir := t.TempDir()
	rulesDir := filepath.Join(dir, ".claude", "rules")
	os.MkdirAll(rulesDir, 0755)

	// Create some rule files.
	for _, name := range []string{"rule-a.md", "rule-b.md", "rule-c.md"} {
		os.WriteFile(filepath.Join(rulesDir, name), []byte("# Rule"), 0644)
	}

	count := countInstalledRules(dir)
	if count != 3 {
		t.Errorf("expected 3 installed rules, got %d", count)
	}
}

func TestCountRegisteredHooks(t *testing.T) {
	dir := t.TempDir()
	os.MkdirAll(filepath.Join(dir, ".claude"), 0755)

	settingsContent := `{
  "hooks": {
    "PreToolUse": [
      {"command": "bash hooks/secret-detector.sh"},
      {"command": "bash hooks/rate-limiter.sh"}
    ],
    "PostToolUse": [
      {"command": "bash hooks/error-learning.sh"}
    ]
  }
}`
	os.WriteFile(filepath.Join(dir, ".claude", "settings.json"), []byte(settingsContent), 0644)

	count := countRegisteredHooks(dir, filepath.Join(".claude", "settings.json"))
	if count != 3 {
		t.Errorf("expected 3 registered hooks, got %d", count)
	}
}

func TestApplyProfileFilterStandard(t *testing.T) {
	dir := t.TempDir()
	cosRulesDir := filepath.Join(dir, ".claude", "rules", "cos")
	os.MkdirAll(cosRulesDir, 0755)

	// Create 20 rule files: the 14 core + 6 extras.
	allRules := []string{
		"RULES-COMPACT.md", "adaptive-bypass.md", "acceptance-criteria.md",
		"agent-quality.md", "trust-score.md", "definition-of-done.md",
		"phase-aware-agents.md", "closed-loop-prompts.md", "token-economy.md",
		"responsiveness.md", "agent-security.md", "credential-management.md",
		"content-policy.md", "error-learning.md",
		// extras that should be removed
		"blast-radius.md", "sandbox-sampling.md", "scout-pattern.md",
		"cognitive-load.md", "model-routing.md", "rate-limiting.md",
	}
	for _, name := range allRules {
		os.WriteFile(filepath.Join(cosRulesDir, name), []byte("# Rule"), 0644)
	}

	err := applyProfileFilter(dir, "standard")
	if err != nil {
		t.Fatalf("applyProfileFilter(standard): %v", err)
	}

	remaining, _ := os.ReadDir(cosRulesDir)
	if len(remaining) != 14 {
		names := make([]string, len(remaining))
		for i, e := range remaining {
			names[i] = e.Name()
		}
		t.Errorf("expected 14 rules after standard filter, got %d: %v", len(remaining), names)
	}

	// Verify all core rules still exist.
	for name := range coreRules {
		if _, err := os.Stat(filepath.Join(cosRulesDir, name)); os.IsNotExist(err) {
			t.Errorf("core rule %s was removed by standard filter", name)
		}
	}
}

func TestApplyProfileFilterMinimal(t *testing.T) {
	dir := t.TempDir()
	cosRulesDir := filepath.Join(dir, ".claude", "rules", "cos")
	os.MkdirAll(cosRulesDir, 0755)

	// Create 20 rule files.
	rules := []string{
		"RULES-COMPACT.md", "adaptive-bypass.md", "acceptance-criteria.md",
		"agent-quality.md", "trust-score.md", "definition-of-done.md",
		"phase-aware-agents.md", "closed-loop-prompts.md", "token-economy.md",
		"responsiveness.md", "agent-security.md", "credential-management.md",
		"content-policy.md", "error-learning.md",
		"blast-radius.md", "sandbox-sampling.md", "scout-pattern.md",
		"cognitive-load.md", "model-routing.md", "rate-limiting.md",
	}
	for _, name := range rules {
		os.WriteFile(filepath.Join(cosRulesDir, name), []byte("# Rule"), 0644)
	}

	err := applyProfileFilter(dir, "minimal")
	if err != nil {
		t.Fatalf("applyProfileFilter(minimal): %v", err)
	}

	remaining, _ := os.ReadDir(cosRulesDir)
	if len(remaining) != 1 {
		names := make([]string, len(remaining))
		for i, e := range remaining {
			names[i] = e.Name()
		}
		t.Errorf("expected 1 rule after minimal filter, got %d: %v", len(remaining), names)
	}

	// Only RULES-COMPACT.md should remain.
	if _, err := os.Stat(filepath.Join(cosRulesDir, "RULES-COMPACT.md")); os.IsNotExist(err) {
		t.Error("RULES-COMPACT.md was removed by minimal filter")
	}
}

func TestApplyProfileFilterFull(t *testing.T) {
	dir := t.TempDir()
	cosRulesDir := filepath.Join(dir, ".claude", "rules", "cos")
	os.MkdirAll(cosRulesDir, 0755)

	// Create 20 rule files.
	rules := []string{
		"RULES-COMPACT.md", "adaptive-bypass.md", "acceptance-criteria.md",
		"agent-quality.md", "trust-score.md", "definition-of-done.md",
		"phase-aware-agents.md", "closed-loop-prompts.md", "token-economy.md",
		"responsiveness.md", "agent-security.md", "credential-management.md",
		"content-policy.md", "error-learning.md",
		"blast-radius.md", "sandbox-sampling.md", "scout-pattern.md",
		"cognitive-load.md", "model-routing.md", "rate-limiting.md",
	}
	for _, name := range rules {
		os.WriteFile(filepath.Join(cosRulesDir, name), []byte("# Rule"), 0644)
	}

	err := applyProfileFilter(dir, "paranoid")
	if err != nil {
		t.Fatalf("applyProfileFilter(paranoid): %v", err)
	}

	remaining, _ := os.ReadDir(cosRulesDir)
	if len(remaining) != 20 {
		t.Errorf("expected 20 rules after paranoid filter (no change), got %d", len(remaining))
	}
}

func TestApplyProfileFilterEmptyDir(t *testing.T) {
	dir := t.TempDir()
	// No .claude/rules/cos/ directory exists.

	err := applyProfileFilter(dir, "standard")
	if err != nil {
		t.Errorf("applyProfileFilter on empty dir should not error, got: %v", err)
	}
}

func TestIsTTY(t *testing.T) {
	// In test environment, stdout is typically not a TTY.
	// Just verify it doesn't panic.
	_ = IsTTY()
}
