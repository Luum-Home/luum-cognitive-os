package cli

import (
	"bufio"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"time"

	"github.com/spf13/cobra"

	"luum-agent-os/cmd/cos/internal/manifest"
	"luum-agent-os/cmd/cos/internal/project"
	"luum-agent-os/cmd/cos/internal/ui"

	"gopkg.in/yaml.v3"
)

var (
	releaseAllPatch     bool
	releaseAllMinor     bool
	releaseAllMajor     bool
	releaseAllDryRun    bool
	releaseAllYes       bool
	releaseAllInclude   string
	releaseAllExclude   string
	releaseAllChangelog bool
)

var releaseAllCmd = &cobra.Command{
	Use:   "release-all",
	Short: "Release all packages with unreleased changes",
	Long: `Find packages with unreleased changes, bump their versions, commit, and tag.

Creates one commit with all version bumps and individual scoped git tags
for each released package.

Examples:
  cos release-all --patch          Bump patch version on changed packages
  cos release-all --minor          Bump minor version on changed packages
  cos release-all --dry-run        Show what would happen
  cos release-all --include "quality-gates,trust-system"
  cos release-all --exclude "sdd-compound"
  cos release-all --patch --yes    Skip confirmation prompt
  cos release-all --patch --changelog  Write per-package CHANGELOG.md files`,
	RunE: runReleaseAll,
}

func init() {
	releaseAllCmd.Flags().BoolVar(&releaseAllPatch, "patch", false, "Bump patch version (default)")
	releaseAllCmd.Flags().BoolVar(&releaseAllMinor, "minor", false, "Bump minor version")
	releaseAllCmd.Flags().BoolVar(&releaseAllMajor, "major", false, "Bump major version")
	releaseAllCmd.Flags().BoolVar(&releaseAllDryRun, "dry-run", false, "Show what would happen without making changes")
	releaseAllCmd.Flags().BoolVar(&releaseAllYes, "yes", false, "Skip confirmation prompt")
	releaseAllCmd.Flags().StringVar(&releaseAllInclude, "include", "", "Comma-separated package names to include (substring match)")
	releaseAllCmd.Flags().StringVar(&releaseAllExclude, "exclude", "", "Comma-separated package names to exclude (substring match)")
	releaseAllCmd.Flags().BoolVar(&releaseAllChangelog, "changelog", false, "Write per-package CHANGELOG.md files")
	rootCmd.AddCommand(releaseAllCmd)
}

// releaseAllPlan holds the plan for a single package release.
type releaseAllPlan struct {
	Name       string
	OldVersion string
	NewVersion string
	TagName    string
	PkgDir     string   // relative path from project root, e.g. "packages/quality-gates"
	Commits    []string // commit messages since last tag
}

