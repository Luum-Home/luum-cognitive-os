package manifest

import (
	"os"
	"path/filepath"
	"testing"
)

func TestParseMinimalManifest(t *testing.T) {
	yaml := `
name: "@community/code-reviewer"
version: "1.0.0"
description: "Adversarial code review skill for pull requests"
authors:
  - "Jane Dev <jane@example.com>"
license: "MIT"
provides:
  - skill
exports:
  - source: "SKILL.md"
    type: skill
    description: "Review code with adversarial protocol"
`
	m, err := ParseBytes([]byte(yaml))
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	if m.Name != "@community/code-reviewer" {
		t.Errorf("name = %q, want %q", m.Name, "@community/code-reviewer")
	}
	if m.Version != "1.0.0" {
		t.Errorf("version = %q, want %q", m.Version, "1.0.0")
	}
	if m.License != "MIT" {
		t.Errorf("license = %q, want %q", m.License, "MIT")
	}
	if len(m.Authors) != 1 {
		t.Errorf("authors count = %d, want 1", len(m.Authors))
	}
	if len(m.Provides) != 1 || m.Provides[0] != "skill" {
		t.Errorf("provides = %v, want [skill]", m.Provides)
	}
	if len(m.Exports) != 1 {
		t.Errorf("exports count = %d, want 1", len(m.Exports))
	}
	if m.Exports[0].Source != "SKILL.md" {
		t.Errorf("exports[0].source = %q, want %q", m.Exports[0].Source, "SKILL.md")
	}
	if m.Exports[0].Type != "skill" {
		t.Errorf("exports[0].type = %q, want %q", m.Exports[0].Type, "skill")
	}
}

