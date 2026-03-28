package cli

import (
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strings"

	"github.com/spf13/cobra"

	"luum-agent-os/cmd/cos/internal/manifest"
	"luum-agent-os/cmd/cos/internal/security"
	"luum-agent-os/cmd/cos/internal/ui"
)

var publishCmd = &cobra.Command{
	Use:   "publish",
	Short: "Validate and prepare package for publishing",
	Long: `Validate the current directory as a cos package and prepare for publishing.

Steps:
  1. Validate cos-package.yaml
  2. Run security self-audit
  3. Check publish configuration
  4. Suggest git tag creation`,
	RunE: runPublish,
}

func init() {
	rootCmd.AddCommand(publishCmd)
}

func runPublish(cmd *cobra.Command, args []string) error {
	cwd, err := os.Getwd()
	if err != nil {
		return fmt.Errorf("getting working directory: %w", err)
	}

	manifestPath := filepath.Join(cwd, "cos-package.yaml")

	// Step 1: Parse manifest.
	ui.Step(ui.IconInfo, "Parsing cos-package.yaml...")

	m, err := manifest.ParseFile(manifestPath)
	if err != nil {
		fmt.Println(ui.ErrorStyle.Render(fmt.Sprintf("%s Cannot read cos-package.yaml: %s", ui.IconError, err)))
		os.Exit(1)
	}

	// Step 2: Validate manifest.
	ui.Step(ui.IconInfo, "Validating manifest...")

	validationErrors := manifest.Validate(m)
	if len(validationErrors) > 0 {
		fmt.Println()
		fmt.Println(ui.ErrorStyle.Render(fmt.Sprintf("%s Validation failed with %d error(s):", ui.IconError, len(validationErrors))))
		for _, ve := range validationErrors {
			fmt.Printf("  %s %s: %s\n", ui.IconBullet, ui.HeaderStyle.Render(ve.Field), ve.Message)
		}
		os.Exit(1)
	}
	ui.Step(ui.IconSuccess, "Manifest is valid")

	// Step 3: Run security audit.
	ui.Step(ui.IconInfo, "Running security audit...")

	audit := security.RunAudit(cwd, m.License)
	printAuditReport(audit)

	if !audit.Passed {
		fmt.Println()
		fmt.Println(ui.ErrorStyle.Render(fmt.Sprintf("%s Security audit failed. Fix the issues above before publishing.", ui.IconError)))
		os.Exit(1)
	}
	fmt.Println()
	ui.Step(ui.IconSuccess, "Security audit passed")

	// Step 4: Check git tag status.
	fmt.Println()
	ui.Step(ui.IconInfo, "Checking git tag status...")

	tagExists := gitTagExists(fmt.Sprintf("v%s", m.Version))
	if tagExists {
		ui.Step(ui.IconWarning, fmt.Sprintf("Git tag v%s already exists", m.Version))
		fmt.Println()
		fmt.Println(ui.MutedStyle.Render("  Consider bumping the version in cos-package.yaml"))
	} else {
		ui.Step(ui.IconInfo, fmt.Sprintf("Git tag v%s does not exist yet", m.Version))
	}

	// Step 5: Show publish summary.
	fmt.Println()
	lines := []string{
		fmt.Sprintf("Package:  %s", m.Name),
		fmt.Sprintf("Version:  %s", m.Version),
		fmt.Sprintf("License:  %s", m.License),
		fmt.Sprintf("Exports:  %d component(s)", len(m.Exports)),
	}

	if len(m.Provides) > 0 {
		lines = append(lines, fmt.Sprintf("Provides: %s", strings.Join(m.Provides, ", ")))
	}

	ui.Summary("Publish Summary", lines)

	// Step 6: Show next steps.
	if !tagExists {
		fmt.Println()
		ui.Step(ui.IconArrow, "Next steps:")
		fmt.Printf("  1. %s\n", ui.InfoStyle.Render(fmt.Sprintf("git tag v%s", m.Version)))
		fmt.Printf("  2. %s\n", ui.InfoStyle.Render("git push --tags"))
		fmt.Println()
		fmt.Println(ui.MutedStyle.Render("  After pushing the tag, users can install with:"))
		fmt.Printf("  %s\n", ui.HeaderStyle.Render(fmt.Sprintf("cos install %s@%s", m.Name, m.Version)))
	}

	return nil
}

// gitTagExists checks if a git tag with the given name already exists.
func gitTagExists(tag string) bool {
	cmd := exec.Command("git", "tag", "-l", tag)
	output, err := cmd.Output()
	if err != nil {
		return false
	}
	return strings.TrimSpace(string(output)) == tag
}
