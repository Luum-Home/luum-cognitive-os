package installer

import (
	"encoding/json"
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
// 2. .cognitive-os/install-meta.json harness field
// 3. Existing project driver file (.codex/hooks.json or .claude/settings.json)
// 4. Codex runtime environment hints
// 5. Claude compatibility default
func ResolveSettingsDriver(projectRoot string) SettingsDriver {
	if explicit := os.Getenv("COGNITIVE_OS_HARNESS"); explicit != "" {
		return settingsDriverForHarness(explicit)
	}

	if metaHarness := readInstallMetaHarness(projectRoot); metaHarness != "" {
		return settingsDriverForHarness(metaHarness)
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
	case "agents-md":
		return structuralSettingsDriver("agents-md", "AGENTS.md")
	case "opencode":
		return structuralSettingsDriver("opencode", "opencode.json")
	case "vscode-copilot":
		return structuralSettingsDriver("vscode-copilot", filepath.Join(".github", "copilot-instructions.md"))
	case "cursor":
		return structuralSettingsDriver("cursor", filepath.Join(".cursor", "rules", "cognitive-os.mdc"))
	case "qwen-code":
		return structuralSettingsDriver("qwen-code", filepath.Join(".qwen", "settings.json"))
	case "kimi-code":
		return structuralSettingsDriver("kimi-code", "AGENTS.md")
	case "gemini-cli":
		return structuralSettingsDriver("gemini-cli", filepath.Join(".gemini", "settings.json"))
	case "warp":
		return structuralSettingsDriver("warp", "AGENTS.md")
	case "amp-code":
		return structuralSettingsDriver("amp-code", "AGENTS.md")
	case "jetbrains-junie":
		return structuralSettingsDriver("jetbrains-junie", filepath.Join(".junie", "AGENTS.md"))
	case "qoder":
		return structuralSettingsDriver("qoder", "AGENTS.md")
	case "factory-droid":
		return structuralSettingsDriver("factory-droid", "AGENTS.md")
	case "cline":
		return structuralSettingsDriver("cline", filepath.Join(".clinerules", "cognitive-os.md"))
	case "continue-dev":
		return structuralSettingsDriver("continue-dev", filepath.Join(".continue", "rules", "cognitive-os.md"))
	case "kilo-code":
		return structuralSettingsDriver("kilo-code", filepath.Join(".kilocode", "rules", "cognitive-os.md"))
	case "zed-ai":
		return structuralSettingsDriver("zed-ai", ".rules")
	case "augment-code":
		return structuralSettingsDriver("augment-code", filepath.Join(".augment", "rules", "cognitive-os.md"))
	case "goose":
		return structuralSettingsDriver("goose", ".goosehints")
	case "aider":
		return structuralSettingsDriver("aider", "CONVENTIONS.md")
	case "shell-ci":
		return structuralSettingsDriver("shell-ci", filepath.Join(".cognitive-os", "shell-ci-projection.json"))
	default:
		return SettingsDriver{
			Harness:         "claude",
			SettingsRelPath: filepath.Join(".claude", "settings.json"),
			ProjectExpr:     "${COGNITIVE_OS_PROJECT_DIR:-${CLAUDE_PROJECT_DIR:-$PWD}}",
			DisplayPath:     ".claude/settings.json",
		}
	}
}

func structuralSettingsDriver(harness string, relPath string) SettingsDriver {
	return SettingsDriver{
		Harness:         harness,
		SettingsRelPath: relPath,
		ProjectExpr:     "${COGNITIVE_OS_PROJECT_DIR:-$PWD}",
		DisplayPath:     filepath.ToSlash(relPath),
	}
}

func readInstallMetaHarness(projectRoot string) string {
	data, err := os.ReadFile(filepath.Join(projectRoot, ".cognitive-os", "install-meta.json"))
	if err != nil {
		return ""
	}
	var meta struct {
		Harness string `json:"harness"`
	}
	if err := json.Unmarshal(data, &meta); err != nil {
		return ""
	}
	return meta.Harness
}

func fileExists(path string) bool {
	_, err := os.Stat(path)
	return err == nil
}
