package cli

import (
	"fmt"
	"os"
	"path/filepath"
	"sort"

	"github.com/spf13/cobra"

	"luum-agent-os/cmd/cos/internal/installer"
	"luum-agent-os/cmd/cos/internal/lockfile"
	"luum-agent-os/cmd/cos/internal/manifest"
	"luum-agent-os/cmd/cos/internal/project"
	"luum-agent-os/cmd/cos/internal/resolver"
	"luum-agent-os/cmd/cos/internal/ui"
)

var updateCmd = &cobra.Command{
	Use:   "update [package]",
	Short: "Update installed packages to latest versions",
	Long: `Update one or all installed packages.

Examples:
  cos update @luum/safety-mesh   Update specific package
  cos update                     Update all packages`,
	RunE: runUpdate,
}

func init() {
	rootCmd.AddCommand(updateCmd)
}

func runUpdate(cmd *cobra.Command, args []string) error {
	// Find project root.
	cwd, err := os.Getwd()
	if err != nil {
		return fmt.Errorf("getting working directory: %w", err)
	}

	projectRoot, err := project.FindRoot(cwd)
	if err != nil {
		projectRoot = cwd
	}

	// Load lockfile.
	lf, err := lockfile.Load(projectRoot)
	if err != nil {
		return fmt.Errorf("loading lockfile: %w", err)
	}

	if len(lf.Packages) == 0 {
		fmt.Println()
		fmt.Println(ui.InfoStyle.Render(fmt.Sprintf("%s No packages installed", ui.IconInfo)))
		return nil
	}

	// Determine which packages to update.
	var packagesToUpdate []string

	if len(args) > 0 {
		spec := args[0]
		pkgName, pkg := findPackage(lf, spec)
		if pkg == nil {
			fmt.Println()
			fmt.Println(ui.ErrorStyle.Render(fmt.Sprintf(
				"%s Package %q is not installed", ui.IconError, spec)))
			os.Exit(1)
		}
		packagesToUpdate = []string{pkgName}
	} else {
		for name := range lf.Packages {
			packagesToUpdate = append(packagesToUpdate, name)
		}
		sort.Strings(packagesToUpdate)
	}

	ui.Step(ui.IconInfo, fmt.Sprintf("Checking %d package(s) for updates...", len(packagesToUpdate)))

	updated := 0
	upToDate := 0
	failed := 0

	for _, pkgName := range packagesToUpdate {
		pkg := lf.Packages[pkgName]

		// Skip local packages (can't check for updates remotely).
		if pkg.SourceType == "local" {
			fmt.Printf("  %s %s: skipped (local source)\n",
				ui.InfoStyle.Render(ui.IconInfo), pkgName)
			upToDate++
			continue
		}

		// Resolve the source to get owner/repo.
		source, err := resolver.Resolve(pkg.Source)
		if err != nil {
			fmt.Printf("  %s %s: failed to resolve source: %v\n",
				ui.WarningStyle.Render(ui.IconWarning), pkgName, err)
			failed++
			continue
		}

		// Fetch latest to check version.
		latestVersion, err := fetchLatestVersion(source)
		if err != nil {
			fmt.Printf("  %s %s: failed to check for updates: %v\n",
				ui.WarningStyle.Render(ui.IconWarning), pkgName, err)
			failed++
			continue
		}

		if latestVersion == "" || latestVersion == pkg.Version {
			fmt.Printf("  %s %s@%s is up-to-date\n",
				ui.SuccessStyle.Render(ui.IconCheck), pkgName, pkg.Version)
			upToDate++
			continue
		}

		// Newer version available: reinstall.
		fmt.Printf("  %s %s: %s -> %s\n",
			ui.InfoStyle.Render(ui.IconArrow), pkgName, pkg.Version, latestVersion)

		// Remove old installation.
		targets := buildTargetsFromLocked(pkg.Exports)
		if err := installer.Uninstall(targets); err != nil {
			fmt.Printf("  %s %s: failed to remove old version: %v\n",
				ui.ErrorStyle.Render(ui.IconError), pkgName, err)
			failed++
			continue
		}

		hookExports := extractHookManifestExports(pkg.Exports)
		settingsPath := filepath.Join(projectRoot, ".claude", "settings.json")
		hookBasePath := filepath.Join(".cognitive-os", "hooks", "cos", pkgName)
		_ = installer.UnregisterHooks(settingsPath, hookExports, hookBasePath)

		lf.RemovePackage(pkgName)

		// Install the new version.
		opts := installer.InstallOptions{Force: true}
		result, err := installer.RunInstall(pkg.Source, projectRoot, opts)
		if err != nil {
			fmt.Printf("  %s %s: failed to install new version: %v\n",
				ui.ErrorStyle.Render(ui.IconError), pkgName, err)
			failed++
			continue
		}

		if result.Installed {
			updated++
		} else {
			upToDate++
		}
	}

	// Reload lockfile after updates (RunInstall may have modified it).
	if updated > 0 {
		if err := lf.Save(projectRoot); err != nil {
			return fmt.Errorf("saving lockfile: %w", err)
		}
	}

	// Print summary.
	fmt.Println()

	var parts []string
	if updated > 0 {
		parts = append(parts, fmt.Sprintf("%d updated", updated))
	}
	if upToDate > 0 {
		parts = append(parts, fmt.Sprintf("%d up-to-date", upToDate))
	}
	if failed > 0 {
		parts = append(parts, fmt.Sprintf("%d failed", failed))
	}

	summary := joinSummaryParts(parts)
	if failed > 0 && updated == 0 {
		fmt.Println(ui.WarningStyle.Render(fmt.Sprintf("%s %s", ui.IconWarning, summary)))
	} else {
		fmt.Println(ui.SuccessStyle.Render(fmt.Sprintf("%s %s", ui.IconSuccess, summary)))
	}

	return nil
}

// fetchLatestVersion fetches the latest version of a package from its source.
// Returns the version string from the manifest or empty if unavailable.
func fetchLatestVersion(source *resolver.ResolvedSource) (string, error) {
	fetchedDir, err := resolver.Fetch(source)
	if err != nil {
		return "", err
	}
	defer resolver.CleanupFetch(fetchedDir)

	manifestPath := filepath.Join(fetchedDir, "cos-package.yaml")
	m, err := manifest.ParseFile(manifestPath)
	if err != nil {
		return "", nil
	}

	return m.Version, nil
}

// joinSummaryParts joins string parts with ", ".
func joinSummaryParts(parts []string) string {
	if len(parts) == 0 {
		return "No changes"
	}
	result := parts[0]
	for i := 1; i < len(parts); i++ {
		result += ", " + parts[i]
	}
	return result
}
