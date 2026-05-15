package cli

import (
	"strings"
	"testing"
)

func TestInstallPrimitivePlanSkillForCursor(t *testing.T) {
	dir := createTestProject(t)
	writeTestFileE2E(t, dir, ".cognitive-os/skills/cos/cos-status/SKILL.md", "---\nname: cos-status\n---\n")

	out, code := runCos(t, dir, "install", "primitive", "skill/cos-status", "--harness", "cursor")
	if code != 0 {
		t.Fatalf("expected exit 0, got %d\n%s", code, out)
	}
	for _, want := range []string{
		"Primitive projection plan",
		"primitive:        skill/cos-status",
		"harness:          cursor",
		"projection_path:  .cursor/rules/cognitive-os.mdc",
		"proof_level:      structural-advisory",
	} {
		if !strings.Contains(out, want) {
			t.Fatalf("expected output to contain %q\n%s", want, out)
		}
	}
}

func TestInstallProfilePlanShowsUnregisteredProfile(t *testing.T) {
	dir := createTestProject(t)

	out, code := runCos(t, dir, "install", "profile", "sre", "--harness", "claude")
	if code != 0 {
		t.Fatalf("expected exit 0 for plan-only unregistered profile, got %d\n%s", code, out)
	}
	if !strings.Contains(out, "registered:      false") {
		t.Fatalf("expected unregistered profile plan\n%s", out)
	}
	if !strings.Contains(out, "manifests/primitive-projection-profiles.yaml") {
		t.Fatalf("expected manifest guidance\n%s", out)
	}
}

func TestProjectPlanRejectsPlannedButUnsupportedWindsurf(t *testing.T) {
	dir := createTestProject(t)

	out, code := runCos(t, dir, "project", "--harness", "windsurf")
	if code == 0 {
		t.Fatalf("expected non-zero for unsupported windsurf\n%s", out)
	}
	if !strings.Contains(out, "unsupported harness \"windsurf\"") {
		t.Fatalf("expected unsupported harness message\n%s", out)
	}
}

func TestProjectPlanForCursor(t *testing.T) {
	dir := createTestProject(t)

	out, code := runCos(t, dir, "project", "--harness", "cursor")
	if code != 0 {
		t.Fatalf("expected exit 0, got %d\n%s", code, out)
	}
	for _, want := range []string{
		"Project projection plan",
		"profile:         default",
		"harness:         cursor",
		"command:         python3 scripts/cos_init.py --default --harness cursor",
	} {
		if !strings.Contains(out, want) {
			t.Fatalf("expected output to contain %q\n%s", want, out)
		}
	}
}
