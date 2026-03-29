package wizard

import (
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strings"

	"github.com/charmbracelet/huh/spinner"
	"github.com/charmbracelet/lipgloss"
)

// InstallResult holds the outcome of the installation.
type InstallResult struct {
	SettingsCreated   bool
	RulesInstalled    int
	HooksRegistered   int
	ConfigCreated     bool
	CosInitRun        bool
	Errors            []string
}

// RunInstall executes the installation based on the wizard configuration.
// It delegates to cos-init.sh and set-security-profile.sh when available.
func RunInstall(cfg SetupConfig, projectDir, cosSourceDir string) InstallResult {
	result := InstallResult{}

	successStyle := lipgloss.NewStyle().Foreground(lipgloss.Color("46"))
	check := successStyle.Render("+")

	// Phase 5: Execute installation with spinner.
	fmt.Println()
	fmt.Println(lipgloss.NewStyle().Bold(true).Foreground(lipgloss.Color("99")).Render("Installing..."))
	fmt.Println()

	// Step 1: Create .claude directory structure.
	err := spinner.New().
		Title("Creating directory structure...").
		Action(func() {
			dirs := []string{
				filepath.Join(projectDir, ".claude"),
				filepath.Join(projectDir, ".claude", "rules"),
				filepath.Join(projectDir, ".claude", "settings"),
			}
			for _, d := range dirs {
				if mkErr := os.MkdirAll(d, 0755); mkErr != nil {
					result.Errors = append(result.Errors, fmt.Sprintf("mkdir %s: %v", d, mkErr))
				}
			}
		}).
		Run()
	if err != nil {
		result.Errors = append(result.Errors, fmt.Sprintf("spinner: %v", err))
	}

	// Step 2: Run cos-init.sh if available.
	initScript := ""
	if cosSourceDir != "" {
		initScript = filepath.Join(cosSourceDir, "scripts", "cos-init.sh")
		if _, err := os.Stat(initScript); os.IsNotExist(err) {
			initScript = ""
		}
	}

	if initScript != "" {
		profileArg := fmt.Sprintf("--%s", cfg.Profile)
		err := spinner.New().
			Title("Running cos-init.sh...").
			Action(func() {
				cmd := exec.Command("bash", initScript, profileArg)
				cmd.Dir = projectDir
				cmd.Env = os.Environ()
				if out, runErr := cmd.CombinedOutput(); runErr != nil {
					result.Errors = append(result.Errors,
						fmt.Sprintf("cos-init.sh: %v\n%s", runErr, strings.TrimSpace(string(out))))
				} else {
					result.CosInitRun = true
				}
			}).
			Run()
		if err != nil {
			result.Errors = append(result.Errors, fmt.Sprintf("spinner: %v", err))
		}

		if result.CosInitRun {
			fmt.Printf("  %s Ran cos-init.sh (%s profile)\n", check, cfg.Profile)
		}
	}

	// Step 3: Create or update cognitive-os.yaml with wizard selections.
	cosYamlPath := filepath.Join(projectDir, "cognitive-os.yaml")
	err = spinner.New().
		Title("Configuring cognitive-os.yaml...").
		Action(func() {
			writeErr := writeCognitiveOSYaml(cosYamlPath, cfg)
			if writeErr != nil {
				result.Errors = append(result.Errors, fmt.Sprintf("cognitive-os.yaml: %v", writeErr))
			} else {
				result.ConfigCreated = true
			}
		}).
		Run()
	if err != nil {
		result.Errors = append(result.Errors, fmt.Sprintf("spinner: %v", err))
	}
	if result.ConfigCreated {
		fmt.Printf("  %s Created cognitive-os.yaml\n", check)
	}

	// Step 4: Apply security profile if script available.
	if cosSourceDir != "" {
		profileScript := filepath.Join(cosSourceDir, "scripts", "set-security-profile.sh")
		if _, err := os.Stat(profileScript); err == nil {
			err := spinner.New().
				Title(fmt.Sprintf("Applying %s security profile...", cfg.Profile)).
				Action(func() {
					cmd := exec.Command("bash", profileScript, string(cfg.Profile))
					cmd.Dir = projectDir
					cmd.Env = os.Environ()
					if out, runErr := cmd.CombinedOutput(); runErr != nil {
						result.Errors = append(result.Errors,
							fmt.Sprintf("set-security-profile.sh: %v\n%s", runErr, strings.TrimSpace(string(out))))
					}
				}).
				Run()
			if err != nil {
				result.Errors = append(result.Errors, fmt.Sprintf("spinner: %v", err))
			}
			fmt.Printf("  %s Applied %s security profile\n", check, cfg.Profile)
		}
	}

	// Step 5: Write .claude/settings.json if it does not exist.
	settingsPath := filepath.Join(projectDir, ".claude", "settings.json")
	if _, err := os.Stat(settingsPath); os.IsNotExist(err) {
		writeErr := writeSettingsJSON(settingsPath, cfg)
		if writeErr != nil {
			result.Errors = append(result.Errors, fmt.Sprintf("settings.json: %v", writeErr))
		} else {
			result.SettingsCreated = true
			fmt.Printf("  %s Created .claude/settings.json\n", check)
		}
	}

	// Count what was installed.
	result.RulesInstalled = countInstalledRules(projectDir)
	result.HooksRegistered = countRegisteredHooks(projectDir)

	if result.RulesInstalled > 0 {
		fmt.Printf("  %s Installed %d rules\n", check, result.RulesInstalled)
	}
	if result.HooksRegistered > 0 {
		fmt.Printf("  %s Registered %d hooks\n", check, result.HooksRegistered)
	}

	return result
}

