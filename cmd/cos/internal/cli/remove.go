package cli

import (
	"fmt"
	"os"
	"path/filepath"
	"strings"

	"github.com/spf13/cobra"

	"luum-agent-os/cmd/cos/internal/installer"
	"luum-agent-os/cmd/cos/internal/lockfile"
	"luum-agent-os/cmd/cos/internal/manifest"
	"luum-agent-os/cmd/cos/internal/project"
	"luum-agent-os/cmd/cos/internal/ui"
)

var removeCmd = &cobra.Command{
	Use:   "remove <package>",
	Short: "Remove an installed cos package",
	Long: `Remove a cos package and all its installed files.

Examples:
  cos remove @luum/safety-mesh
  cos remove safety-mesh`,
	Args: cobra.ExactArgs(1),
	RunE: runRemove,
}

func init() {
	rootCmd.AddCommand(removeCmd)
}

func runRemove(cmd *cobra.Command, args []string) error {
	spec := args[0]

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

	// Find the package: try exact name, then with/without scope.
	pkgName, pkg := findPackage(lf, spec)
	if pkg == nil {
		fmt.Println()
		fmt.Println(ui.ErrorStyle.Render(fmt.Sprintf("%s Package %q is not installed", ui.IconError, spec)))
		os.Exit(1)
	}

	ui.Step(ui.IconInfo, fmt.Sprintf("Removing %s@%s...", pkgName, pkg.Version))

	// Reconstruct ExportTargets from lockfile entries.
	targets := buildTargetsFromLocked(pkg.Exports)

	// Show exports being removed.
	if len(targets) > 0 {
		fmt.Println()
		ui.Step(ui.IconInfo, fmt.Sprintf("Removing %d export(s):", len(targets)))

		for _, t := range targets {
			relPath, err := filepath.Rel(projectRoot, t.Target)
			if err != nil {
				relPath = t.Target
			}
			ui.ExportLine("-", relPath, t.Export.Type)
		}
	}

	// Uninstall exports (remove files).
	if err := installer.Uninstall(targets); err != nil {
		return fmt.Errorf("removing files: %w", err)
	}

	// Unregister hooks from settings.json.
	settingsPath := filepath.Join(projectRoot, ".claude", "settings.json")
	hookBasePath := filepath.Join(".cognitive-os", "hooks", "cos", pkgName)
	hookExports := extractHookManifestExports(pkg.Exports)
	if err := installer.UnregisterHooks(settingsPath, hookExports, hookBasePath); err != nil {
		return fmt.Errorf("unregistering hooks: %w", err)
	}

	// Remove from lockfile.
	lf.RemovePackage(pkgName)

	// Save lockfile.
	if err := lf.Save(projectRoot); err != nil {
		return fmt.Errorf("saving lockfile: %w", err)
	}

	// Print summary.
	fmt.Println()
	fmt.Println(ui.SuccessStyle.Render(fmt.Sprintf(
		"%s Removed %s, %d file(s) cleaned up", ui.IconSuccess, pkgName, len(targets),
	)))

	return nil
}

// findPackage searches the lockfile for a package by name.
// Tries exact match first, then tries with/without scope prefix.
func findPackage(lf *lockfile.Lockfile, spec string) (string, *lockfile.LockedPackage) {
	// Strip leading "@" and version suffix for lookup.
	name := spec
	if idx := strings.LastIndex(name, "@"); idx > 0 {
		name = name[:idx]
	}

	// Try exact match.
	if pkg := lf.GetPackage(name); pkg != nil {
		return name, pkg
	}

	// Try without leading "@".
	bare := strings.TrimPrefix(name, "@")
	if pkg := lf.GetPackage(bare); pkg != nil {
		return bare, pkg
	}

	// If the spec contains "/", try just the repo part.
	if idx := strings.LastIndex(bare, "/"); idx >= 0 {
		repoName := bare[idx+1:]
		if pkg := lf.GetPackage(repoName); pkg != nil {
			return repoName, pkg
		}
	}

	// Iterate all packages and match by repo name suffix.
	for pkgName, pkg := range lf.Packages {
		// Match if the package name ends with the spec.
		if strings.HasSuffix(pkgName, "/"+bare) || strings.HasSuffix(pkgName, "/"+name) {
			p := pkg
			return pkgName, &p
		}
		// Match bare name directly.
		if pkgName == bare || pkgName == name {
			p := pkg
			return pkgName, &p
		}
	}

	return "", nil
}

// buildTargetsFromLocked reconstructs ExportTargets from lockfile entries.
func buildTargetsFromLocked(exports []lockfile.LockedExport) []installer.ExportTarget {
	targets := make([]installer.ExportTarget, len(exports))
	for i, exp := range exports {
		targets[i] = installer.ExportTarget{
			Export: manifest.Export{
				Source:      exp.Source,
				Type:        exp.Type,
				HookEvent:   exp.HookEvent,
				HookMatcher: exp.HookMatcher,
			},
			Target: exp.Target,
		}
	}
	return targets
}

// extractHookManifestExports converts locked exports back to manifest exports
// for use with UnregisterHooks.
func extractHookManifestExports(exports []lockfile.LockedExport) []manifest.Export {
	var hooks []manifest.Export
	for _, exp := range exports {
		hooks = append(hooks, manifest.Export{
			Source:      exp.Source,
			Type:        exp.Type,
			HookEvent:   exp.HookEvent,
			HookMatcher: exp.HookMatcher,
		})
	}
	return hooks
}