func TestParseFullManifest(t *testing.T) {
	yaml := `
name: "github.com/luum/safety-mesh"
version: "1.2.0"
description: "Complete safety mesh: hooks, rules, and review skill"
authors:
  - "Luum Team <team@luum.dev>"
license: "Apache-2.0"
repository: "https://github.com/luum/safety-mesh"
keywords:
  - "safety"
  - "guardrails"
  - "hooks"
cos_version: ">=0.1.0"
provides:
  - skill
  - rule
  - hook
exports:
  - source: "skills/safety-review/SKILL.md"
    type: skill
    description: "Safety-focused code review"
    triggers:
      - "security"
      - "safety review"
  - source: "rules/safety-gates.md"
    type: rule
    description: "Constitutional safety gates"
    always_active: true
  - source: "hooks/pre-safety-check.sh"
    type: hook
    hook_event: "PreToolUse"
    hook_matcher: "Agent"
    description: "Pre-execution safety validation"
  - source: "templates/safety-prompt.md"
    type: template
    description: "Safety-aware prompt template"
dependencies:
  "github.com/luum/core-rules":
    version: ">=1.0.0,<2.0.0"
    features:
      - "strict-mode"
  "@community/prompt-library":
    version: "^2.0.0"
groups:
  dev:
    "github.com/luum/test-helpers":
      version: ">=0.5.0"
features:
  strict-mode:
    default: false
    description: "Enable strict safety checks"
    exports:
      - source: "rules/strict-safety.md"
        type: rule
    dependencies:
      "github.com/luum/metrics-core":
        version: ">=1.0.0"
scripts:
  postinstall: "scripts/postinstall.sh"
  preuninstall: "scripts/preuninstall.sh"
  test: "scripts/test.sh"
platform:
  os:
    - linux
    - darwin
  shell: bash
  tools:
    - name: "jq"
      version: ">=1.6"
    - name: "git"
      version: ">=2.30"
  ide:
    - claude-code
publish:
  include:
    - "skills/**"
    - "rules/**"
  exclude:
    - "**/*_test.go"
  registry: "github"
  min_score: 40
`
	m, err := ParseBytes([]byte(yaml))
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	// Package identity.
	if m.Name != "github.com/luum/safety-mesh" {
		t.Errorf("name = %q, want %q", m.Name, "github.com/luum/safety-mesh")
	}
	if m.Version != "1.2.0" {
		t.Errorf("version = %q, want %q", m.Version, "1.2.0")
	}
	if m.Repository != "https://github.com/luum/safety-mesh" {
		t.Errorf("repository = %q", m.Repository)
	}
	if len(m.Keywords) != 3 {
		t.Errorf("keywords count = %d, want 3", len(m.Keywords))
	}
	if m.CosVersion != ">=0.1.0" {
		t.Errorf("cos_version = %q, want %q", m.CosVersion, ">=0.1.0")
	}

	// Exports.
	if len(m.Exports) != 4 {
		t.Fatalf("exports count = %d, want 4", len(m.Exports))
	}
	if m.Exports[2].HookEvent != "PreToolUse" {
		t.Errorf("exports[2].hook_event = %q, want %q", m.Exports[2].HookEvent, "PreToolUse")
	}
	if m.Exports[2].HookMatcher != "Agent" {
		t.Errorf("exports[2].hook_matcher = %q, want %q", m.Exports[2].HookMatcher, "Agent")
	}
	if !m.Exports[1].AlwaysActive {
		t.Errorf("exports[1].always_active = false, want true")
	}

	// Dependencies.
	if len(m.Dependencies) != 2 {
		t.Errorf("dependencies count = %d, want 2", len(m.Dependencies))
	}
	dep, ok := m.Dependencies["github.com/luum/core-rules"]
	if !ok {
		t.Fatal("dependency github.com/luum/core-rules not found")
	}
	if dep.Version != ">=1.0.0,<2.0.0" {
		t.Errorf("dependency version = %q", dep.Version)
	}
	if len(dep.Features) != 1 || dep.Features[0] != "strict-mode" {
		t.Errorf("dependency features = %v", dep.Features)
	}

	// Groups.
	if len(m.Groups) != 1 {
		t.Errorf("groups count = %d, want 1", len(m.Groups))
	}

	// Features.
	if len(m.Features) != 1 {
		t.Fatalf("features count = %d, want 1", len(m.Features))
	}
	feat, ok := m.Features["strict-mode"]
	if !ok {
		t.Fatal("feature strict-mode not found")
	}
	if feat.Default != false {
		t.Errorf("feature default = %v, want false", feat.Default)
	}
	if len(feat.Exports) != 1 {
		t.Errorf("feature exports count = %d, want 1", len(feat.Exports))
	}

	// Scripts.
	if len(m.Scripts) != 3 {
		t.Errorf("scripts count = %d, want 3", len(m.Scripts))
	}

	// Platform.
	if m.Platform == nil {
		t.Fatal("platform is nil")
	}
	if len(m.Platform.OS) != 2 {
		t.Errorf("platform.os count = %d, want 2", len(m.Platform.OS))
	}
	if m.Platform.Shell != "bash" {
		t.Errorf("platform.shell = %q, want %q", m.Platform.Shell, "bash")
	}
	if len(m.Platform.Tools) != 2 {
		t.Errorf("platform.tools count = %d, want 2", len(m.Platform.Tools))
	}

	// Publish.
	if m.Publish == nil {
		t.Fatal("publish is nil")
	}
	if len(m.Publish.Include) != 2 {
		t.Errorf("publish.include count = %d, want 2", len(m.Publish.Include))
	}
	if m.Publish.MinScore == nil || *m.Publish.MinScore != 40 {
		t.Errorf("publish.min_score unexpected")
	}
}

func TestParseInvalidYAML(t *testing.T) {
	data := []byte(`
name: "test
  invalid: yaml
  - broken
`)
	_, err := ParseBytes(data)
	if err == nil {
		t.Fatal("expected error for invalid YAML, got nil")
	}
}

func TestParseMissingFile(t *testing.T) {
	_, err := ParseFile(filepath.Join(os.TempDir(), "nonexistent-cos-package-12345.yaml"))
	if err == nil {
		t.Fatal("expected error for missing file, got nil")
	}
}
