package cli

import (
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strconv"
	"strings"
	"time"

	"github.com/spf13/cobra"

	"luum-agent-os/cmd/cos/internal/manifest"
	"luum-agent-os/cmd/cos/internal/project"
	"luum-agent-os/cmd/cos/internal/ui"
)

var (
	releasePatch  bool
	releaseMinor  bool
	releaseMajor  bool
	releaseDryRun bool
	releaseCheck  bool
)

var releaseCmd = &cobra.Command{
	Use:   "release [version]",
	Short: "Create a new release",
	Long: `Create a new OS release: bump VERSION, update CHANGELOG, create git tag.

Examples:
  cos release 0.2.0         Create release v0.2.0
  cos release --patch        Bump patch version
  cos release --minor        Bump minor version
  cos release --major        Bump major version
  cos release --dry-run      Show what would happen
  cos release --check        Validate release readiness without releasing`,
	RunE: runRelease,
}

func init() {
	releaseCmd.Flags().BoolVar(&releasePatch, "patch", false, "Bump patch version")
	releaseCmd.Flags().BoolVar(&releaseMinor, "minor", false, "Bump minor version")
	releaseCmd.Flags().BoolVar(&releaseMajor, "major", false, "Bump major version")
	releaseCmd.Flags().BoolVar(&releaseDryRun, "dry-run", false, "Show what would happen without making changes")
	releaseCmd.Flags().BoolVar(&releaseCheck, "check", false, "Validate release readiness without releasing")
	rootCmd.AddCommand(releaseCmd)
}

// parseSemver splits a version string like "0.1.0" into major, minor, patch.
func parseSemver(version string) (int, int, int, error) {
	version = strings.TrimPrefix(version, "v")
	parts := strings.Split(version, ".")
	if len(parts) != 3 {
		return 0, 0, 0, fmt.Errorf("invalid semver format %q: expected MAJOR.MINOR.PATCH", version)
	}

	major, err := strconv.Atoi(parts[0])
	if err != nil {
		return 0, 0, 0, fmt.Errorf("invalid major version %q: %w", parts[0], err)
	}
	minor, err := strconv.Atoi(parts[1])
	if err != nil {
		return 0, 0, 0, fmt.Errorf("invalid minor version %q: %w", parts[1], err)
	}
	patch, err := strconv.Atoi(parts[2])
	if err != nil {
		return 0, 0, 0, fmt.Errorf("invalid patch version %q: %w", parts[2], err)
	}

	return major, minor, patch, nil
}

// bumpVersion computes the next version based on the bump type.
func bumpVersion(current string, bumpMajor, bumpMinor, bumpPatch bool) (string, error) {
	major, minor, patch, err := parseSemver(current)
	if err != nil {
		return "", err
	}

	switch {
	case bumpMajor:
		major++
		minor = 0
		patch = 0
	case bumpMinor:
		minor++
		patch = 0
	case bumpPatch:
		patch++
	default:
		return "", fmt.Errorf("no bump type specified")
	}

	return fmt.Sprintf("%d.%d.%d", major, minor, patch), nil
}

// updateChangelog renames the [Unreleased] section to [version] - date and adds
// a new empty [Unreleased] section. Returns the updated content.
func updateChangelog(content, version string) string {
	today := time.Now().Format("2006-01-02")
	versionHeader := fmt.Sprintf("## [%s] - %s", version, today)

	// Replace the first occurrence of "## [Unreleased]" with the versioned header
	// preceded by a new [Unreleased] section.
	newUnreleased := "## [Unreleased]\n\n" + versionHeader
	result := strings.Replace(content, "## [Unreleased]", newUnreleased, 1)

	return result
}

