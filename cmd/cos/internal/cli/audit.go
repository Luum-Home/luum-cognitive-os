package cli

import (
	"fmt"
	"os"
	"path/filepath"

	"github.com/spf13/cobra"

	"luum-agent-os/cmd/cos/internal/manifest"
	"luum-agent-os/cmd/cos/internal/resolver"
	"luum-agent-os/cmd/cos/internal/security"
	"luum-agent-os/cmd/cos/internal/ui"
)

var auditCmd = &cobra.Command{
	Use:   "audit <package>",
	Short: "Run security audit on a package without installing",
	Long: `Run the 5-gate security audit on a package source.

Examples:
  cos audit ./my-package
  cos audit @luum/safety-mesh
  cos audit https://github.com/org/repo`,
	Args: cobra.ExactArgs(1),
	RunE: runAudit,
}

func init() {
	rootCmd.AddCommand(auditCmd)
}

func runAudit(cmd *cobra.Command, args []string) error {
	spec := args[0]

	ui.Step(ui.IconInfo, fmt.Sprintf("Resolving %s...", spec))

	// Step 1: Resolve the source.
	source, err := resolver.Resolve(spec)
	if err != nil {
		return fmt.Errorf("resolving %q: %w", spec, err)
	}

	// Step 2: Fetch to temp dir.
	ui.Step(ui.IconInfo, fmt.Sprintf("Fetching %s...", source))
	fetchedDir, err := resolver.Fetch(source)
	if err != nil {
		return fmt.Errorf("fetching %q: %w", spec, err)
	}
	defer resolver.CleanupFetch(fetchedDir)

	// Step 3: Parse manifest for license info.
	license := detectLicense(fetchedDir)

	// Step 4: Run security audit.
	ui.Step(ui.IconInfo, "Running security audit...")
	report := security.RunAudit(fetchedDir, license)
	report.Package = source.Name

	// Step 5: Print formatted report.
	fmt.Println()
	printAuditReport(report)

	fmt.Println()
	if report.Passed {
		fmt.Println(ui.SuccessStyle.Render(fmt.Sprintf(
			"%s Security audit PASSED for %s", ui.IconSuccess, source.Name,
		)))
		return nil
	}

	fmt.Println(ui.ErrorStyle.Render(fmt.Sprintf(
		"%s Security audit FAILED for %s", ui.IconError, source.Name,
	)))
	os.Exit(1)
	return nil
}

// detectLicense tries to read the license from the manifest, falls back to empty.
func detectLicense(fetchedDir string) string {
	manifestPath := filepath.Join(fetchedDir, "cos-package.yaml")
	m, err := manifest.ParseFile(manifestPath)
	if err != nil {
		return ""
	}
	return m.License
}
