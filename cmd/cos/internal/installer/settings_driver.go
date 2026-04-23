package installer

import (
	"os"
	"path/filepath"
)

// SettingsDriver describes the harness-specific settings projection target.
type SettingsDriver struct {
	Harness         string
	SettingsRelPath string
	ProjectExpr     string
	DisplayPath     string
}

// ResolveSettingsDriver selects the active harness projection for a project.
//
// Precedence:
// 1. COGNITIVE_OS_HARNESS explicit override
// 2. Existing project driver file (.codex/hooks.json or .claude/settings.json)
// 3. Codex runtime environment hints
// 4. Claude compatibility default
func ResolveSettingsDriver(projectRoot string) SettingsDriver {
	if explicit := os.Getenv("COGNITIVE_OS_HARNESS"); explicit != "" {
		return settingsDriverForHarness(explicit)
	}

	codexPath := filepath.Join(projectRoot, ".codex", "hooks.json")
	claudePath := filepath.Join(projectRoot, ".claude", "settings.json")
	if fileExists(codexPath) && !fileExists(claudePath) {
		return settingsDriverForHarness("codex")
	}
	if fileExists(claudePath) && !fileExists(codexPath) {
		return settingsDriverForHarness("claude")
	}

	if os.Getenv("CODEX_PROJECT_DIR") != "" || os.Getenv("CODEX_SESSION_ID") != "" || os.Getenv("CODEX_HOME") != "" {
		return settingsDriverForHarness("codex")
	}

	return settingsDriverForHarness("claude")
}

func settingsDriverForHarness(harness string) SettingsDriver {
	switch harness {
	case "codex":
		return SettingsDriver{
			Harness:         "codex",
			SettingsRelPath: filepath.Join(".codex", "hooks.json"),
			ProjectExpr:     "${COGNITIVE_OS_PROJECT_DIR:-${CODEX_PROJECT_DIR:-$PWD}}",
			DisplayPath:     ".codex/hooks.json",
		}
	default:
		return SettingsDriver{
			Harness:         "claude",
			SettingsRelPath: filepath.Join(".claude", "settings.json"),
			ProjectExpr:     "${COGNITIVE_OS_PROJECT_DIR:-${CLAUDE_PROJECT_DIR:-$PWD}}",
			DisplayPath:     ".claude/settings.json",
		}
	}
}

func fileExists(path string) bool {
	_, err := os.Stat(path)
	return err == nil
}
