package wizard

import (
	"fmt"
	"os"
	"path/filepath"
	"strings"

	"github.com/charmbracelet/lipgloss"
)

// SkillRecommendation represents a suggested skill for the detected stack.
type SkillRecommendation struct {
	Name       string // e.g., "go-testing"
	Reason     string // e.g., "Go project detected"
	Source     string // "cos-builtin" | "skills.sh" | "community"
	InstallCmd string // e.g., "npx skills add go" or "/go-testing"
	Priority   string // "recommended" | "optional" | "suggested"
}

// RecommendSkills returns skill recommendations based on detected environment.
// It combines language-based, framework-based, and universal recommendations.
// This is a pure Go implementation — no Python dependency.
func RecommendSkills(env DetectedEnv, projectDir string) []SkillRecommendation {
	var recs []SkillRecommendation

	// Language-based recommendations.
	recs = append(recs, recommendLanguageSkills(env)...)

	// Framework detection from project files.
	recs = append(recs, detectFrameworkSkills(projectDir)...)

	// CI/CD recommendations.
	recs = append(recs, recommendCISkills(env)...)

	// COS universal skills (always recommended).
	recs = append(recs, universalSkills()...)

	// Deduplicate by name (framework detection may overlap with CI detection).
	return deduplicateSkills(recs)
}

func recommendLanguageSkills(env DetectedEnv) []SkillRecommendation {
	switch env.Language {
	case "go":
		return []SkillRecommendation{
			{
				Name: "go-testing", Reason: "Go project detected",
				Source: "cos-builtin", InstallCmd: "/go-testing", Priority: "recommended",
			},
		}
	case "typescript":
		return []SkillRecommendation{
			{
				Name: "typescript-patterns", Reason: "TypeScript project detected",
				Source: "skills.sh", InstallCmd: "npx skills add typescript", Priority: "recommended",
			},
		}
	case "python":
		return []SkillRecommendation{
			{
				Name: "python-testing", Reason: "Python project detected",
				Source: "skills.sh", InstallCmd: "npx skills add python", Priority: "recommended",
			},
		}
	case "rust":
		return []SkillRecommendation{
			{
				Name: "rust-patterns", Reason: "Rust project detected",
				Source: "skills.sh", InstallCmd: "npx skills add rust", Priority: "optional",
			},
		}
	case "java":
		return []SkillRecommendation{
			{
				Name: "java-patterns", Reason: "Java project detected",
				Source: "skills.sh", InstallCmd: "npx skills add java", Priority: "optional",
			},
		}
	}
	return nil
}

func recommendCISkills(env DetectedEnv) []SkillRecommendation {
	switch env.CISystem {
	case "GitHub Actions":
		return []SkillRecommendation{
			{
				Name: "github-actions", Reason: "GitHub Actions CI detected",
				Source: "skills.sh", InstallCmd: "npx skills add github-actions", Priority: "optional",
			},
		}
	}
	return nil
}

func universalSkills() []SkillRecommendation {
	return []SkillRecommendation{
		{Name: "run-tests", Reason: "Universal test runner", Source: "cos-builtin", InstallCmd: "/run-tests", Priority: "recommended"},
		{Name: "code-review", Reason: "Code review with memory", Source: "cos-builtin", InstallCmd: "/code-review", Priority: "recommended"},
		{Name: "scout", Reason: "Pre-implementation reconnaissance", Source: "cos-builtin", InstallCmd: "/scout", Priority: "optional"},
	}
}

// frameworkMarker maps a file presence to a framework skill recommendation.
type frameworkMarker struct {
	// files is a list of filenames to check for existence.
	files []string
	// dirCheck is a directory to look for (optional).
	dirCheck string
	// envCheck is an env var prefix to look for in .env files (optional).
	envCheck string
	// rec is the skill recommendation to emit if the marker is found.
	rec SkillRecommendation
}

