package cli

import (
	"fmt"
	"os"
	"path/filepath"
	"strings"

	"github.com/spf13/cobra"

	"luum-agent-os/cmd/cos/internal/lockfile"
	"luum-agent-os/cmd/cos/internal/manifest"
	"luum-agent-os/cmd/cos/internal/resolver"
	"luum-agent-os/cmd/cos/internal/ui"
)

var infoInstalled bool

var infoCmd = &cobra.Command{
	Use:   "info <package>",
	Short: "Show detailed information about a cos package",
	Long: `Display package details including exports, dependencies, license, and security status.

Examples:
  cos info @luum/quality-gates        Show package info from GitHub
  cos info ./packages/quality-gates   Show local package info
  cos info --installed quality-gates  Show info for an installed package`,
	Args: cobra.ExactArgs(1),
	RunE: runInfo,
}

func init() {
	infoCmd.Flags().BoolVar(&infoInstalled, "installed", false, "Look up package in cos-lock.yaml instead of fetching")
	rootCmd.AddCommand(infoCmd)
}

func runInfo(cmd *cobra.Command, args []string) error {
	spec := args[0]

	if infoInstalled {
		return runInfoInstalled(spec)
	}
	return runInfoFetch(spec)
}

// runInfoInstalled shows info for a package already recorded in cos-lock.yaml.
func runInfoInstalled(name string) error {
	cwd, err := os.Getwd()
	if err != nil {
		return fmt.Errorf("getting working directory: %w", err)
	}

	lf, err := lockfile.Load(cwd)
	if err != nil {
		return fmt.Errorf("loading lockfile: %w", err)
	}

	// Try exact match first, then search by suffix.
	pkg := lf.GetPackage(name)
	if pkg == nil {
		// Try with @scope prefix variants.
		for key, p := range lf.Packages {
			if strings.HasSuffix(key, "/"+name) || key == name {
				found := p
				pkg = &found
				name = key
				break
			}
		}
	}

	if pkg == nil {
		fmt.Println(ui.ErrorStyle.Render(fmt.Sprintf("%s Package %q is not installed", ui.IconError, name)))
		os.Exit(1)
	}

	// Display installed package info.
	fmt.Println()
	printField("Package", name)
	printField("Version", pkg.Version)
	printField("License", pkg.License)
	printField("Source", fmt.Sprintf("%s (%s)", pkg.Source, pkg.SourceType))

	// Exports.
	if len(pkg.Exports) > 0 {
		fmt.Println()
		fmt.Println(ui.HeaderStyle.Render("Exports:"))
		for _, e := range pkg.Exports {
			hookInfo := ""
			if e.HookEvent != "" {
				hookInfo = fmt.Sprintf("  %s", ui.MutedStyle.Render(e.HookEvent))
				if e.HookMatcher != "" {
					hookInfo += fmt.Sprintf("(%s)", ui.MutedStyle.Render(e.HookMatcher))
				}
			}
			fmt.Printf("  [%s] %s%s\n", e.Type, e.Source, hookInfo)
		}
	}

	// Installed metadata.
	fmt.Println()
	fmt.Println(ui.HeaderStyle.Render("Install Info:"))
	printField("  Installed", pkg.InstalledAt)
	if pkg.Commit != "" {
		printField("  Commit", pkg.Commit)
	}
	if pkg.Integrity != "" {
		printField("  Integrity", pkg.Integrity)
	}
	if pkg.Forced {
		fmt.Printf("  %s\n", ui.WarningStyle.Render("Forced: audit failures were overridden"))
	}

	// Audit status.
	fmt.Println()
	fmt.Println(ui.HeaderStyle.Render("Audit:"))
	printAuditField("  License", pkg.Audit.License)
	printAuditField("  Secrets", pkg.Audit.Secrets)
	printAuditField("  Injection", pkg.Audit.Injection)
	printAuditField("  Sandbox", pkg.Audit.Sandbox)

	fmt.Println()
	return nil
}

