// Package wizard implements the interactive TUI onboarding wizard for Cognitive OS.
package wizard

import (
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
)

// DetectedEnv holds the results of automatic project environment detection.
type DetectedEnv struct {
	ProjectName    string
	Language       string // "go", "typescript", "python", "rust", "java", "unknown"
	PackageManager string // "go modules", "npm", "yarn", "pnpm", "bun", "pip", "poetry", "uv", "cargo", "maven", "gradle", ""
	TestFramework  string // "go test", "jest", "vitest", "pytest", "cargo test", ""
	TestFileCount  int
	DockerAvail    bool
	DockerVersion  string
	GitInitialized bool
	GitBranch      string
	GitClean       bool
	CISystem       string // "github-actions", "gitlab-ci", "jenkins", "circleci", ""
	ExistingCOS    bool
	COSVersion     string
	IsMonorepo     bool
}

// Detect runs automatic project environment detection in the given directory.
func Detect(dir string) DetectedEnv {
	env := DetectedEnv{
		ProjectName: detectProjectName(dir),
		Language:    detectLanguage(dir),
	}

	env.PackageManager = detectPackageManager(dir, env.Language)
	env.TestFramework = detectTestFramework(dir, env.Language)
	env.TestFileCount = countTestFiles(dir, env.Language)
	env.DockerAvail, env.DockerVersion = detectDocker()
	env.GitInitialized, env.GitBranch, env.GitClean = detectGit(dir)
	env.CISystem = detectCI(dir)
	env.ExistingCOS, env.COSVersion = detectExistingCOS(dir)
	env.IsMonorepo = detectMonorepo(dir)

	return env
}

// FormatDetection returns a human-readable summary of the detected environment.
func (e *DetectedEnv) FormatDetection() string {
	var sb strings.Builder

	sb.WriteString(fmt.Sprintf("  Project:    %s\n", e.ProjectName))

	if e.Language != "unknown" {
		sb.WriteString(fmt.Sprintf("  Language:   %s\n", capitalizeFirst(e.Language)))
	} else {
		sb.WriteString("  Language:   Not detected\n")
	}

	if e.TestFramework != "" {
		sb.WriteString(fmt.Sprintf("  Tests:      %s", e.TestFramework))
		if e.TestFileCount > 0 {
			sb.WriteString(fmt.Sprintf(" (%d test files found)", e.TestFileCount))
		}
		sb.WriteString("\n")
	}

	if e.DockerAvail {
		sb.WriteString(fmt.Sprintf("  Docker:     Available (%s)\n", e.DockerVersion))
	} else {
		sb.WriteString("  Docker:     Not available\n")
	}

	if e.GitInitialized {
		gitStatus := "clean"
		if !e.GitClean {
			gitStatus = "dirty"
		}
		sb.WriteString(fmt.Sprintf("  Git:        %s (%s branch)\n", gitStatus, e.GitBranch))
	} else {
		sb.WriteString("  Git:        Not initialized\n")
	}

	if e.CISystem != "" {
		sb.WriteString(fmt.Sprintf("  CI:         %s\n", e.CISystem))
	}

	if e.ExistingCOS {
		sb.WriteString(fmt.Sprintf("  COS:        Installed (v%s) — upgrade mode\n", e.COSVersion))
	} else {
		sb.WriteString("  COS:        Not installed (fresh setup)\n")
	}

	if e.IsMonorepo {
		sb.WriteString("  Monorepo:   Yes\n")
	}

	return sb.String()
}

