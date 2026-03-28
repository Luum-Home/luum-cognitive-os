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

	"luum-agent-os/cmd/cos/internal/project"
	"luum-agent-os/cmd/cos/internal/ui"
)

var (
	releasePatch  bool
	releaseMinor  bool
	releaseMajor  bool
	releaseDryRun bool
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
  cos release --dry-run      Show what would happen`,
	RunE: runRelease,
}

func init() {
	releaseCmd.Flags().BoolVar(&releasePatch, "patch", false, "Bump patch version")
	releaseCmd.Flags().BoolVar(&releaseMinor, "minor", false, "Bump minor version")
	releaseCmd.Flags().BoolVar(&releaseMajor, "major", false, "Bump major version")
	releaseCmd.Flags().BoolVar(&releaseDryRun, "dry-run", false, "Show what would happen without making changes")
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

func runRelease(cmd *cobra.Command, args []string) error {
	projectRoot := project.FindRootOrCwd()
	currentVersion := readVersionFile(projectRoot)
	if currentVersion == "unknown" {
		return fmt.Errorf("VERSION file not found in %s", projectRoot)
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
		fmt.Printf("    3. git commit -m \"release: v%s\"\n", targetVersion)
		fmt.Printf("    4. git tag v%s\n", targetVersion)
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

	// Step 3: Git commit.
	gitAdd := exec.Command("git", "add", "VERSION", "CHANGELOG.md")
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
