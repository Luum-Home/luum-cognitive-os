package cli

import (
	"fmt"
	"os"
	"path/filepath"
	"strings"

	"github.com/spf13/cobra"

	"luum-agent-os/cmd/cos/internal/installer"
	"luum-agent-os/cmd/cos/internal/project"
	"luum-agent-os/cmd/cos/internal/registry"
	"luum-agent-os/cmd/cos/internal/security"
	"luum-agent-os/cmd/cos/internal/ui"
)

var (
	installForce    bool
	installGenerate bool
	installDryRun   bool
)

var installCmd = &cobra.Command{
	Use:   "install <package>",
	Short: "Install a cos package",
	Long: `Install a cos package from local path, GitHub, or URL.

Examples:
  cos install ./my-package              Install from local directory
  cos install @luum/safety-mesh         Install from GitHub (github.com/luum/safety-mesh)
  cos install @luum/safety-mesh@1.0.0   Install specific version
  cos install https://github.com/org/repo  Install from URL
  cos install --generate https://github.com/org/repo  Auto-generate manifest`,
	Args: cobra.ExactArgs(1),
	RunE: runInstall,
}

func init() {
	installCmd.Flags().BoolVar(&installForce, "force", false, "Bypass security audit (not recommended)")
	installCmd.Flags().BoolVar(&installGenerate, "generate", false, "Auto-generate manifest from repo structure")
	installCmd.Flags().BoolVar(&installDryRun, "dry-run", false, "Show what would be installed without installing")
	rootCmd.AddCommand(installCmd)
}

func runInstall(cmd *cobra.Command, args []string) error {
	spec := args[0]

	// Find project root.
	cwd, err := os.Getwd()
	if err != nil {
		return fmt.Errorf("getting working directory: %w", err)
	}

	projectRoot, err := project.FindRoot(cwd)
	if err != nil {
		// Fall back to current directory if no project markers found.
		projectRoot = cwd
	}

	// If the spec is a bare name (no @, no /, no .), try registry resolution first.
	spec = resolveFromRegistries(spec, projectRoot)

	// Print header.
	ui.Step(ui.IconInfo, fmt.Sprintf("Resolving %s...", spec))

	opts := installer.InstallOptions{
		Force:    installForce,
		Generate: installGenerate,
		DryRun:   installDryRun,
	}

	result, err := installer.RunInstall(spec, projectRoot, opts)
	if err != nil {
		fmt.Println()
		fmt.Println(ui.ErrorStyle.Render(fmt.Sprintf("%s %s", ui.IconError, err.Error())))
		os.Exit(1)
	}

	// Display audit report.
	if result.Audit != nil {
		printAuditReport(result.Audit)
	}

	// Display exports.
	if len(result.Exports) > 0 {
		printExports(result.Exports, projectRoot, installDryRun)
	}

	// Display result.
	fmt.Println()
	if result.Installed {
		fmt.Println(ui.SuccessStyle.Render(fmt.Sprintf(
			"%s Installed %s@%s successfully", ui.IconSuccess, result.Package, result.Version,
		)))
	} else if installDryRun {
		fmt.Println(ui.InfoStyle.Render(fmt.Sprintf(
			"%s Dry run: %s@%s would be installed", ui.IconInfo, result.Package, result.Version,
		)))
	} else if result.Message != "" {
		fmt.Println(ui.InfoStyle.Render(fmt.Sprintf("%s %s", ui.IconInfo, result.Message)))
	}

	return nil
}

// printAuditReport displays the security audit results.
func printAuditReport(audit *security.AuditReport) {
	fmt.Println()
	ui.Step(ui.IconInfo, "Security Audit:")

	for _, gate := range audit.Gates {
		ui.AuditGate(string(gate.Status), gate.Name, gate.Message)

		// Show findings for failed gates.
		for _, finding := range gate.Findings {
			fmt.Printf("      %s %s\n", ui.IconBullet, ui.MutedStyle.Render(finding))
		}
	}

	if audit.Forced {
		fmt.Println()
		ui.Step(ui.IconWarning, "Audit failures were force-overridden")
	}
}

// printExports displays the list of exports that were/would be installed.
func printExports(targets []installer.ExportTarget, projectRoot string, dryRun bool) {
	fmt.Println()

	action := "Installing"
	if dryRun {
		action = "Would install"
	}
	ui.Step(ui.IconInfo, fmt.Sprintf("%s %d export(s):", action, len(targets)))

	for _, t := range targets {
		// Show the path relative to the project root for readability.
		relPath, err := filepath.Rel(projectRoot, t.Target)
		if err != nil {
			relPath = t.Target
		}
		ui.ExportLine("+", relPath, t.Export.Type)
	}
}

// resolveFromRegistries checks if the spec is a bare package name (no path
// indicators) and tries to find it in configured registries. If found, returns
// the GitHub URL. Otherwise returns the original spec unchanged.
func resolveFromRegistries(spec string, projectRoot string) string {
	// Skip if spec is clearly a path, URL, or scoped name.
	if strings.HasPrefix(spec, "./") || strings.HasPrefix(spec, "/") ||
		strings.HasPrefix(spec, "@") || strings.HasPrefix(spec, "https://") ||
		strings.HasPrefix(spec, "github.com/") || strings.Contains(spec, "/") {
		return spec
	}

	registries := registry.LoadRegistries(projectRoot)
	results, _ := registry.SearchAllRegistries(registries, spec, 5)

	// Look for an exact name match.
	for _, r := range results {
		if strings.EqualFold(r.Repo, spec) || strings.EqualFold(r.Name, spec) {
			if r.URL != "" && strings.HasPrefix(r.URL, "https://") {
				return r.URL
			}
		}
	}

	return spec
}
