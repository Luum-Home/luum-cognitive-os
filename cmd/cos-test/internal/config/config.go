package config

import (
	"os"
	"path/filepath"
)

// TestCategory represents a test dimension/category.
type TestCategory string

const (
	CategoryUnit        TestCategory = "unit"
	CategoryBehavior    TestCategory = "behavior"
	CategoryIntegration TestCategory = "integration"
	CategorySystem      TestCategory = "system"
	CategoryE2E         TestCategory = "e2e"
)

// AllCategories returns all test categories in order.
func AllCategories() []TestCategory {
	return []TestCategory{
		CategoryUnit,
		CategoryBehavior,
		CategoryIntegration,
		CategorySystem,
		CategoryE2E,
	}
}

// CategoryLabel returns a human-readable label for a category.
func CategoryLabel(c TestCategory) string {
	switch c {
	case CategoryUnit:
		return "Unit"
	case CategoryBehavior:
		return "Behavior"
	case CategoryIntegration:
		return "Integration"
	case CategorySystem:
		return "System"
	case CategoryE2E:
		return "E2E"
	default:
		return string(c)
	}
}

// CategoryMarker returns the pytest marker for a category.
func CategoryMarker(c TestCategory) string {
	return string(c)
}

// Config holds the test runner configuration.
type Config struct {
	// ProjectRoot is the root of the Cognitive OS project.
	ProjectRoot string

	// TestsDir is the directory containing tests.
	TestsDir string

	// HooksDir is the hooks directory to scan for coverage.
	HooksDir string

	// SkillsDir is the skills directory to scan for coverage.
	SkillsDir string

	// HooksLibDir is the hooks library directory.
	HooksLibDir string

	// PytestArgs are additional args passed to pytest.
	PytestArgs []string

	// Categories to run (empty = all).
	Categories []TestCategory

	// CIMode disables TUI and uses plain text.
	CIMode bool

	// Verbose enables verbose output.
	Verbose bool

	// DockerRequired indicates tests need Docker.
	DockerRequired bool

	// WatchPaths are directories to watch for changes.
	WatchPaths []string
}

// DefaultConfig creates a config with default values, auto-detecting the project root.
func DefaultConfig() *Config {
	root := findProjectRoot()
	return &Config{
		ProjectRoot: root,
		TestsDir:    filepath.Join(root, "tests"),
		HooksDir:    filepath.Join(root, "hooks"),
		SkillsDir:   filepath.Join(root, "skills"),
		HooksLibDir: filepath.Join(root, "hooks", "_lib"),
		WatchPaths: []string{
			filepath.Join(root, "hooks"),
			filepath.Join(root, "skills"),
			filepath.Join(root, "hooks", "_lib"),
		},
	}
}

// TestDir returns the directory for a specific test category.
func (c *Config) TestDir(cat TestCategory) string {
	return filepath.Join(c.TestsDir, string(cat))
}

// findProjectRoot walks up from cwd looking for the tests/ directory.
func findProjectRoot() string {
	dir, err := os.Getwd()
	if err != nil {
		return "."
	}

	for {
		if _, err := os.Stat(filepath.Join(dir, "tests")); err == nil {
			return dir
		}
		parent := filepath.Dir(dir)
		if parent == dir {
			break
		}
		dir = parent
	}

	// Fallback to cwd.
	cwd, _ := os.Getwd()
	return cwd
}