// writeCognitiveOSYaml creates or updates the cognitive-os.yaml file.
func writeCognitiveOSYaml(path string, cfg SetupConfig) error {
	// If the file already exists, we only update specific fields.
	// For simplicity in v1, we write a complete config.

	content := fmt.Sprintf(`# Cognitive OS Configuration
# Generated by cos setup wizard

project:
  name: %s
  phase: %s

efficiency:
  profile: standard

model_capability:
  level: 3

security:
  profile: %s

features:
  engram: %t
  auto_skills: %t
  agent_teams: %t
  smart_reader: %t

resources:
  budget:
    daily_alert_usd: 10
    monthly_limit_usd: 200
    per_agent_max_usd: 2.00
  compute:
    max_parallel_agents: 5
    agent_timeout_seconds: 300
`,
		cfg.Env.ProjectName,
		cfg.Phase,
		cfg.Profile,
		cfg.Features.Engram,
		cfg.Features.AutoSkills,
		cfg.Features.AgentTeams,
		cfg.Features.SmartRead,
	)

	return os.WriteFile(path, []byte(content), 0644)
}

// writeSettingsJSON creates a minimal .claude/settings.json.
func writeSettingsJSON(path string, cfg SetupConfig) error {
	content := `{
  "permissions": {
    "allow": [],
    "deny": []
  }
}
`
	return os.WriteFile(path, []byte(content), 0644)
}

// countInstalledRules counts .md files in .claude/rules/.
func countInstalledRules(dir string) int {
	pattern := filepath.Join(dir, ".claude", "rules", "*.md")
	matches, err := filepath.Glob(pattern)
	if err != nil {
		return 0
	}
	// Also check subdirectories.
	subPattern := filepath.Join(dir, ".claude", "rules", "*", "*.md")
	subMatches, err := filepath.Glob(subPattern)
	if err == nil {
		matches = append(matches, subMatches...)
	}
	return len(matches)
}

// countRegisteredHooks parses .claude/settings.json for hook entries.
// This is a rough count — it looks for "command" keys in the hooks section.
func countRegisteredHooks(dir string) int {
	content, err := os.ReadFile(filepath.Join(dir, ".claude", "settings.json"))
	if err != nil {
		// Also try settings.local.json.
		content, err = os.ReadFile(filepath.Join(dir, ".claude", "settings.local.json"))
		if err != nil {
			return 0
		}
	}
	return strings.Count(string(content), `"command"`)
}