// updateDocsIndex replaces the version reference in the first line heading of
// docs/INDEX.md. The expected format is: "# ... — vX.Y.Z"
func updateDocsIndex(content, newVersion string) string {
	lines := strings.SplitN(content, "\n", 2)
	if len(lines) == 0 {
		return content
	}

	heading := lines[0]
	// Find the last occurrence of a version pattern vX.Y.Z in the heading.
	// We search backwards for "v" followed by digits and dots.
	lastV := strings.LastIndex(heading, "v")
	if lastV < 0 {
		return content
	}

	// Extract the rest after 'v' and check it looks like a semver.
	rest := heading[lastV+1:]
	// Find where the version ends (first char that is not digit or dot).
	endIdx := 0
	for endIdx < len(rest) {
		c := rest[endIdx]
		if (c >= '0' && c <= '9') || c == '.' {
			endIdx++
		} else {
			break
		}
	}

	if endIdx == 0 {
		return content
	}

	// Rebuild the heading with the new version.
	newHeading := heading[:lastV] + "v" + newVersion + heading[lastV+1+endIdx:]
	if len(lines) > 1 {
		return newHeading + "\n" + lines[1]
	}
	return newHeading
}

// releaseReadinessCheck validates that the project is ready for a release.
// Returns a list of check results (pass/fail) and an overall pass boolean.
func releaseReadinessCheck(projectRoot, currentVersion string) ([]string, bool) {
	var checks []string
	allPassed := true

	// Check 1: No uncommitted changes.
	statusCmd := exec.Command("git", "status", "--porcelain")
	statusCmd.Dir = projectRoot
	statusOut, err := statusCmd.Output()
	if err != nil {
		checks = append(checks, fmt.Sprintf("%s Git status: could not determine (%v)", ui.IconError, err))
		allPassed = false
	} else if len(strings.TrimSpace(string(statusOut))) > 0 {
		checks = append(checks, fmt.Sprintf("%s No uncommitted changes: FAIL (working tree is dirty)", ui.IconError))
		allPassed = false
	} else {
		checks = append(checks, fmt.Sprintf("%s No uncommitted changes", ui.IconSuccess))
	}

	// Check 2: Version is newer than last git tag.
	lastTagCmd := exec.Command("git", "describe", "--tags", "--abbrev=0")
	lastTagCmd.Dir = projectRoot
	lastTagOut, err := lastTagCmd.Output()
	if err != nil {
		// No tags exist yet — that's fine for a first release.
		checks = append(checks, fmt.Sprintf("%s Version newer than last tag: OK (no previous tags)", ui.IconSuccess))
	} else {
		lastTag := strings.TrimSpace(string(lastTagOut))
		lastTagVersion := strings.TrimPrefix(lastTag, "v")
		// Also handle scoped tags: extract version after last @.
		if idx := strings.LastIndex(lastTag, "@"); idx >= 0 {
			lastTagVersion = lastTag[idx+1:]
		}
		cmp := manifest.CompareVersions(currentVersion, lastTagVersion)
		if cmp > 0 {
			checks = append(checks, fmt.Sprintf("%s Version %s is newer than last tag %s", ui.IconSuccess, currentVersion, lastTag))
		} else {
			checks = append(checks, fmt.Sprintf("%s Version newer than last tag: FAIL (current %s <= tag %s)", ui.IconError, currentVersion, lastTag))
			allPassed = false
		}
	}

	// Check 3: CHANGELOG.md has an [Unreleased] section with content.
	changelogPath := filepath.Join(projectRoot, "CHANGELOG.md")
	changelogData, err := os.ReadFile(changelogPath)
	if err != nil {
		checks = append(checks, fmt.Sprintf("%s CHANGELOG.md: not found", ui.IconError))
		allPassed = false
	} else {
		content := string(changelogData)
		if !strings.Contains(content, "## [Unreleased]") {
			checks = append(checks, fmt.Sprintf("%s CHANGELOG.md: no [Unreleased] section found", ui.IconError))
			allPassed = false
		} else {
			// Check there is content between [Unreleased] and the next ## heading.
			idx := strings.Index(content, "## [Unreleased]")
			rest := content[idx+len("## [Unreleased]"):]
			nextSection := strings.Index(rest, "\n## ")
			var section string
			if nextSection >= 0 {
				section = rest[:nextSection]
			} else {
				section = rest
			}
			trimmed := strings.TrimSpace(section)
			if trimmed == "" {
				checks = append(checks, fmt.Sprintf("%s CHANGELOG.md: [Unreleased] section is empty", ui.IconWarning))
			} else {
				checks = append(checks, fmt.Sprintf("%s CHANGELOG.md has unreleased entries", ui.IconSuccess))
			}
		}
	}

	// Check 4: Tests pass (run go test if go.mod exists, or python tests if pytest exists).
	goModPath := filepath.Join(projectRoot, "cmd", "cos", "go.mod")
	if _, err := os.Stat(goModPath); err == nil {
		testCmd := exec.Command("go", "test", "./...")
		testCmd.Dir = filepath.Join(projectRoot, "cmd", "cos")
		if testOut, err := testCmd.CombinedOutput(); err != nil {
			checks = append(checks, fmt.Sprintf("%s Tests pass: FAIL\n      %s",
				ui.IconError, strings.Split(strings.TrimSpace(string(testOut)), "\n")[0]))
			allPassed = false
		} else {
			checks = append(checks, fmt.Sprintf("%s Tests pass", ui.IconSuccess))
		}
	} else {
		checks = append(checks, fmt.Sprintf("%s Tests: skipped (no go.mod found at cmd/cos/)", ui.IconWarning))
	}

	return checks, allPassed
}