func runReleaseAll(cmd *cobra.Command, args []string) error {
	projectRoot := project.FindRootOrCwd()

	// Validate bump flags.
	bumpCount := 0
	if releaseAllMajor {
		bumpCount++
	}
	if releaseAllMinor {
		bumpCount++
	}
	if releaseAllPatch {
		bumpCount++
	}
	if bumpCount > 1 {
		return fmt.Errorf("specify only one bump flag: --patch, --minor, or --major")
	}
	// Default to patch if no bump flag specified.
	if bumpCount == 0 {
		releaseAllPatch = true
	}

	// Safety: require clean git working tree.
	if !releaseAllDryRun {
		if err := requireCleanGit(projectRoot); err != nil {
			return err
		}
	}

	// Discover packages and filter to those with changes.
	statuses, err := discoverPackages(projectRoot)
	if err != nil {
		return err
	}

	// Filter to changed packages.
	var changed []PackageStatus
	for _, s := range statuses {
		if !s.HasChanges {
			continue
		}
		if !matchesFilter(s.Name, releaseAllInclude, releaseAllExclude) {
			continue
		}
		changed = append(changed, s)
	}

	if len(changed) == 0 {
		fmt.Println("No packages with unreleased changes found.")
		return nil
	}

	// Build release plan.
	var plans []releaseAllPlan
	for _, s := range changed {
		newVersion, err := bumpVersion(s.Version, releaseAllMajor, releaseAllMinor, releaseAllPatch)
		if err != nil {
			return fmt.Errorf("bumping version for %s: %w", s.Name, err)
		}

		// Find the package directory by scanning packages/.
		pkgDir, err := findPackageDir(projectRoot, s.Name)
		if err != nil {
			return fmt.Errorf("finding directory for %s: %w", s.Name, err)
		}

		// Fetch commit messages for this package since last tag.
		lastTag := scopedTagName(s.Name, s.Version)
		commits, _ := getPackageCommits(projectRoot, pkgDir, lastTag)

		plans = append(plans, releaseAllPlan{
			Name:       s.Name,
			OldVersion: s.Version,
			NewVersion: newVersion,
			TagName:    scopedTagName(s.Name, newVersion),
			PkgDir:     pkgDir,
			Commits:    commits,
		})
	}

	// Show plan.
	fmt.Println()
	fmt.Printf("%s Release plan (%d packages):\n\n", ui.IconInfo, len(plans))

	for _, p := range plans {
		commitInfo := ""
		if len(p.Commits) > 0 {
			commitInfo = fmt.Sprintf("  (%d commits)", len(p.Commits))
		}
		fmt.Printf("  %s  %s  %s -> %s  (tag: %s)%s\n",
			ui.IconArrow,
			ui.HeaderStyle.Render(p.Name),
			p.OldVersion,
			ui.SuccessStyle.Render(p.NewVersion),
			p.TagName,
			commitInfo,
		)
	}

	if releaseAllDryRun {
		// Show per-package changelogs in dry-run mode.
		printPackageChangelogs(plans)
		fmt.Println()
		fmt.Println(ui.MutedStyle.Render("  No changes made (dry run)"))
		return nil
	}

	// Confirm unless --yes.
	if !releaseAllYes {
		fmt.Println()
		fmt.Print("  Proceed? [y/N] ")
		reader := bufio.NewReader(os.Stdin)
		answer, _ := reader.ReadString('\n')
		answer = strings.TrimSpace(strings.ToLower(answer))
		if answer != "y" && answer != "yes" {
			fmt.Println("  Aborted.")
			return nil
		}
	}

	// Execute: bump versions in cos-package.yaml files.
	var modifiedFiles []string
	for _, p := range plans {
		manifestPath := filepath.Join(projectRoot, p.PkgDir, "cos-package.yaml")
		if err := updateManifestVersion(manifestPath, p.NewVersion); err != nil {
			return fmt.Errorf("updating %s: %w", p.Name, err)
		}
		modifiedFiles = append(modifiedFiles, filepath.Join(p.PkgDir, "cos-package.yaml"))
		fmt.Printf("  %s %s -> %s\n", ui.IconCheck, p.Name, p.NewVersion)
	}

	// Git add all modified files.
	gitAddArgs := append([]string{"add"}, modifiedFiles...)
	gitAdd := exec.Command("git", gitAddArgs...)
	gitAdd.Dir = projectRoot
	if out, err := gitAdd.CombinedOutput(); err != nil {
		return fmt.Errorf("git add failed: %w\n%s", err, string(out))
	}

	// Create one commit with all changes.
	commitMsg := buildReleaseAllCommitMsg(plans)
	gitCommit := exec.Command("git", "commit", "-m", commitMsg)
	gitCommit.Dir = projectRoot
	if out, err := gitCommit.CombinedOutput(); err != nil {
		return fmt.Errorf("git commit failed: %w\n%s", err, string(out))
	}
	fmt.Printf("\n  %s Committed: %s\n", ui.IconCheck, strings.Split(commitMsg, "\n")[0])

	// Create scoped tags for each package.
	for _, p := range plans {
		gitTag := exec.Command("git", "tag", p.TagName)
		gitTag.Dir = projectRoot
		if out, err := gitTag.CombinedOutput(); err != nil {
			return fmt.Errorf("git tag %s failed: %w\n%s", p.TagName, err, string(out))
		}
		fmt.Printf("  %s Tagged: %s\n", ui.IconCheck, p.TagName)
	}

	// Write per-package CHANGELOG.md files if --changelog is set.
	if releaseAllChangelog {
		for _, p := range plans {
			changelogPath := filepath.Join(projectRoot, p.PkgDir, "CHANGELOG.md")
			if err := writePackageChangelog(changelogPath, p.Name, p.NewVersion, p.Commits); err != nil {
				fmt.Printf("  %s Failed to write changelog for %s: %v\n", ui.IconWarning, p.Name, err)
			}
		}
		fmt.Printf("\n  %s Per-package changelogs written to packages/*/CHANGELOG.md\n", ui.IconCheck)
	}

	// Print summary report with commit counts.
	fmt.Println()
	fmt.Printf("%s Released %d packages:\n", ui.IconSuccess, len(plans))
	for _, p := range plans {
		commitInfo := ""
		if len(p.Commits) > 0 {
			commitInfo = fmt.Sprintf("  (%d commits)", len(p.Commits))
		}
		fmt.Printf("  %-40s %s -> %s%s\n", p.Name, p.OldVersion, p.NewVersion, commitInfo)
	}
	fmt.Println()
	fmt.Printf("  Push with: git push && git push --tags\n")

	return nil
}

