package wizard

import (
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestRecommendGoProject(t *testing.T) {
	dir := t.TempDir()
	os.WriteFile(filepath.Join(dir, "go.mod"), []byte("module example.com/app\n\ngo 1.22\n"), 0644)

	env := Detect(dir)
	recs := RecommendSkills(env, dir)

	found := false
	for _, r := range recs {
		if r.Name == "go-testing" {
			found = true
			if r.Priority != "recommended" {
				t.Errorf("expected go-testing priority 'recommended', got %q", r.Priority)
			}
			if r.Source != "cos-builtin" {
				t.Errorf("expected go-testing source 'cos-builtin', got %q", r.Source)
			}
			break
		}
	}
	if !found {
		t.Error("expected go-testing skill in recommendations for Go project")
	}
}

func TestRecommendTypeScriptProject(t *testing.T) {
	dir := t.TempDir()
	os.WriteFile(filepath.Join(dir, "package.json"), []byte(`{"name":"app"}`), 0644)
	os.WriteFile(filepath.Join(dir, "tsconfig.json"), []byte(`{}`), 0644)

	env := Detect(dir)
	recs := RecommendSkills(env, dir)

	found := false
	for _, r := range recs {
		if r.Name == "typescript-patterns" {
			found = true
			if r.Priority != "recommended" {
				t.Errorf("expected typescript-patterns priority 'recommended', got %q", r.Priority)
			}
			break
		}
	}
	if !found {
		t.Error("expected typescript-patterns skill in recommendations for TypeScript project")
	}
}

func TestRecommendPythonProject(t *testing.T) {
	dir := t.TempDir()
	os.WriteFile(filepath.Join(dir, "pyproject.toml"), []byte("[project]\nname = \"app\"\n"), 0644)

	env := Detect(dir)
	recs := RecommendSkills(env, dir)

	found := false
	for _, r := range recs {
		if r.Name == "python-testing" {
			found = true
			if r.Priority != "recommended" {
				t.Errorf("expected python-testing priority 'recommended', got %q", r.Priority)
			}
			break
		}
	}
	if !found {
		t.Error("expected python-testing skill in recommendations for Python project")
	}
}

func TestAlwaysRecommendsUniversal(t *testing.T) {
	dir := t.TempDir()
	// Even an empty project should get universal skills.
	env := Detect(dir)
	recs := RecommendSkills(env, dir)

	expected := map[string]bool{
		"run-tests":   false,
		"code-review": false,
		"scout":       false,
	}

	for _, r := range recs {
		if _, ok := expected[r.Name]; ok {
			expected[r.Name] = true
		}
	}

	for name, found := range expected {
		if !found {
			t.Errorf("expected universal skill %q in recommendations", name)
		}
	}
}

func TestDetectFrameworkNextjs(t *testing.T) {
	dir := t.TempDir()
	os.WriteFile(filepath.Join(dir, "package.json"), []byte(`{"name":"app"}`), 0644)
	os.WriteFile(filepath.Join(dir, "next.config.js"), []byte("module.exports = {}"), 0644)

	env := Detect(dir)
	recs := RecommendSkills(env, dir)

	found := false
	for _, r := range recs {
		if r.Name == "nextjs" {
			found = true
			if r.Reason != "Next.js config found" {
				t.Errorf("expected reason 'Next.js config found', got %q", r.Reason)
			}
			break
		}
	}
	if !found {
		t.Error("expected nextjs skill when next.config.js is present")
	}
}

func TestDetectFrameworkDocker(t *testing.T) {
	dir := t.TempDir()
	os.WriteFile(filepath.Join(dir, "Dockerfile"), []byte("FROM alpine"), 0644)

	env := Detect(dir)
	recs := RecommendSkills(env, dir)

	found := false
	for _, r := range recs {
		if r.Name == "docker" {
			found = true
			break
		}
	}
	if !found {
		t.Error("expected docker skill when Dockerfile is present")
	}
}

func TestDetectFrameworkPrisma(t *testing.T) {
	dir := t.TempDir()
	os.WriteFile(filepath.Join(dir, "package.json"), []byte(`{"name":"app"}`), 0644)
	os.MkdirAll(filepath.Join(dir, "prisma"), 0755)
	os.WriteFile(filepath.Join(dir, "prisma", "schema.prisma"), []byte("generator client {}"), 0644)

	env := Detect(dir)
	recs := RecommendSkills(env, dir)

	found := false
	for _, r := range recs {
		if r.Name == "prisma" {
			found = true
			if r.Priority != "recommended" {
				t.Errorf("expected prisma priority 'recommended', got %q", r.Priority)
			}
			break
		}
	}
	if !found {
		t.Error("expected prisma skill when prisma/schema.prisma is present")
	}
}

func TestDetectFrameworkTailwind(t *testing.T) {
	dir := t.TempDir()
	os.WriteFile(filepath.Join(dir, "package.json"), []byte(`{"name":"app"}`), 0644)
	os.WriteFile(filepath.Join(dir, "tailwind.config.js"), []byte("module.exports = {}"), 0644)

	env := Detect(dir)
	recs := RecommendSkills(env, dir)

	found := false
	for _, r := range recs {
		if r.Name == "tailwind" {
			found = true
			break
		}
	}
	if !found {
		t.Error("expected tailwind skill when tailwind.config.js is present")
	}
}

func TestDetectFrameworkGitHubActions(t *testing.T) {
	dir := t.TempDir()
	os.MkdirAll(filepath.Join(dir, ".github", "workflows"), 0755)

	env := Detect(dir)
	recs := RecommendSkills(env, dir)

	found := false
	for _, r := range recs {
		if r.Name == "github-actions" {
			found = true
			break
		}
	}
	if !found {
		t.Error("expected github-actions skill when .github/workflows/ exists")
	}
}

func TestDetectSupabaseFromEnv(t *testing.T) {
	dir := t.TempDir()
	os.WriteFile(filepath.Join(dir, ".env"), []byte("SUPABASE_URL=https://foo.supabase.co\nSUPABASE_KEY=abc\n"), 0644)

	env := Detect(dir)
	recs := RecommendSkills(env, dir)

	found := false
	for _, r := range recs {
		if r.Name == "supabase" {
			found = true
			break
		}
	}
	if !found {
		t.Error("expected supabase skill when .env contains SUPABASE_URL")
	}
}

func TestFormatRecommendations(t *testing.T) {
	recs := []SkillRecommendation{
		{Name: "go-testing", Reason: "Go project detected", Source: "cos-builtin", InstallCmd: "/go-testing", Priority: "recommended"},
		{Name: "docker", Reason: "Dockerfile found", Source: "skills.sh", InstallCmd: "npx skills add docker", Priority: "optional"},
		{Name: "run-tests", Reason: "Universal test runner", Source: "cos-builtin", InstallCmd: "/run-tests", Priority: "recommended"},
	}

	output := FormatRecommendations(recs)

	if !strings.Contains(output, "Recommended skills:") {
		t.Error("expected header in formatted output")
	}
	if !strings.Contains(output, "go-testing") {
		t.Error("expected go-testing in formatted output")
	}
	if !strings.Contains(output, "docker") {
		t.Error("expected docker in formatted output")
	}
	if !strings.Contains(output, "run-tests") {
		t.Error("expected run-tests in formatted output")
	}
	// External skills should show install command.
	if !strings.Contains(output, "npx skills add docker") {
		t.Error("expected install command for external skill")
	}

	// Recommended items should appear before optional items.
	goIdx := strings.Index(output, "go-testing")
	dockerIdx := strings.Index(output, "docker")
	if goIdx > dockerIdx {
		t.Error("expected recommended skills (go-testing) to appear before optional skills (docker)")
	}
}

func TestFormatRecommendationsEmpty(t *testing.T) {
	output := FormatRecommendations(nil)
	if output != "" {
		t.Errorf("expected empty string for nil recs, got %q", output)
	}
}

func TestEmptyProject(t *testing.T) {
	dir := t.TempDir()
	env := Detect(dir)
	recs := RecommendSkills(env, dir)

	// Should still have universal skills but no language-specific ones.
	for _, r := range recs {
		if r.Name == "go-testing" || r.Name == "typescript-patterns" || r.Name == "python-testing" {
			t.Errorf("did not expect language-specific skill %q for empty project", r.Name)
		}
	}

	// Universal skills should be present.
	hasRunTests := false
	hasCodeReview := false
	for _, r := range recs {
		if r.Name == "run-tests" {
			hasRunTests = true
		}
		if r.Name == "code-review" {
			hasCodeReview = true
		}
	}
	if !hasRunTests {
		t.Error("expected run-tests for empty project")
	}
	if !hasCodeReview {
		t.Error("expected code-review for empty project")
	}
}

func TestDeduplicateGitHubActions(t *testing.T) {
	// When both CI detection and framework detection find github-actions,
	// it should appear only once.
	dir := t.TempDir()
	os.MkdirAll(filepath.Join(dir, ".github", "workflows"), 0755)

	env := Detect(dir)
	recs := RecommendSkills(env, dir)

	count := 0
	for _, r := range recs {
		if r.Name == "github-actions" {
			count++
		}
	}
	if count != 1 {
		t.Errorf("expected exactly 1 github-actions recommendation, got %d", count)
	}
}

func TestFormatSkillRecommendationsTUI(t *testing.T) {
	recs := []SkillRecommendation{
		{Name: "go-testing", Reason: "Go project detected", Source: "cos-builtin", InstallCmd: "/go-testing", Priority: "recommended"},
		{Name: "docker", Reason: "Dockerfile found", Source: "skills.sh", InstallCmd: "npx skills add docker", Priority: "optional"},
	}

	output := FormatSkillRecommendations(recs)

	if !strings.Contains(output, "Skill Recommendations") {
		t.Error("expected TUI header in output")
	}
	if !strings.Contains(output, "go-testing") {
		t.Error("expected go-testing in TUI output")
	}
	if !strings.Contains(output, "docker") {
		t.Error("expected docker in TUI output")
	}
}

func TestDetectFrameworkDockerCompose(t *testing.T) {
	dir := t.TempDir()
	os.WriteFile(filepath.Join(dir, "docker-compose.yml"), []byte("version: '3'"), 0644)

	env := Detect(dir)
	recs := RecommendSkills(env, dir)

	found := false
	for _, r := range recs {
		if r.Name == "docker-compose" {
			found = true
			break
		}
	}
	if !found {
		t.Error("expected docker-compose skill when docker-compose.yml is present")
	}
}

func TestDetectFrameworkAngular(t *testing.T) {
	dir := t.TempDir()
	os.WriteFile(filepath.Join(dir, "angular.json"), []byte("{}"), 0644)

	env := Detect(dir)
	recs := RecommendSkills(env, dir)

	found := false
	for _, r := range recs {
		if r.Name == "angular" {
			found = true
			if r.Priority != "recommended" {
				t.Errorf("expected angular priority 'recommended', got %q", r.Priority)
			}
			break
		}
	}
	if !found {
		t.Error("expected angular skill when angular.json is present")
	}
}