func runRelease(cmd *cobra.Command, args []string) error {
	projectRoot := project.FindRootOrCwd()
	currentVersion := readVersionFile(projectRoot)
	if currentVersion == "unknown" {
		return fmt.Errorf("VERSION file not found in %s", projectRoot)
	}

	// Handle --check: validate release readiness and exit.
	if releaseCheck {
		fmt.Println()
		fmt.Printf("%s Release readiness check (v%s):\n\n", ui.IconInfo, currentVersion)

		checks, allPassed := releaseReadinessCheck(projectRoot, currentVersion)
		for _, c := range checks {
			fmt.Printf("  %s\n", c)
		}

		fmt.Println()
		if allPassed {
			fmt.Println(ui.SuccessStyle.Render(fmt.Sprintf("%s Release readiness: PASS", ui.IconSuccess)))
		} else {
			fmt.Println(ui.ErrorStyle.Render(fmt.Sprintf("%s Release readiness: FAIL — fix issues above before releasing", ui.IconError)))
			os.Exit(1)
		}
		return nil
	}

	// Determine target version.
	var targetVersion string
	bumpCount := 0
	if releaseMajor {
		bumpCount++
	}
	if releaseMinor {
		bumpCount++
	}
	if releasePatch {
		bumpCount++
	}

	if len(args) > 0 && bumpCount > 0 {
		return fmt.Errorf("specify either an explicit version or a bump flag, not both")
	}
	if len(args) == 0 && bumpCount == 0 {
		return fmt.Errorf("specify a version (e.g., cos release 0.2.0) or a bump flag (--patch, --minor, --major)")
	}
	if bumpCount > 1 {
		return fmt.Errorf("specify only one bump flag: --patch, --minor, or --major")
	}

	if len(args) > 0 {
		targetVersion = strings.TrimPrefix(args[0], "v")
		// Validate format.
		if _, _, _, err := parseSemver(targetVersion); err != nil {
			return fmt.Errorf("invalid version %q: %w", args[0], err)
		}
	} else {
		var err error
		targetVersion, err = bumpVersion(currentVersion, releaseMajor, releaseMinor, releasePatch)
		if err != nil {
			return fmt.Errorf("computing next version: %w", err)
		}
	}

	// Dry-run: show plan and exit.
	if releaseDryRun {
		fmt.Println()
		fmt.Printf("%s Release plan:\n", ui.IconInfo)
		fmt.Printf("  Current version: %s\n", currentVersion)
		fmt.Printf("  Target version:  %s\n", targetVersion)
		fmt.Println()
		fmt.Println("  Actions:")
		fmt.Printf("    1. Update VERSION file to %s\n", targetVersion)
		fmt.Println("    2. Update CHANGELOG.md (rename [Unreleased] section)")
		fmt.Printf("    3. Update docs/INDEX.md version to v%s\n", targetVersion)
		fmt.Printf("    4. git commit -m \"release: v%s\"\n", targetVersion)
		fmt.Printf("    5. git tag v%s\n", targetVersion)
		fmt.Println()
		fmt.Println(ui.MutedStyle.Render("  No changes made (dry run)"))
		return nil
	}

	// Step 1: Update VERSION file.
	versionPath := filepath.Join(projectRoot, "VERSION")
	if err := os.WriteFile(versionPath, []byte(targetVersion+"\n"), 0644); err != nil {
		return fmt.Errorf("writing VERSION file: %w", err)
	}
	fmt.Printf("%s Updated VERSION to %s\n", ui.IconCheck, targetVersion)

	// Step 2: Update CHANGELOG.md.
	changelogPath := filepath.Join(projectRoot, "CHANGELOG.md")
	changelogData, err := os.ReadFile(changelogPath)
	if err != nil {
		fmt.Printf("%s CHANGELOG.md not found, skipping changelog update\n", ui.IconWarning)
	} else {
		updated := updateChangelog(string(changelogData), targetVersion)
		if err := os.WriteFile(changelogPath, []byte(updated), 0644); err != nil {
			return fmt.Errorf("writing CHANGELOG.md: %w", err)
		}
		fmt.Printf("%s Updated CHANGELOG.md\n", ui.IconCheck)
	}

	// Step 2b: Update docs/INDEX.md version reference.
	docsIndexPath := filepath.Join(projectRoot, "docs", "INDEX.md")
	docsIndexData, err := os.ReadFile(docsIndexPath)
	if err != nil {
		fmt.Printf("%s docs/INDEX.md not found, skipping version update\n", ui.IconWarning)
	} else {
		updated := updateDocsIndex(string(docsIndexData), targetVersion)
		if err := os.WriteFile(docsIndexPath, []byte(updated), 0644); err != nil {
			return fmt.Errorf("writing docs/INDEX.md: %w", err)
		}
		fmt.Printf("%s Updated docs/INDEX.md version to v%s\n", ui.IconCheck, targetVersion)
	}

	// Step 3: Git commit.
	gitAdd := exec.Command("git", "add", "VERSION", "CHANGELOG.md", "docs/INDEX.md")
	gitAdd.Dir = projectRoot
	if out, err := gitAdd.CombinedOutput(); err != nil {
		return fmt.Errorf("git add failed: %w\n%s", err, string(out))
	}

	commitMsg := fmt.Sprintf("release: v%s", targetVersion)
	gitCommit := exec.Command("git", "commit", "-m", commitMsg)
	gitCommit.Dir = projectRoot
	if out, err := gitCommit.CombinedOutput(); err != nil {
		return fmt.Errorf("git commit failed: %w\n%s", err, string(out))
	}
	fmt.Printf("%s Committed: %s\n", ui.IconCheck, commitMsg)

	// Step 4: Git tag.
	tagName := fmt.Sprintf("v%s", targetVersion)
	gitTag := exec.Command("git", "tag", tagName)
	gitTag.Dir = projectRoot
	if out, err := gitTag.CombinedOutput(); err != nil {
		return fmt.Errorf("git tag failed: %w\n%s", err, string(out))
	}
	fmt.Printf("%s Tagged: %s\n", ui.IconCheck, tagName)

	fmt.Println()
	fmt.Printf("%s Release v%s created.\n", ui.IconSuccess, targetVersion)
	fmt.Printf("  Push with: git push && git push --tags\n")

	return nil
}
