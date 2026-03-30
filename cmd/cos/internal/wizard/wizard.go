package wizard

import (
	"fmt"
	"os"
	"strings"

	"github.com/charmbracelet/huh"
	"github.com/charmbracelet/lipgloss"
)

// SecurityProfile defines the hook profile for installation.
type SecurityProfile string

const (
	ProfileMinimal  SecurityProfile = "minimal"
	ProfileStandard SecurityProfile = "standard"
	ProfileParanoid SecurityProfile = "paranoid"
)

// Phase defines the project lifecycle phase.
type Phase string

const (
	PhaseReconstruction Phase = "reconstruction"
	PhaseStabilization  Phase = "stabilization"
	PhaseProduction     Phase = "production"
	PhaseMaintenance    Phase = "maintenance"
)

// Feature flags for optional components.
type Features struct {
	Engram     bool
	AutoSkills bool
	AgentTeams bool
	SmartRead  bool
}

// SetupConfig holds all the wizard selections to be used during installation.
type SetupConfig struct {
	Env      DetectedEnv
	Profile  SecurityProfile
	Phase    Phase
	Features Features
	Proceed  bool
}

// Preset defines a pre-configured combination of settings.
type Preset string

const (
	PresetSoloDev    Preset = "solo-dev"
	PresetTeam       Preset = "team"
	PresetEnterprise Preset = "enterprise"
)

// ApplyPreset returns a SetupConfig with preset defaults (no TUI needed).
func ApplyPreset(preset Preset, env DetectedEnv) SetupConfig {
	cfg := SetupConfig{
		Env:     env,
		Proceed: true,
	}

	switch preset {
	case PresetSoloDev:
		cfg.Profile = ProfileMinimal
		cfg.Phase = PhaseReconstruction
		cfg.Features = Features{
			Engram:     true,
			AutoSkills: true,
			AgentTeams: false,
			SmartRead:  true,
		}
	case PresetTeam:
		cfg.Profile = ProfileStandard
		cfg.Phase = PhaseStabilization
		cfg.Features = Features{
			Engram:     true,
			AutoSkills: true,
			AgentTeams: false,
			SmartRead:  true,
		}
	case PresetEnterprise:
		cfg.Profile = ProfileParanoid
		cfg.Phase = PhaseProduction
		cfg.Features = Features{
			Engram:     true,
			AutoSkills: true,
			AgentTeams: true,
			SmartRead:  true,
		}
	default:
		// Default to team preset.
		cfg.Profile = ProfileStandard
		cfg.Phase = PhaseStabilization
		cfg.Features = Features{
			Engram:     true,
			AutoSkills: true,
			AgentTeams: false,
			SmartRead:  true,
		}
	}

	return cfg
}

// DefaultConfig returns the default non-interactive configuration.
func DefaultConfig(env DetectedEnv) SetupConfig {
	return ApplyPreset(PresetTeam, env)
}

