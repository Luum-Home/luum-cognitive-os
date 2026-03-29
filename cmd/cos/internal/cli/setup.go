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
)

var setupCmd = &cobra.Command{
	Use:   "setup",
	Short: "Interactive onboarding wizard for Cognitive OS",
	Long: `Run the interactive TUI wizard to install and configure Cognitive OS
in the current project.

The wizard detects your project environment (language, package manager,
Docker, git, CI) and guides you through selecting a security profile,
project phase, and optional features.

Presets for non-interactive mode:
  solo-dev      Minimal profile, reconstruction phase, fast development
  team          Standard profile, stabilization phase (default)
  enterprise    Paranoid profile, production phase, all features

Examples:
  cos setup                           Interactive wizard
  cos setup --non-interactive         Use defaults (team preset)
  cos setup --preset solo-dev         Use solo-dev preset
  cos setup --preset enterprise       Use enterprise preset`,
	RunE: runSetup,
}

func init() {
	setupCmd.Flags().BoolVar(&setupNonInteractive, "non-interactive", false, "Skip TUI, use defaults or preset")
	setupCmd.Flags().StringVar(&setupPreset, "preset", "", "Use a preset configuration (solo-dev|team|enterprise)")
	rootCmd.AddCommand(setupCmd)
}

func runSetup(cmd *cobra.Command, args []string) error {
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
	fmt.Println(ui.MutedStyle.Render("Next steps:"))
	fmt.Println("  cos status       Verify installation")
	fmt.Println("  cos map          View system knowledge graph")
	fmt.Println()

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
