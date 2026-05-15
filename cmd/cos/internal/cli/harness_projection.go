package cli

import (
	"fmt"
	"strings"
)

var supportedHarnesses = []string{
	"claude",
	"codex",
	"agents-md",
	"opencode",
	"vscode-copilot",
	"cursor",
	"qwen-code",
	"kimi-code",
	"gemini-cli",
	"warp",
	"amp-code",
	"jetbrains-junie",
	"qoder",
	"factory-droid",
	"cline",
	"continue-dev",
	"kilo-code",
	"zed-ai",
	"augment-code",
	"goose",
	"aider",
	"shell-ci",
}

var supportedHarnessSet = func() map[string]struct{} {
	out := make(map[string]struct{}, len(supportedHarnesses))
	for _, harness := range supportedHarnesses {
		out[harness] = struct{}{}
	}
	return out
}()

var structuralHarnessSettings = map[string]string{
	"claude":          ".claude/settings.json",
	"codex":           ".codex/hooks.json",
	"agents-md":       "AGENTS.md",
	"opencode":        "opencode.json",
	"vscode-copilot":  ".github/copilot-instructions.md",
	"cursor":          ".cursor/rules/cognitive-os.mdc",
	"qwen-code":       ".qwen/settings.json",
	"kimi-code":       "AGENTS.md",
	"gemini-cli":      ".gemini/settings.json",
	"warp":            "AGENTS.md",
	"amp-code":        "AGENTS.md",
	"jetbrains-junie": ".junie/AGENTS.md",
	"qoder":           "AGENTS.md",
	"factory-droid":   "AGENTS.md",
	"cline":           ".clinerules/cognitive-os.md",
	"continue-dev":    ".continue/rules/cognitive-os.md",
	"kilo-code":       ".kilocode/rules/cognitive-os.md",
	"zed-ai":          ".rules",
	"augment-code":    ".augment/rules/cognitive-os.md",
	"goose":           ".goosehints",
	"aider":           "CONVENTIONS.md",
	"shell-ci":        ".cognitive-os/shell-ci-projection.json",
}

func validateHarness(harness string) error {
	if _, ok := supportedHarnessSet[harness]; ok {
		return nil
	}
	return fmt.Errorf("unsupported harness %q: supported harnesses are %s", harness, strings.Join(supportedHarnesses, ", "))
}

func harnessProjectionPath(harness string) string {
	if path, ok := structuralHarnessSettings[harness]; ok {
		return path
	}
	return ".cognitive-os/install-meta.json"
}

func harnessProofSummary(harness string) string {
	switch harness {
	case "claude", "codex":
		return "native-lifecycle"
	case "opencode":
		return "governed-wrapper-enforced for signed plugin slice; otherwise structural-advisory"
	case "shell-ci":
		return "shell-ci projection"
	default:
		return "structural-advisory"
	}
}