// runInfoFetch resolves, fetches, and displays info about an uninstalled package.
func runInfoFetch(spec string) error {
	ui.Step(ui.IconInfo, fmt.Sprintf("Resolving %s...", spec))

	// Resolve the source.
	source, err := resolver.Resolve(spec)
	if err != nil {
		return fmt.Errorf("resolving %q: %w", spec, err)
	}

	// Fetch to temp dir.
	ui.Step(ui.IconInfo, fmt.Sprintf("Fetching %s...", source))
	fetchedDir, err := resolver.Fetch(source)
	if err != nil {
		return fmt.Errorf("fetching %q: %w", spec, err)
	}
	defer resolver.CleanupFetch(fetchedDir)

	// Parse manifest.
	manifestPath := filepath.Join(fetchedDir, "cos-package.yaml")
	m, err := manifest.ParseFile(manifestPath)
	if err != nil {
		return fmt.Errorf("parsing manifest: %w", err)
	}

	// Display package info.
	fmt.Println()
	printField("Package", m.Name)
	printField("Version", m.Version)
	printField("License", m.License)
	if m.Description != "" {
		printField("Description", m.Description)
	}

	// Provides.
	if len(m.Provides) > 0 {
		printField("Provides", strings.Join(m.Provides, ", "))
	}

	// Exports.
	if len(m.Exports) > 0 {
		fmt.Println()
		fmt.Println(ui.HeaderStyle.Render("Exports:"))
		for _, e := range m.Exports {
			desc := ""
			if e.Description != "" {
				desc = fmt.Sprintf("  %s", ui.MutedStyle.Render(e.Description))
			}
			hookInfo := ""
			if e.HookEvent != "" {
				hookInfo = fmt.Sprintf(" %s", e.HookEvent)
				if e.HookMatcher != "" {
					hookInfo += fmt.Sprintf("(%s)", e.HookMatcher)
				}
				hookInfo = ui.MutedStyle.Render(hookInfo)
			}
			fmt.Printf("  [%s] %s%s%s\n", e.Type, e.Source, hookInfo, desc)
		}
	}

	// Dependencies.
	if len(m.Dependencies) > 0 {
		fmt.Println()
		fmt.Println(ui.HeaderStyle.Render("Dependencies:"))
		for name, dep := range m.Dependencies {
			fmt.Printf("  %s %s\n", name, ui.MutedStyle.Render(dep.Version))
		}
	} else {
		printField("Dependencies", "none")
	}

	// Platform.
	if m.Platform != nil {
		printPlatformInfo(m.Platform)
	}

	// Keywords.
	if len(m.Keywords) > 0 {
		printField("Keywords", strings.Join(m.Keywords, ", "))
	}

	// Security summary.
	fmt.Println()
	fmt.Println(ui.HeaderStyle.Render("Security:"))
	printLicenseSafety(m.License)
	fmt.Printf("  Audit: %s\n", ui.MutedStyle.Render(
		fmt.Sprintf("not yet audited (run: cos audit %s)", spec),
	))

	fmt.Println()
	return nil
}

// printField prints a labeled value on a single line.
func printField(label, value string) {
	fmt.Printf("%s %s\n", ui.HeaderStyle.Render(label+":"), value)
}

// printAuditField prints an audit gate result with pass/fail styling.
func printAuditField(label, status string) {
	if status == "" {
		status = "not checked"
	}
	var styled string
	switch status {
	case "pass":
		styled = ui.SuccessStyle.Render(status)
	case "fail":
		styled = ui.ErrorStyle.Render(status)
	case "warning":
		styled = ui.WarningStyle.Render(status)
	default:
		styled = ui.MutedStyle.Render(status)
	}
	fmt.Printf("%s %s\n", label+":", styled)
}

// printPlatformInfo displays platform requirements.
func printPlatformInfo(p *manifest.Platform) {
	parts := []string{}
	if p.Shell != "" {
		parts = append(parts, p.Shell)
	}
	if len(p.OS) > 0 {
		parts = append(parts, strings.Join(p.OS, "/"))
	}
	if len(p.Tools) > 0 {
		toolNames := make([]string, len(p.Tools))
		for i, t := range p.Tools {
			if t.Version != "" {
				toolNames[i] = fmt.Sprintf("%s@%s", t.Name, t.Version)
			} else {
				toolNames[i] = t.Name
			}
		}
		parts = append(parts, strings.Join(toolNames, ", "))
	}
	if len(parts) > 0 {
		printField("Platform", strings.Join(parts, "; "))
	}
}

// printLicenseSafety classifies a license as safe, caution, or blocked.
func printLicenseSafety(license string) {
	upper := strings.ToUpper(license)

	safe := map[string]bool{
		"MIT": true, "APACHE-2.0": true, "BSD-2-CLAUSE": true,
		"BSD-3-CLAUSE": true, "ISC": true, "CC0-1.0": true,
	}
	blocked := map[string]bool{
		"AGPL-3.0": true, "AGPL-3.0-ONLY": true, "AGPL-3.0-OR-LATER": true,
		"SSPL": true, "SSPL-1.0": true,
	}
	caution := map[string]bool{
		"LGPL-2.1": true, "LGPL-3.0": true, "MPL-2.0": true,
		"GPL-2.0": true, "GPL-3.0": true,
	}

	switch {
	case safe[upper]:
		fmt.Printf("  License: %s (%s)\n", ui.SuccessStyle.Render("SAFE"), license)
	case blocked[upper]:
		fmt.Printf("  License: %s (%s)\n", ui.ErrorStyle.Render("BLOCKED"), license)
	case caution[upper]:
		fmt.Printf("  License: %s (%s)\n", ui.WarningStyle.Render("CAUTION"), license)
	case license == "":
		fmt.Printf("  License: %s\n", ui.WarningStyle.Render("unknown (no license specified)"))
	default:
		fmt.Printf("  License: %s (%s)\n", ui.MutedStyle.Render("unknown"), license)
	}
}
