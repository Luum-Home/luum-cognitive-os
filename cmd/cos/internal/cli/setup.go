package cli

import (
	"fmt"
	"os"

	"github.com/spf13/cobra"

	"luum-agent-os/cmd/cos/internal/project"
	"luum-agent-os/cmd/cos/internal/ui"
	"luum-agent-os/cmd/cos/internal/wizard"
)

var (
	setupNonInteractive bool
	setupPreset         string
	setupGlobal         bool
)

var setupCmd = &cobra.Command{
	Use:   "setup",
	Short: "Interactive onboarding wizard for Cognitive OS",
	Long: `Run the interactive TUI wizard to install and configure Cognitive OS
in the current project, or install global rules for all projects.

The wizard detects your project environment (language, package manager,
Docker, git, CI) and guides you through selecting a security profile,
project phase, and optional features.

Use --global to install universal COS rules to ~/.claude/rules/cos/.
Global rules apply to ALL projects on this machine without needing
per-project installation. Hooks are NOT installed globally (they
require project context).

Presets for non-interactive mode:
  solo-dev      Minimal profile, reconstruction phase, fast development
  team          Standard profile, stabilization phase (default)
  enterprise    Paranoid profile, production phase, all features

Examples:
  cos setup                           Interactive wizard
  cos setup --global                  Install global rules for all projects
  cos setup --non-interactive         Use defaults (team preset)
  cos setup --preset solo-dev         Use solo-dev preset
  cos setup --preset enterprise       Use enterprise preset`,
	RunE: runSetup,
}

func init() {
	setupCmd.Flags().BoolVar(&setupNonInteractive, "non-interactive", false, "Skip TUI, use defaults or preset")
	setupCmd.Flags().StringVar(&setupPreset, "preset", "", "Use a preset configuration (solo-dev|team|enterprise)")
	setupCmd.Flags().BoolVar(&setupGlobal, "global", false, "Install universal COS rules to ~/.claude/rules/cos/")
	rootCmd.AddCommand(setupCmd)
}

func runSetup(cmd *cobra.Command, args []string) error {
	// Handle --global mode: install universal rules to ~/.claude/rules/cos/.
	if setupGlobal {
		return runGlobalSetup()
	}

	cwd, err := os.Getwd()
	if err != nil {
		return fmt.Errorf("getting working directory: %w", err)
	}

	// Phase 1: Detection (always runs).
	env := wizard.Detect(cwd)

	// Check for git.
	if !env.GitInitialized {
		fmt.Println(ui.WarningStyle.Render("Warning: No git repository detected. COS works best with git."))
		fmt.Println(ui.MutedStyle.Render("  Run 'git init' first, or continue anyway."))
		fmt.Println()
	}

	// Determine setup mode.
	var cfg wizard.SetupConfig

	if setupPreset != "" {
		// Preset mode: apply preset and skip TUI.
		preset := wizard.Preset(setupPreset)
		switch preset {
		case wizard.PresetSoloDev, wizard.PresetTeam, wizard.PresetEnterprise:
			cfg = wizard.ApplyPreset(preset, env)
		default:
			return fmt.Errorf("unknown preset %q: valid presets are solo-dev, team, enterprise", setupPreset)
		}
		fmt.Println(ui.InfoStyle.Render(fmt.Sprintf("Using %s preset", setupPreset)))
		fmt.Println()
		fmt.Println(wizard.FormatSummary(cfg))
		fmt.Println()
	} else if setupNonInteractive || !wizard.IsTTY() {
		// Non-interactive mode: use defaults.
		cfg = wizard.DefaultConfig(env)
		fmt.Println(ui.InfoStyle.Render("Non-interactive mode: using team defaults"))
		fmt.Println()
		fmt.Println(wizard.FormatSummary(cfg))
		fmt.Println()
	} else {
		// Interactive TUI wizard.
		cfg, err = wizard.RunWizard(env)
		if err != nil {
			return fmt.Errorf("wizard: %w", err)
		}
	}

	if !cfg.Proceed {
		fmt.Println(ui.MutedStyle.Render("Setup cancelled."))
		return nil
	}

	// Phase 5: Install.
	cosSourceDir := findCosSourceDir()
	result := wizard.RunInstall(cfg, cwd, cosSourceDir)

	// Report results.
	fmt.Println()
	if len(result.Errors) > 0 {
		fmt.Println(ui.WarningStyle.Render("Completed with warnings:"))
		for _, e := range result.Errors {
			fmt.Printf("  %s %s\n", ui.IconBullet, e)
		}
		fmt.Println()
	}

	fmt.Println(ui.SuccessStyle.Render(fmt.Sprintf("%s Done! Cognitive OS is configured.", ui.IconCheck)))
	fmt.Println()

	// Show skill recommendations based on detected stack.
	recs := wizard.RecommendSkills(env, cwd)
	if len(recs) > 0 {
		fmt.Println(wizard.FormatRecommendations(recs))
	}

	fmt.Println(ui.MutedStyle.Render("Next steps:"))
	fmt.Println("  cos status       Verify installation")
	fmt.Println("  cos map          View system knowledge graph")
	fmt.Println()

	return nil
}

