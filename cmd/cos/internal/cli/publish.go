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
  2. Check for README.md
  3. Run security self-audit
  4. Check publish configuration
  5. Suggest git tag creation (use --push to auto-push)`,
	RunE: runPublish,
}

func init() {
	publishCmd.Flags().Bool("push", false, "Run git push && git push --tags after creating the tag")
	publishCmd.Flags().Bool("dry-run", false, "Show what would be done without executing")
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

	// Step 1b: Check for README.md.
	readmePath := filepath.Join(cwd, "README.md")
	if _, err := os.Stat(readmePath); os.IsNotExist(err) {
		ui.Step(ui.IconWarning, "No README.md found in package directory — consider adding one for registry discovery")
	} else {
		ui.Step(ui.IconSuccess, "README.md found")
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

	tagName := scopedTagName(m.Name, m.Version)
	tagExists := gitTagExists(tagName)
	if tagExists {
		ui.Step(ui.IconWarning, fmt.Sprintf("Git tag %s already exists", tagName))
		fmt.Println()
		fmt.Println(ui.MutedStyle.Render("  Consider bumping the version in cos-package.yaml"))
	} else {
		ui.Step(ui.IconInfo, fmt.Sprintf("Git tag %s does not exist yet", tagName))
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

	// Step 6: Handle --push or show next steps.
	dryRun, _ := cmd.Flags().GetBool("dry-run")
	pushFlag, _ := cmd.Flags().GetBool("push")

	if !tagExists && !dryRun {
		if pushFlag {
			// Create tag and push automatically.
			fmt.Println()
			ui.Step(ui.IconInfo, fmt.Sprintf("Creating git tag %s...", tagName))

			tagCmd := exec.Command("git", "tag", tagName)
			if out, err := tagCmd.CombinedOutput(); err != nil {
				return fmt.Errorf("creating git tag: %s\n%s", err, string(out))
			}
			ui.Step(ui.IconSuccess, fmt.Sprintf("Created git tag %s", tagName))

			ui.Step(ui.IconInfo, "Pushing to remote...")
			pushCmd := exec.Command("git", "push")
			if out, err := pushCmd.CombinedOutput(); err != nil {
				return fmt.Errorf("git push: %s\n%s", err, string(out))
			}

			pushTagsCmd := exec.Command("git", "push", "--tags")
			if out, err := pushTagsCmd.CombinedOutput(); err != nil {
				return fmt.Errorf("git push --tags: %s\n%s", err, string(out))
			}
			ui.Step(ui.IconSuccess, "Pushed commits and tags to remote")
		} else {
			fmt.Println()
			ui.Step(ui.IconArrow, "Next steps:")
			fmt.Printf("  1. %s\n", ui.InfoStyle.Render(fmt.Sprintf("git tag %s", tagName)))
			fmt.Printf("  2. %s\n", ui.InfoStyle.Render("git push --tags"))
			fmt.Println()
			fmt.Println(ui.MutedStyle.Render("  Or use --push to do this automatically:"))
			fmt.Printf("  %s\n", ui.InfoStyle.Render(fmt.Sprintf("cos publish --push")))
		}
	}

	if dryRun {
		fmt.Println()
		ui.Step(ui.IconInfo, "dry run — no tag created, no push executed")
	}

	// Step 7: GitHub topic suggestion.
	fmt.Println()
	fmt.Println(ui.MutedStyle.Render("  Tip: Add topic 'cos-package' to your repo for registry discovery"))
	fmt.Println()
	fmt.Println(ui.MutedStyle.Render("  After publishing, users can install with:"))
	fmt.Printf("  %s\n", ui.HeaderStyle.Render(fmt.Sprintf("cos install %s@%s", m.Name, m.Version)))

	return nil
}

// scopedTagName builds a scoped tag like "@luum/name@1.0.0" for package
// publishing. This matches the cos install convention where packages are
// referenced as @scope/name@version.
func scopedTagName(name, version string) string {
	return fmt.Sprintf("%s@%s", name, version)
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