// RunWizard runs the interactive TUI wizard and returns the user's selections.
// It assumes the terminal supports TUI. For non-interactive mode, use DefaultConfig.
func RunWizard(env DetectedEnv) (SetupConfig, error) {
	cfg := SetupConfig{
		Env: env,
	}

	// Styles for the header.
	titleStyle := lipgloss.NewStyle().
		Bold(true).
		Foreground(lipgloss.Color("99"))

	detectionBoxStyle := lipgloss.NewStyle().
		Border(lipgloss.RoundedBorder()).
		BorderForeground(lipgloss.Color("241")).
		Padding(0, 2).
		MarginBottom(1)

	// Phase 1: Show detection results.
	fmt.Println()
	fmt.Println(titleStyle.Render("Cognitive OS Setup Wizard"))
	fmt.Println()
	fmt.Println(detectionBoxStyle.Render(
		lipgloss.NewStyle().Bold(true).Render("Detected environment:") + "\n" +
			env.FormatDetection(),
	))

	// Phase 1b: Show skill recommendations based on detected stack.
	recs := RecommendSkills(env, ".")
	if len(recs) > 0 {
		recBoxStyle := lipgloss.NewStyle().
			Border(lipgloss.RoundedBorder()).
			BorderForeground(lipgloss.Color("86")).
			Padding(0, 2).
			MarginBottom(1)
		fmt.Println(recBoxStyle.Render(FormatSkillRecommendations(recs)))
	}

	// Phase 2: Security profile selection.
	var profile string
	profileForm := huh.NewForm(
		huh.NewGroup(
			huh.NewSelect[string]().
				Title("Security profile").
				Description("Controls how many hooks and safety gates are active").
				Options(
					huh.NewOption("Minimal — fast development, 10 hooks", "minimal"),
					huh.NewOption("Standard — recommended, 14 core rules, 24 hooks", "standard"),
					huh.NewOption("Paranoid — compliance/audit, 55+ hooks", "paranoid"),
				).
				Value(&profile),
		).Title("Profile"),
	).WithTheme(huh.ThemeCharm()).
		WithShowHelp(true)

	if err := profileForm.Run(); err != nil {
		return cfg, fmt.Errorf("profile selection: %w", err)
	}
	cfg.Profile = SecurityProfile(profile)

	// Phase 2b: Project phase selection.
	var phase string
	phaseForm := huh.NewForm(
		huh.NewGroup(
			huh.NewSelect[string]().
				Title("Project phase").
				Description("Determines governance strictness and hook behavior").
				Options(
					huh.NewOption("Reconstruction — max speed, min governance", "reconstruction"),
					huh.NewOption("Stabilization — balanced (recommended)", "stabilization"),
					huh.NewOption("Production — max governance, feature flags required", "production"),
					huh.NewOption("Maintenance — bug fixes and security only", "maintenance"),
				).
				Value(&phase),
		).Title("Phase"),
	).WithTheme(huh.ThemeCharm())

	if err := phaseForm.Run(); err != nil {
		return cfg, fmt.Errorf("phase selection: %w", err)
	}
	cfg.Phase = Phase(phase)

	// Phase 3: Feature toggles.
	var features []string
	featureForm := huh.NewForm(
		huh.NewGroup(
			huh.NewMultiSelect[string]().
				Title("Enable features").
				Description("Space to toggle, Enter to confirm").
				Options(
					huh.NewOption("Engram persistent memory", "engram").Selected(true),
					huh.NewOption("Auto skill generation", "auto-skills").Selected(true),
					huh.NewOption("Agent Teams (experimental)", "agent-teams"),
					huh.NewOption("Smart file reader", "smart-read").Selected(true),
				).
				Value(&features),
		).Title("Features"),
	).WithTheme(huh.ThemeCharm())

	if err := featureForm.Run(); err != nil {
		return cfg, fmt.Errorf("feature selection: %w", err)
	}

	for _, f := range features {
		switch f {
		case "engram":
			cfg.Features.Engram = true
		case "auto-skills":
			cfg.Features.AutoSkills = true
		case "agent-teams":
			cfg.Features.AgentTeams = true
		case "smart-read":
			cfg.Features.SmartRead = true
		}
	}

	// Phase 4: Summary and confirmation.
	fmt.Println()
	fmt.Println(FormatSummary(cfg))
	fmt.Println()

	var proceed bool
	confirmForm := huh.NewForm(
		huh.NewGroup(
			huh.NewConfirm().
				Title("Proceed with installation?").
				Affirmative("Yes").
				Negative("No").
				Value(&proceed),
		),
	).WithTheme(huh.ThemeCharm())

	if err := confirmForm.Run(); err != nil {
		return cfg, fmt.Errorf("confirmation: %w", err)
	}
	cfg.Proceed = proceed

	return cfg, nil
}

// FormatSummary returns a formatted summary of the installation plan.
func FormatSummary(cfg SetupConfig) string {
	boxStyle := lipgloss.NewStyle().
		Border(lipgloss.DoubleBorder()).
		BorderForeground(lipgloss.Color("86")).
		Padding(1, 2)

	var sb strings.Builder
	sb.WriteString(lipgloss.NewStyle().Bold(true).Render("Installation Summary"))
	sb.WriteString("\n\n")

	profileDesc := map[SecurityProfile]string{
		ProfileMinimal:  "Minimal (10 hooks)",
		ProfileStandard: "Standard (14 core rules, 24 hooks)",
		ProfileParanoid: "Paranoid (55+ hooks)",
	}

	sb.WriteString(fmt.Sprintf("  Profile:   %s\n", profileDesc[cfg.Profile]))
	sb.WriteString(fmt.Sprintf("  Phase:     %s\n", cfg.Phase))

	var featureList []string
	if cfg.Features.Engram {
		featureList = append(featureList, "Engram")
	}
	if cfg.Features.AutoSkills {
		featureList = append(featureList, "Auto-skills")
	}
	if cfg.Features.AgentTeams {
		featureList = append(featureList, "Agent Teams")
	}
	if cfg.Features.SmartRead {
		featureList = append(featureList, "Smart reader")
	}
	sb.WriteString(fmt.Sprintf("  Features:  %s\n", strings.Join(featureList, ", ")))

	ruleCount := "14 core + 78 on-demand"
	if cfg.Profile == ProfileMinimal {
		ruleCount = "6 core + 86 on-demand"
	} else if cfg.Profile == ProfileParanoid {
		ruleCount = "55 core + 37 on-demand"
	}
	sb.WriteString(fmt.Sprintf("  Rules:     %s\n", ruleCount))

	return boxStyle.Render(sb.String())
}

// IsTTY returns true if stdout is connected to a terminal.
func IsTTY() bool {
	fi, err := os.Stdout.Stat()
	if err != nil {
		return false
	}
	return fi.Mode()&os.ModeCharDevice != 0
}