// detectFrameworkSkills scans the project directory for framework config files
// and returns matching skill recommendations.
func detectFrameworkSkills(projectDir string) []SkillRecommendation {
	if projectDir == "" {
		return nil
	}

	markers := []frameworkMarker{
		{
			files: []string{"next.config.js", "next.config.ts", "next.config.mjs"},
			rec: SkillRecommendation{
				Name: "nextjs", Reason: "Next.js config found",
				Source: "skills.sh", InstallCmd: "npx skills add nextjs", Priority: "recommended",
			},
		},
		{
			files: []string{"tailwind.config.js", "tailwind.config.ts", "tailwind.config.mjs"},
			rec: SkillRecommendation{
				Name: "tailwind", Reason: "Tailwind CSS config found",
				Source: "skills.sh", InstallCmd: "npx skills add tailwind", Priority: "optional",
			},
		},
		{
			files: []string{"vite.config.js", "vite.config.ts", "vite.config.mjs"},
			rec: SkillRecommendation{
				Name: "vite", Reason: "Vite config found",
				Source: "skills.sh", InstallCmd: "npx skills add vite", Priority: "optional",
			},
		},
		{
			files: []string{"nuxt.config.js", "nuxt.config.ts"},
			rec: SkillRecommendation{
				Name: "nuxt", Reason: "Nuxt config found",
				Source: "skills.sh", InstallCmd: "npx skills add nuxt", Priority: "recommended",
			},
		},
		{
			files: []string{"svelte.config.js", "svelte.config.ts"},
			rec: SkillRecommendation{
				Name: "svelte", Reason: "SvelteKit config found",
				Source: "skills.sh", InstallCmd: "npx skills add svelte", Priority: "optional",
			},
		},
		{
			files: []string{"angular.json"},
			rec: SkillRecommendation{
				Name: "angular", Reason: "Angular workspace found",
				Source: "skills.sh", InstallCmd: "npx skills add angular", Priority: "recommended",
			},
		},
		{
			files: []string{"Dockerfile"},
			rec: SkillRecommendation{
				Name: "docker", Reason: "Dockerfile found",
				Source: "skills.sh", InstallCmd: "npx skills add docker", Priority: "optional",
			},
		},
		{
			files: []string{"docker-compose.yml", "docker-compose.yaml", "compose.yml", "compose.yaml"},
			rec: SkillRecommendation{
				Name: "docker-compose", Reason: "Docker Compose config found",
				Source: "skills.sh", InstallCmd: "npx skills add docker-compose", Priority: "optional",
			},
		},
		{
			dirCheck: ".github/workflows",
			rec: SkillRecommendation{
				Name: "github-actions", Reason: "GitHub Actions workflows found",
				Source: "skills.sh", InstallCmd: "npx skills add github-actions", Priority: "optional",
			},
		},
		{
			files: []string{"prisma/schema.prisma"},
			rec: SkillRecommendation{
				Name: "prisma", Reason: "Prisma schema found",
				Source: "skills.sh", InstallCmd: "npx skills add prisma", Priority: "recommended",
			},
		},
		{
			dirCheck: "supabase",
			envCheck: "SUPABASE_URL",
			rec: SkillRecommendation{
				Name: "supabase", Reason: "Supabase project detected",
				Source: "skills.sh", InstallCmd: "npx skills add supabase", Priority: "recommended",
			},
		},
		{
			files: []string{"astro.config.mjs", "astro.config.ts"},
			rec: SkillRecommendation{
				Name: "astro", Reason: "Astro config found",
				Source: "skills.sh", InstallCmd: "npx skills add astro", Priority: "optional",
			},
		},
		{
			files: []string{"remix.config.js", "remix.config.ts"},
			rec: SkillRecommendation{
				Name: "remix", Reason: "Remix config found",
				Source: "skills.sh", InstallCmd: "npx skills add remix", Priority: "optional",
			},
		},
	}

	var recs []SkillRecommendation
	seen := make(map[string]bool)

	for _, m := range markers {
		if seen[m.rec.Name] {
			continue
		}
		if matchMarker(projectDir, m) {
			recs = append(recs, m.rec)
			seen[m.rec.Name] = true
		}
	}

	return recs
}

