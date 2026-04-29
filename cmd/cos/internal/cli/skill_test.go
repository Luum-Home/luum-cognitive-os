package cli

import (
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func copyGovernedSkillRuntime(t *testing.T, projectDir string) {
	t.Helper()
	sourceRoot, err := filepath.Abs(filepath.Join("..", "..", "..", ".."))
	if err != nil {
		t.Fatal(err)
	}
	files := map[string]string{
		filepath.Join("scripts", "cos-governed-self-improvement.py"): filepath.Join("scripts", "cos-governed-self-improvement.py"),
		filepath.Join("lib", "governed_self_improvement.py"):         filepath.Join("lib", "governed_self_improvement.py"),
	}
	for srcRel, dstRel := range files {
		data, err := os.ReadFile(filepath.Join(sourceRoot, srcRel))
		if err != nil {
			t.Fatal(err)
		}
		dst := filepath.Join(projectDir, dstRel)
		if err := os.MkdirAll(filepath.Dir(dst), 0755); err != nil {
			t.Fatal(err)
		}
		if err := os.WriteFile(dst, data, 0755); err != nil {
			t.Fatal(err)
		}
	}
}

func writeSkillJSONL(t *testing.T, projectDir string, name string, rows []map[string]any) {
	t.Helper()
	path := filepath.Join(projectDir, ".cognitive-os", "metrics", name)
	if err := os.MkdirAll(filepath.Dir(path), 0755); err != nil {
		t.Fatal(err)
	}
	var b strings.Builder
	for _, row := range rows {
		data, err := json.Marshal(row)
		if err != nil {
			t.Fatal(err)
		}
		b.Write(data)
		b.WriteString("\n")
	}
	if err := os.WriteFile(path, []byte(b.String()), 0644); err != nil {
		t.Fatal(err)
	}
}

func TestE2E_SkillSuggestDraftPromote(t *testing.T) {
	projectDir := createTestProject(t)
	copyGovernedSkillRuntime(t, projectDir)
	writeSkillJSONL(t, projectDir, "error-learning.jsonl", []map[string]any{
		{"type": "TEST_FAILURE", "service": "checkout"},
		{"type": "TEST_FAILURE", "service": "checkout"},
		{"type": "TEST_FAILURE", "service": "checkout"},
	})

	out, code := runCos(t, projectDir, "skill", "suggest")
	if code != 0 {
		t.Fatalf("cos skill suggest failed (%d): %s", code, out)
	}
	if !strings.Contains(out, "repair-test-failure-checkout") {
		t.Fatalf("expected signal slug in suggest output, got: %s", out)
	}

	out, code = runCos(t, projectDir, "skill", "draft", "repair-test-failure-checkout")
	if code != 0 {
		t.Fatalf("cos skill draft failed (%d): %s", code, out)
	}
	if !strings.Contains(out, `"status": "draft"`) {
		t.Fatalf("expected draft status, got: %s", out)
	}

	out, code = runCos(t, projectDir, "skill", "promote", "repair-test-failure-checkout")
	if code == 0 {
		t.Fatalf("promotion without approval should fail, got output: %s", out)
	}
	if !strings.Contains(out, "promotion requires") {
		t.Fatalf("expected approval error, got: %s", out)
	}

	out, code = runCos(t, projectDir, "skill", "promote", "repair-test-failure-checkout", "--approved-by", "go-test")
	if code != 0 {
		t.Fatalf("approved promotion failed (%d): %s", code, out)
	}
	promotedSkill := filepath.Join(projectDir, ".cognitive-os", "skills", "cos", "repair-test-failure-checkout", "SKILL.md")
	if _, err := os.Stat(promotedSkill); err != nil {
		t.Fatalf("expected promoted skill at %s: %v", promotedSkill, err)
	}
	rootSkill := filepath.Join(projectDir, "skills", "repair-test-failure-checkout", "SKILL.md")
	if _, err := os.Stat(rootSkill); !os.IsNotExist(err) {
		t.Fatalf("promotion must not write root skills path: %s", rootSkill)
	}
}