// coreGlobalRules is the list of 14 core rules installed globally.
// These are universal across all projects and define COS behavioral protocol.
// Kept in sync with scripts/cos-init-global.sh and hooks/self-install.sh CORE_RULES.
var coreGlobalRules = []string{
	"RULES-COMPACT.md",
	"adaptive-bypass.md",
	"acceptance-criteria.md",
	"agent-quality.md",
	"trust-score.md",
	"definition-of-done.md",
	"closed-loop-prompts.md",
	"token-economy.md",
	"responsiveness.md",
	"credential-management.md",
	"license-policy.md",
	"result-management.md",
	"decomposition.md",
	"model-routing.md",
}

// runGlobalSetup installs universal COS rules to ~/.claude/rules/cos/.
func runGlobalSetup() error {
	homeDir, err := os.UserHomeDir()
	if err != nil {
		return fmt.Errorf("finding home directory: %w", err)
	}

	cosSourceDir := findCosSourceDir()
	if cosSourceDir == "" {
		return fmt.Errorf("cannot find COS source directory; set COS_SOURCE_DIR or run from luum-agent-os repo")
	}

	rulesSource := fmt.Sprintf("%s/rules", cosSourceDir)
	if _, err := os.Stat(rulesSource); err != nil {
		return fmt.Errorf("rules source not found: %s", rulesSource)
	}

	globalRulesDir := fmt.Sprintf("%s/.claude/rules/cos", homeDir)

	fmt.Println(ui.InfoStyle.Render("Installing universal COS rules globally"))
	fmt.Println()
	fmt.Printf("  Source: %s/rules/\n", cosSourceDir)
	fmt.Printf("  Target: %s/\n", globalRulesDir)
	fmt.Println()

	// Create target directory.
	if err := os.MkdirAll(globalRulesDir, 0755); err != nil {
		return fmt.Errorf("creating rules directory: %w", err)
	}

	installed := 0
	updated := 0
	skipped := 0

	for _, rule := range coreGlobalRules {
		src := fmt.Sprintf("%s/%s", rulesSource, rule)
		dst := fmt.Sprintf("%s/%s", globalRulesDir, rule)

		srcData, err := os.ReadFile(src)
		if err != nil {
			fmt.Printf("  %s %s (not found, skipped)\n", ui.IconBullet, rule)
			skipped++
			continue
		}

		dstData, dstErr := os.ReadFile(dst)
		if dstErr == nil {
			// File exists — check if content differs.
			if string(srcData) == string(dstData) {
				skipped++
				continue
			}
			updated++
		} else {
			installed++
		}

		if err := os.WriteFile(dst, srcData, 0644); err != nil {
			return fmt.Errorf("writing %s: %w", rule, err)
		}
	}

	fmt.Printf("  Installed: %d new\n", installed)
	fmt.Printf("  Updated:   %d changed\n", updated)
	fmt.Printf("  Skipped:   %d unchanged\n", skipped)
	fmt.Println()
	fmt.Println(ui.SuccessStyle.Render(fmt.Sprintf("%s %d universal rules installed to %s", ui.IconCheck, installed+updated+skipped, globalRulesDir)))
	fmt.Println()
	fmt.Println(ui.MutedStyle.Render("These rules now apply to ALL projects on this machine."))
	fmt.Println(ui.MutedStyle.Render("Project-specific rules are still installed per-project via 'cos setup'."))

	return nil
}

// findCosSourceDir is defined in new.go — reuse it via the package scope.
// If not available (different build), try common locations.
func findCosSetupSourceDir() string {
	// Check COS_SOURCE_DIR env var.
	if dir := os.Getenv("COS_SOURCE_DIR"); dir != "" {
		return dir
	}

	// Check via project root detection.
	root := project.FindRootOrCwd()
	if _, err := os.Stat(fmt.Sprintf("%s/scripts/cos-init.sh", root)); err == nil {
		return root
	}

	return ""
}