func detectProjectName(dir string) string {
	// Try go.mod module name.
	if content, err := os.ReadFile(filepath.Join(dir, "go.mod")); err == nil {
		for _, line := range strings.Split(string(content), "\n") {
			if strings.HasPrefix(line, "module ") {
				mod := strings.TrimPrefix(line, "module ")
				mod = strings.TrimSpace(mod)
				// Use the last segment of the module path.
				parts := strings.Split(mod, "/")
				return parts[len(parts)-1]
			}
		}
	}

	// Try package.json name.
	if content, err := os.ReadFile(filepath.Join(dir, "package.json")); err == nil {
		// Simple extraction without full JSON parsing.
		for _, line := range strings.Split(string(content), "\n") {
			line = strings.TrimSpace(line)
			if strings.HasPrefix(line, `"name"`) {
				parts := strings.SplitN(line, ":", 2)
				if len(parts) == 2 {
					name := strings.TrimSpace(parts[1])
					name = strings.Trim(name, `",`)
					if name != "" {
						return name
					}
				}
			}
		}
	}

	// Try pyproject.toml name.
	if content, err := os.ReadFile(filepath.Join(dir, "pyproject.toml")); err == nil {
		inProject := false
		for _, line := range strings.Split(string(content), "\n") {
			if strings.Contains(line, "[project]") || strings.Contains(line, "[tool.poetry]") {
				inProject = true
				continue
			}
			if inProject && strings.HasPrefix(strings.TrimSpace(line), "name") {
				parts := strings.SplitN(line, "=", 2)
				if len(parts) == 2 {
					name := strings.TrimSpace(parts[1])
					name = strings.Trim(name, `"' `)
					if name != "" {
						return name
					}
				}
			}
			if inProject && strings.HasPrefix(line, "[") {
				inProject = false
			}
		}
	}

	// Fallback to directory name.
	return filepath.Base(dir)
}

func detectLanguage(dir string) string {
	markers := []struct {
		file string
		lang string
	}{
		{"go.mod", "go"},
		{"go.work", "go"},
		{"package.json", "typescript"},
		{"tsconfig.json", "typescript"},
		{"pyproject.toml", "python"},
		{"requirements.txt", "python"},
		{"setup.py", "python"},
		{"Pipfile", "python"},
		{"Cargo.toml", "rust"},
		{"pom.xml", "java"},
		{"build.gradle", "java"},
		{"build.gradle.kts", "java"},
	}
	for _, m := range markers {
		if _, err := os.Stat(filepath.Join(dir, m.file)); err == nil {
			return m.lang
		}
	}
	return "unknown"
}

func detectPackageManager(dir, lang string) string {
	switch lang {
	case "go":
		return "go modules"
	case "rust":
		return "cargo"
	}

	lockFiles := []struct {
		file    string
		manager string
	}{
		{"bun.lock", "bun"},
		{"bun.lockb", "bun"},
		{"pnpm-lock.yaml", "pnpm"},
		{"yarn.lock", "yarn"},
		{"package-lock.json", "npm"},
		{"poetry.lock", "poetry"},
		{"uv.lock", "uv"},
		{"Pipfile.lock", "pipenv"},
	}
	for _, lf := range lockFiles {
		if _, err := os.Stat(filepath.Join(dir, lf.file)); err == nil {
			return lf.manager
		}
	}

	if lang == "python" {
		return "pip"
	}
	if lang == "java" {
		if _, err := os.Stat(filepath.Join(dir, "pom.xml")); err == nil {
			return "maven"
		}
		return "gradle"
	}
	return ""
}

func detectTestFramework(dir, lang string) string {
	switch lang {
	case "go":
		return "go test"
	case "rust":
		return "cargo test"
	case "python":
		if _, err := os.Stat(filepath.Join(dir, "pytest.ini")); err == nil {
			return "pytest"
		}
		if content, err := os.ReadFile(filepath.Join(dir, "pyproject.toml")); err == nil {
			if strings.Contains(string(content), "[tool.pytest") {
				return "pytest"
			}
		}
		return "pytest"
	case "typescript":
		if _, err := os.Stat(filepath.Join(dir, "vitest.config.ts")); err == nil {
			return "vitest"
		}
		if _, err := os.Stat(filepath.Join(dir, "vitest.config.js")); err == nil {
			return "vitest"
		}
		for _, name := range []string{"jest.config.ts", "jest.config.js", "jest.config.mjs", "jest.config.cjs"} {
			if _, err := os.Stat(filepath.Join(dir, name)); err == nil {
				return "jest"
			}
		}
		return ""
	case "java":
		return "junit"
	}
	return ""
}

