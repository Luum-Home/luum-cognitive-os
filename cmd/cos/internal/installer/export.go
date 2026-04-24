package installer

import (
	"fmt"
	"io"
	"os"
	"path/filepath"
	"strings"

	"luum-agent-os/cmd/cos/internal/manifest"
)

// ExportTarget maps an export to its destination path.
type ExportTarget struct {
	Export manifest.Export
	Source string // absolute source path in fetched dir
	Target string // absolute target path in project
}

// ResolveTargets maps all exports to their destination paths.
// projectRoot is the root of the target project.
// packageDir is the fetched package directory.
// packageName is used for namespacing (cos/{name}/).
func ResolveTargets(exports []manifest.Export, projectRoot, packageDir, packageName string) ([]ExportTarget, error) {
	var targets []ExportTarget

	for _, exp := range exports {
		source := filepath.Join(packageDir, exp.Source)

		// Verify the source file exists.
		if _, err := os.Stat(source); err != nil {
			return nil, fmt.Errorf("export source %q does not exist: %w", exp.Source, err)
		}

		resolvedTargets, err := resolveTargetsForExport(exp, projectRoot, packageName)
		if err != nil {
			return nil, fmt.Errorf("resolving target for %q: %w", exp.Source, err)
		}

		for _, target := range resolvedTargets {
			targets = append(targets, ExportTarget{
				Export: exp,
				Source: source,
				Target: target,
			})
		}
	}

	return targets, nil
}

// resolveTargetsForExport computes all destination paths for an export.
//
// Skills and rules are written additively to:
//  1. the canonical .cognitive-os source-of-truth
//  2. the active Claude projection
//
// Other export types still have a single destination.
func resolveTargetsForExport(exp manifest.Export, projectRoot, packageName string) ([]string, error) {
	switch exp.Type {
	case "skill":
		return resolveSkillTargets(exp.Source, projectRoot, packageName), nil
	case "rule":
		filename := filepath.Base(exp.Source)
		return []string{
			filepath.Join(canonicalRulesDir(projectRoot), packageName, filename),
			filepath.Join(claudeRulesProjectionDir(projectRoot), packageName, filename),
		}, nil
	case "hook":
		filename := filepath.Base(exp.Source)
		return []string{filepath.Join(projectRoot, ".cognitive-os", "hooks", "cos", packageName, filename)}, nil
	case "template":
		filename := filepath.Base(exp.Source)
		return []string{filepath.Join(projectRoot, ".cognitive-os", "templates", packageName, filename)}, nil
	case "agent":
		filename := filepath.Base(exp.Source)
		return []string{filepath.Join(projectRoot, ".cognitive-os", "agents", packageName, filename)}, nil
	default:
		return nil, fmt.Errorf("unsupported export type %q", exp.Type)
	}
}

// resolveSkillTargets handles skill exports by preserving the skill directory name
// across both the canonical source-of-truth and the Claude projection.
func resolveSkillTargets(source, projectRoot, packageName string) []string {
	canonicalRoot := canonicalSkillsDir(projectRoot)
	projectionRoot := claudeSkillsProjectionDir(projectRoot)
	// Normalize path separators.
	normalized := filepath.ToSlash(source)

	// Check if it has a skills/*/SKILL.md structure.
	parts := strings.Split(normalized, "/")
	if len(parts) >= 3 && parts[0] == "skills" {
		relPath := strings.Join(parts[1:], string(filepath.Separator))
		return []string{
			filepath.Join(canonicalRoot, relPath),
			filepath.Join(projectionRoot, relPath),
		}
	}

	if len(parts) == 2 && parts[0] == "skills" {
		return []string{
			filepath.Join(canonicalRoot, packageName, parts[1]),
			filepath.Join(projectionRoot, packageName, parts[1]),
		}
	}

	return []string{
		filepath.Join(canonicalRoot, packageName, filepath.Base(source)),
		filepath.Join(projectionRoot, packageName, filepath.Base(source)),
	}
}

// Install copies all export targets to their destinations.
// Creates directories as needed. Preserves file permissions.
func Install(targets []ExportTarget) error {
	for _, t := range targets {
		// Create the target directory.
		targetDir := filepath.Dir(t.Target)
		if err := os.MkdirAll(targetDir, 0755); err != nil {
			return fmt.Errorf("creating directory %q: %w", targetDir, err)
		}

		if err := copyFile(t.Source, t.Target); err != nil {
			return fmt.Errorf("copying %q to %q: %w", t.Source, t.Target, err)
		}
	}

	return nil
}

// Uninstall removes all files at the target paths.
// Also removes empty parent directories.
func Uninstall(targets []ExportTarget) error {
	for _, t := range targets {
		if err := os.Remove(t.Target); err != nil && !os.IsNotExist(err) {
			return fmt.Errorf("removing %q: %w", t.Target, err)
		}

		// Remove empty parent directories up to the project root.
		cleanEmptyDirs(filepath.Dir(t.Target))
	}

	return nil
}

// copyFile copies a file from src to dst, preserving permissions.
func copyFile(src, dst string) error {
	srcFile, err := os.Open(src)
	if err != nil {
		return err
	}
	defer srcFile.Close()

	srcInfo, err := srcFile.Stat()
	if err != nil {
		return err
	}

	dstFile, err := os.OpenFile(dst, os.O_WRONLY|os.O_CREATE|os.O_TRUNC, srcInfo.Mode())
	if err != nil {
		return err
	}
	defer dstFile.Close()

	if _, err := io.Copy(dstFile, srcFile); err != nil {
		return err
	}

	return dstFile.Close()
}

// cleanEmptyDirs removes empty directories walking upward.
// Stops at the first non-empty directory or on error.
func cleanEmptyDirs(dir string) {
	for {
		entries, err := os.ReadDir(dir)
		if err != nil || len(entries) > 0 {
			return
		}

		if err := os.Remove(dir); err != nil {
			return
		}

		parent := filepath.Dir(dir)
		if parent == dir {
			return
		}
		dir = parent
	}
}