// requireCleanGit checks that the git working tree has no uncommitted changes.
func requireCleanGit(projectRoot string) error {
	cmd := exec.Command("git", "status", "--porcelain")
	cmd.Dir = projectRoot
	out, err := cmd.Output()
	if err != nil {
		return fmt.Errorf("checking git status: %w", err)
	}
	if len(strings.TrimSpace(string(out))) > 0 {
		return fmt.Errorf("working tree is dirty — commit or stash changes before releasing")
	}
	return nil
}

// matchesFilter checks if a package name matches include/exclude filters.
// Both filters use substring matching on comma-separated values.
func matchesFilter(name, include, exclude string) bool {
	if exclude != "" {
		for _, pattern := range strings.Split(exclude, ",") {
			pattern = strings.TrimSpace(pattern)
			if pattern != "" && strings.Contains(name, pattern) {
				return false
			}
		}
	}
	if include != "" {
		for _, pattern := range strings.Split(include, ",") {
			pattern = strings.TrimSpace(pattern)
			if pattern != "" && strings.Contains(name, pattern) {
				return true
			}
		}
		return false
	}
	return true
}

// findPackageDir finds the relative path for a package by its name.
func findPackageDir(projectRoot, name string) (string, error) {
	packagesDir := filepath.Join(projectRoot, "packages")
	entries, err := os.ReadDir(packagesDir)
	if err != nil {
		return "", err
	}

	for _, entry := range entries {
		if !entry.IsDir() {
			continue
		}
		manifestPath := filepath.Join(packagesDir, entry.Name(), "cos-package.yaml")
		m, err := manifest.ParseFile(manifestPath)
		if err != nil {
			continue
		}
		if m.Name == name {
			return filepath.Join("packages", entry.Name()), nil
		}
	}

	return "", fmt.Errorf("package %q not found in packages/", name)
}

// updateManifestVersion reads a cos-package.yaml file, updates the version field,
// and writes it back. Uses raw YAML node manipulation to preserve formatting.
func updateManifestVersion(path, newVersion string) error {
	data, err := os.ReadFile(path)
	if err != nil {
		return fmt.Errorf("reading %s: %w", path, err)
	}

	var doc yaml.Node
	if err := yaml.Unmarshal(data, &doc); err != nil {
		return fmt.Errorf("parsing %s: %w", path, err)
	}

	// The root is a document node; the first content node is the mapping.
	if doc.Kind != yaml.DocumentNode || len(doc.Content) == 0 {
		return fmt.Errorf("unexpected YAML structure in %s", path)
	}

	mapping := doc.Content[0]
	if mapping.Kind != yaml.MappingNode {
		return fmt.Errorf("expected mapping node in %s", path)
	}

	// Find the "version" key and update its value.
	for i := 0; i < len(mapping.Content)-1; i += 2 {
		if mapping.Content[i].Value == "version" {
			mapping.Content[i+1].Value = newVersion
			break
		}
	}

	out, err := yaml.Marshal(&doc)
	if err != nil {
		return fmt.Errorf("marshaling %s: %w", path, err)
	}

	return os.WriteFile(path, out, 0644)
}