func countTestFiles(dir, lang string) int {
	patterns := map[string][]string{
		"go":         {"**/*_test.go"},
		"typescript": {"**/*.test.ts", "**/*.spec.ts", "**/*.test.js", "**/*.spec.js"},
		"python":     {"**/test_*.py", "**/*_test.py"},
		"rust":       {}, // Rust tests are inline
		"java":       {"**/*Test.java", "**/*Tests.java"},
	}

	globs, ok := patterns[lang]
	if !ok {
		return 0
	}

	count := 0
	for _, pattern := range globs {
		matches, err := filepath.Glob(filepath.Join(dir, pattern))
		if err == nil {
			count += len(matches)
		}
		// Also check one level deeper for common structures.
		deeper, err := filepath.Glob(filepath.Join(dir, "*", pattern))
		if err == nil {
			count += len(deeper)
		}
	}
	return count
}

func detectDocker() (bool, string) {
	cmd := exec.Command("docker", "--version")
	out, err := cmd.Output()
	if err != nil {
		return false, ""
	}
	version := strings.TrimSpace(string(out))
	// Extract just "Docker XX.X.X" part.
	if idx := strings.Index(version, ","); idx > 0 {
		version = version[:idx]
	}
	return true, version
}

func detectGit(dir string) (bool, string, bool) {
	if _, err := os.Stat(filepath.Join(dir, ".git")); os.IsNotExist(err) {
		return false, "", false
	}

	branch := "unknown"
	cmd := exec.Command("git", "rev-parse", "--abbrev-ref", "HEAD")
	cmd.Dir = dir
	if out, err := cmd.Output(); err == nil {
		branch = strings.TrimSpace(string(out))
	}

	clean := true
	cmd = exec.Command("git", "status", "--porcelain")
	cmd.Dir = dir
	if out, err := cmd.Output(); err == nil {
		clean = strings.TrimSpace(string(out)) == ""
	}

	return true, branch, clean
}

func detectCI(dir string) string {
	if _, err := os.Stat(filepath.Join(dir, ".github", "workflows")); err == nil {
		return "GitHub Actions"
	}
	if _, err := os.Stat(filepath.Join(dir, ".gitlab-ci.yml")); err == nil {
		return "GitLab CI"
	}
	if _, err := os.Stat(filepath.Join(dir, "Jenkinsfile")); err == nil {
		return "Jenkins"
	}
	if _, err := os.Stat(filepath.Join(dir, ".circleci")); err == nil {
		return "CircleCI"
	}
	return ""
}

func detectExistingCOS(dir string) (bool, string) {
	versionFile := filepath.Join(dir, ".cognitive-os", "version")
	if content, err := os.ReadFile(versionFile); err == nil {
		return true, strings.TrimSpace(string(content))
	}

	cosYaml := filepath.Join(dir, "cognitive-os.yaml")
	if _, err := os.Stat(cosYaml); err == nil {
		return true, "unknown"
	}

	return false, ""
}

func detectMonorepo(dir string) bool {
	// Go workspace.
	if _, err := os.Stat(filepath.Join(dir, "go.work")); err == nil {
		return true
	}

	// Node.js monorepo tools.
	for _, f := range []string{"lerna.json", "nx.json", "turbo.json"} {
		if _, err := os.Stat(filepath.Join(dir, f)); err == nil {
			return true
		}
	}

	// Check package.json for workspaces.
	if content, err := os.ReadFile(filepath.Join(dir, "package.json")); err == nil {
		if strings.Contains(string(content), `"workspaces"`) {
			return true
		}
	}

	return false
}

func capitalizeFirst(s string) string {
	if s == "" {
		return s
	}
	return strings.ToUpper(s[:1]) + s[1:]
}
