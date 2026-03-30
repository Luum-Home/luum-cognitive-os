package cli

import (
	"fmt"
	"os"
	"strings"

	"github.com/spf13/cobra"

	"luum-agent-os/cmd/cos/internal/installer"
	"luum-agent-os/cmd/cos/internal/project"
	"luum-agent-os/cmd/cos/internal/registry"
	"luum-agent-os/cmd/cos/internal/security"
	"luum-agent-os/cmd/cos/internal/ui"
)

var (
	addFrom     string
	addForce    bool
	addGenerate bool
	addDryRun   bool
)

var addCmd = &cobra.Command{
	Use:   "add <skill> [skill...]",
	Short: "Search and install skills in one step",
	Long: `Search configured registries (including skills.sh) and install the best match.

This is a convenience command that combines search + install.
Multiple skills can be installed at once.

Examples:
  cos add react                         Search all registries, install best match
  cos add react typescript              Install multiple skills
  cos add --from skills-sh react        Search only skills.sh registry
  cos add --from cos-official security  Search only the cos-official registry`,
	Args: cobra.MinimumNArgs(1),
	RunE: runAdd,
}

func init() {
	addCmd.Flags().StringVar(&addFrom, "from", "", "Search only this registry (by name)")
	addCmd.Flags().BoolVar(&addForce, "force", false, "Bypass security audit (not recommended)")
	addCmd.Flags().BoolVar(&addGenerate, "generate", false, "Auto-generate manifest from repo structure")
	addCmd.Flags().BoolVar(&addDryRun, "dry-run", false, "Show what would be installed without installing")
	rootCmd.AddCommand(addCmd)
}

func runAdd(cmd *cobra.Command, args []string) error {
	projectRoot := project.FindRootOrCwd()
	registries := registry.LoadRegistries(projectRoot)

	var hasErrors bool

	for _, skillName := range args {
		if err := addOneSkill(skillName, projectRoot, registries); err != nil {
			fmt.Println(ui.ErrorStyle.Render(fmt.Sprintf("%s %s: %s", ui.IconError, skillName, err.Error())))
			hasErrors = true
		}
	}

	if hasErrors {
		os.Exit(1)
	}
	return nil
}

// addOneSkill searches for and installs a single skill.
func addOneSkill(skillName string, projectRoot string, registries []registry.RegistryConfig) error {
	ui.Step(ui.IconInfo, fmt.Sprintf("Searching for %q...", skillName))

	// Search for the skill across registries.
	var results []registry.AnnotatedResult
	var searchErrors []error

	if addFrom != "" {
		r, err := registry.SearchOneRegistry(registries, addFrom, skillName, 5)
		if err != nil {
			return fmt.Errorf("searching registry %q: %w", addFrom, err)
		}
		results = r
	} else {
		r, errs := registry.SearchAllRegistries(registries, skillName, 5)
		results = r
		searchErrors = errs
	}

	// Show non-fatal search errors as warnings.
	for _, err := range searchErrors {
		fmt.Println(ui.WarningStyle.Render(fmt.Sprintf("  %s %s", ui.IconWarning, err.Error())))
	}

	if len(results) == 0 {
		return fmt.Errorf("no packages found matching %q", skillName)
	}

	// Pick the best match: exact name match first, then first result.
	best := pickBestMatch(results, skillName)

	// Display what we found.
	fmt.Println()
	printAddMatch(best)

	// Resolve the installable spec from the result.
	spec := resolveInstallSpec(best)
	if spec == "" {
		return fmt.Errorf("could not resolve install path for %q", best.Name)
	}

	// Run the install.
	ui.Step(ui.IconInfo, fmt.Sprintf("Installing %s...", spec))

	opts := installer.InstallOptions{
		Force:    addForce,
		Generate: addGenerate,
		DryRun:   addDryRun,
	}

	result, err := installer.RunInstall(spec, projectRoot, opts)
	if err != nil {
		return fmt.Errorf("installing: %w", err)
	}

	// Display audit report.
	if result.Audit != nil {
		printAddAuditReport(result.Audit)
	}

	// Display result.
	fmt.Println()
	if result.Installed {
		fmt.Println(ui.SuccessStyle.Render(fmt.Sprintf(
			"%s Installed %s@%s successfully", ui.IconSuccess, result.Package, result.Version,
		)))
	} else if addDryRun {
		fmt.Println(ui.InfoStyle.Render(fmt.Sprintf(
			"%s Dry run: %s@%s would be installed", ui.IconInfo, result.Package, result.Version,
		)))
	} else if result.Message != "" {
		fmt.Println(ui.InfoStyle.Render(fmt.Sprintf("%s %s", ui.IconInfo, result.Message)))
	}

	return nil
}

// pickBestMatch selects the best result, preferring exact name matches.
func pickBestMatch(results []registry.AnnotatedResult, query string) registry.AnnotatedResult {
	queryLower := strings.ToLower(query)

	// First pass: exact match on Name or Repo.
	for _, r := range results {
		nameLower := strings.ToLower(r.Name)
		repoLower := strings.ToLower(r.Repo)
		if nameLower == queryLower || repoLower == queryLower {
			return r
		}
	}

	// Second pass: contains match on Name.
	for _, r := range results {
		if strings.Contains(strings.ToLower(r.Name), queryLower) {
			return r
		}
	}

	// Fall back to highest stars/installs.
	best := results[0]
	for _, r := range results[1:] {
		if r.Stars > best.Stars {
			best = r
		}
	}
	return best
}

// resolveInstallSpec converts a search result into an installable spec.
func resolveInstallSpec(r registry.AnnotatedResult) string {
	// If URL is a GitHub URL, use it directly.
	if r.URL != "" && strings.HasPrefix(r.URL, "https://github.com/") {
		return r.URL
	}

	// If we have owner and repo, construct a scoped name.
	if r.Owner != "" && r.Repo != "" {
		return fmt.Sprintf("@%s/%s", r.Owner, r.Repo)
	}

	// If URL is a local path, use it.
	if r.URL != "" {
		return r.URL
	}

	return ""
}

// printAddMatch displays the selected match to the user.
func printAddMatch(r registry.AnnotatedResult) {
	name := ui.HeaderStyle.Render(r.Name)
	from := ui.MutedStyle.Render(fmt.Sprintf("from: %s", r.Registry))

	starsStr := ""
	if r.Stars > 0 {
		// Use installs label for skills-sh, stars for GitHub.
		if r.Registry == "skills-sh" {
			starsStr = ui.MutedStyle.Render(registry.FormatInstallCount(r.Stars))
		} else {
			starsStr = ui.MutedStyle.Render(fmt.Sprintf("★ %d", r.Stars))
		}
	}

	fmt.Printf("  %s  %s  %s\n", name, starsStr, from)
	if r.Description != "" {
		fmt.Printf("  %s\n", ui.DimStyle.Render(r.Description))
	}
	fmt.Println()
}

// printAddAuditReport displays the security audit results in compact form.
func printAddAuditReport(audit *security.AuditReport) {
	fmt.Println()
	ui.Step(ui.IconInfo, "Security Audit:")

	for _, gate := range audit.Gates {
		ui.AuditGate(string(gate.Status), gate.Name, gate.Message)
		for _, finding := range gate.Findings {
			fmt.Printf("      %s %s\n", ui.IconBullet, ui.MutedStyle.Render(finding))
		}
	}

	if audit.Forced {
		fmt.Println()
		ui.Step(ui.IconWarning, "Audit failures were force-overridden")
	}
}