// matchMarker checks if any of the marker's conditions match in projectDir.
func matchMarker(dir string, m frameworkMarker) bool {
	// Check files.
	for _, f := range m.files {
		if _, err := os.Stat(filepath.Join(dir, f)); err == nil {
			return true
		}
	}

	// Check directory.
	if m.dirCheck != "" {
		info, err := os.Stat(filepath.Join(dir, m.dirCheck))
		if err == nil && info.IsDir() {
			return true
		}
	}

	// Check env var in .env file.
	if m.envCheck != "" {
		if envFileContains(filepath.Join(dir, ".env"), m.envCheck) {
			return true
		}
	}

	return false
}

// envFileContains checks if a .env file contains a line starting with the given prefix.
func envFileContains(path, prefix string) bool {
	content, err := os.ReadFile(path)
	if err != nil {
		return false
	}
	for _, line := range strings.Split(string(content), "\n") {
		line = strings.TrimSpace(line)
		if strings.HasPrefix(line, prefix) {
			return true
		}
	}
	return false
}

// deduplicateSkills removes duplicate skills by name, keeping the first occurrence.
func deduplicateSkills(recs []SkillRecommendation) []SkillRecommendation {
	seen := make(map[string]bool)
	var result []SkillRecommendation
	for _, r := range recs {
		if !seen[r.Name] {
			seen[r.Name] = true
			result = append(result, r)
		}
	}
	return result
}

// FormatRecommendations returns a plain text string of skill recommendations
// for non-TUI output. Skills are grouped by priority.
func FormatRecommendations(recs []SkillRecommendation) string {
	if len(recs) == 0 {
		return ""
	}

	var sb strings.Builder
	sb.WriteString("Recommended skills:\n")

	// Show recommended first, then optional/suggested.
	for _, r := range recs {
		if r.Priority == "recommended" {
			sb.WriteString(formatPlainSkillLine(r, true))
		}
	}
	for _, r := range recs {
		if r.Priority != "recommended" {
			sb.WriteString(formatPlainSkillLine(r, false))
		}
	}

	return sb.String()
}

func formatPlainSkillLine(r SkillRecommendation, recommended bool) string {
	icon := "  o "
	if recommended {
		icon = "  * "
	}

	line := fmt.Sprintf("%s%s -- %s", icon, r.Name, r.Reason)

	// Add install command if it is an external skill.
	if r.Source != "cos-builtin" {
		line += fmt.Sprintf(" (%s)", r.InstallCmd)
	}

	return line + "\n"
}

// FormatSkillRecommendations returns a styled string for displaying skill
// recommendations in the TUI wizard.
func FormatSkillRecommendations(recs []SkillRecommendation) string {
	if len(recs) == 0 {
		return ""
	}

	headerStyle := lipgloss.NewStyle().Bold(true).Foreground(lipgloss.Color("99"))
	recStyle := lipgloss.NewStyle().Foreground(lipgloss.Color("46"))
	optStyle := lipgloss.NewStyle().Foreground(lipgloss.Color("242"))
	sugStyle := lipgloss.NewStyle().Foreground(lipgloss.Color("240"))

	var sb strings.Builder
	sb.WriteString(headerStyle.Render("Skill Recommendations"))
	sb.WriteString("\n")

	for _, rec := range recs {
		var tag string
		switch rec.Priority {
		case "recommended":
			tag = recStyle.Render("[recommended]")
		case "optional":
			tag = optStyle.Render("[optional]   ")
		default:
			tag = sugStyle.Render("[suggested]  ")
		}
		sb.WriteString(fmt.Sprintf("  %s %s -- %s\n", tag, rec.Name, rec.Reason))
	}

	// Collect external install commands.
	var external []string
	seen := map[string]bool{}
	for _, rec := range recs {
		if rec.Source != "cos-builtin" && !strings.HasPrefix(rec.InstallCmd, "/") {
			if !seen[rec.InstallCmd] {
				seen[rec.InstallCmd] = true
				external = append(external, rec.InstallCmd)
			}
		}
	}
	if len(external) > 0 {
		sb.WriteString("\n  Install external skills with:\n")
		for _, cmd := range external {
			sb.WriteString(fmt.Sprintf("    %s\n", cmd))
		}
	}

	return sb.String()
}