// getPackageCommits returns commit messages for a specific package since a given tag.
// If the tag does not exist, it returns all commits affecting the package directory.
func getPackageCommits(projectRoot, pkgDir, lastTag string) ([]string, error) {
	var args []string
	if lastTag != "" && gitTagExistsInDir(projectRoot, lastTag) {
		args = []string{"log", "--oneline", "--no-decorate", lastTag + "..HEAD", "--", pkgDir}
	} else {
		args = []string{"log", "--oneline", "--no-decorate", "--", pkgDir}
	}

	cmd := exec.Command("git", args...)
	cmd.Dir = projectRoot
	out, err := cmd.Output()
	if err != nil {
		return nil, fmt.Errorf("git log: %w", err)
	}

	raw := strings.TrimSpace(string(out))
	if raw == "" {
		return nil, nil
	}

	var commits []string
	for _, line := range strings.Split(raw, "\n") {
		line = strings.TrimSpace(line)
		if line == "" {
			continue
		}
		// Strip the short hash prefix (first word).
		if idx := strings.IndexByte(line, ' '); idx >= 0 {
			commits = append(commits, strings.TrimSpace(line[idx+1:]))
		} else {
			commits = append(commits, line)
		}
	}
	return commits, nil
}

// generatePackageChangelog formats a list of commits as a markdown changelog
// section for a given package version.
func generatePackageChangelog(name, version string, commits []string) string {
	today := time.Now().Format("2006-01-02")
	var sb strings.Builder
	sb.WriteString(fmt.Sprintf("## [%s] - %s\n", version, today))
	if len(commits) == 0 {
		sb.WriteString("- Version bump (no notable changes)\n")
	} else {
		for _, c := range commits {
			sb.WriteString(fmt.Sprintf("- %s\n", c))
		}
	}
	return sb.String()
}

// writePackageChangelog creates or prepends to a CHANGELOG.md file in the package directory.
func writePackageChangelog(path, name, version string, commits []string) error {
	newSection := generatePackageChangelog(name, version, commits)

	existing, err := os.ReadFile(path)
	if err != nil {
		// File does not exist; create from scratch.
		header := fmt.Sprintf("# Changelog — %s\n\n", name)
		return os.WriteFile(path, []byte(header+newSection), 0644)
	}

	// Insert the new section after the first heading line.
	content := string(existing)
	// Find the position after the first line (the # heading).
	if idx := strings.Index(content, "\n"); idx >= 0 {
		// Insert after the heading + a blank line.
		before := content[:idx+1]
		after := content[idx+1:]
		// Skip any leading blank lines after the heading.
		trimmedAfter := strings.TrimLeft(after, "\n")
		updated := before + "\n" + newSection + "\n" + trimmedAfter
		return os.WriteFile(path, []byte(updated), 0644)
	}

	// Fallback: just prepend.
	return os.WriteFile(path, []byte(content+"\n"+newSection), 0644)
}

// printPackageChangelogs prints per-package commit details to stdout.
func printPackageChangelogs(plans []releaseAllPlan) {
	hasCommits := false
	for _, p := range plans {
		if len(p.Commits) > 0 {
			hasCommits = true
			break
		}
	}
	if !hasCommits {
		return
	}

	fmt.Println()
	fmt.Printf("%s Per-package changes:\n", ui.IconInfo)
	for _, p := range plans {
		if len(p.Commits) == 0 {
			continue
		}
		fmt.Printf("\n  %s %s -> %s\n",
			ui.HeaderStyle.Render(p.Name),
			p.OldVersion,
			ui.SuccessStyle.Render(p.NewVersion),
		)
		for _, c := range p.Commits {
			fmt.Printf("    %s %s\n", ui.IconBullet, c)
		}
	}
}

// buildReleaseAllCommitMsg creates a commit message summarizing all package releases.
func buildReleaseAllCommitMsg(plans []releaseAllPlan) string {
	if len(plans) == 1 {
		return fmt.Sprintf("release: %s@%s", plans[0].Name, plans[0].NewVersion)
	}

	var sb strings.Builder
	sb.WriteString(fmt.Sprintf("release: %d packages\n\n", len(plans)))
	for _, p := range plans {
		sb.WriteString(fmt.Sprintf("- %s %s -> %s\n", p.Name, p.OldVersion, p.NewVersion))
	}
	return sb.String()
}
