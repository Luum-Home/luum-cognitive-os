package cli

import (
	"bufio"
	"fmt"
	"os"
	"path/filepath"
	"strings"

	"github.com/spf13/cobra"
	"gopkg.in/yaml.v3"

	"luum-agent-os/cmd/cos/internal/manifest"
	"luum-agent-os/cmd/cos/internal/ui"
)

var initCmd = &cobra.Command{
	Use:   "init",
	Short: "Create a new cos-package.yaml",
	Long:  "Interactively generate a cos-package.yaml manifest in the current directory.",
	RunE:  runInit,
}

func init() {
	rootCmd.AddCommand(initCmd)
}

func runInit(cmd *cobra.Command, args []string) error {
	cwd, err := os.Getwd()
	if err != nil {
		return fmt.Errorf("getting working directory: %w", err)
	}

	target := filepath.Join(cwd, "cos-package.yaml")
	if _, err := os.Stat(target); err == nil {
		fmt.Println(ui.WarningStyle.Render("cos-package.yaml already exists in this directory."))
		fmt.Print("Overwrite? [y/N] ")
		reader := bufio.NewReader(os.Stdin)
		answer, _ := reader.ReadString('\n')
		answer = strings.TrimSpace(strings.ToLower(answer))
		if answer != "y" && answer != "yes" {
			fmt.Println("Aborted.")
			return nil
		}
	}

	reader := bufio.NewReader(os.Stdin)

	fmt.Println(ui.TitleStyle.Render("cos init — Create a new package manifest"))
	fmt.Println()

	// Package name.
	dirName := filepath.Base(cwd)
	name := prompt(reader, "Package name", dirName)

	// Version.
	version := prompt(reader, "Version", "0.1.0")

	// Description.
	description := prompt(reader, "Description", "")

	// Author.
	author := prompt(reader, "Author", "")

	// License.
	license := prompt(reader, "License (SPDX)", "MIT")

	// Auto-detect exports.
	exports := detectExports(cwd)

	// Determine provides from exports.
	provides := deriveProvides(exports)
	if len(provides) == 0 {
		provides = []string{"skill"}
	}

	// Build manifest.
	m := manifest.Manifest{
		Name:        name,
		Version:     version,
		Description: description,
		License:     license,
		Provides:    provides,
		Exports:     exports,
	}
	if author != "" {
		m.Authors = []string{author}
	}

	// Write YAML.
	data, err := yaml.Marshal(&m)
	if err != nil {
		return fmt.Errorf("marshaling manifest: %w", err)
	}

	if err := os.WriteFile(target, data, 0644); err != nil {
		return fmt.Errorf("writing cos-package.yaml: %w", err)
	}

	fmt.Println()
	fmt.Println(ui.SuccessStyle.Render(fmt.Sprintf("%s Created cos-package.yaml", ui.IconCheck)))

	// Show validation results.
	errs := manifest.Validate(&m)
	if len(errs) > 0 {
		fmt.Println()
		fmt.Println(ui.WarningStyle.Render("Validation warnings:"))
		for _, e := range errs {
			fmt.Printf("  %s %s\n", ui.IconBullet, e.Error())
		}
	}

	return nil
}

func prompt(reader *bufio.Reader, label, defaultVal string) string {
	if defaultVal != "" {
		fmt.Printf("%s [%s]: ", ui.HeaderStyle.Render(label), defaultVal)
	} else {
		fmt.Printf("%s: ", ui.HeaderStyle.Render(label))
	}

	input, _ := reader.ReadString('\n')
	input = strings.TrimSpace(input)
	if input == "" {
		return defaultVal
	}
	return input
}

func detectExports(dir string) []manifest.Export {
	var exports []manifest.Export

	// Detect skills (directories containing SKILL.md).
	skillDirs := findFiles(dir, "skills/*/SKILL.md")
	for _, path := range skillDirs {
		rel, _ := filepath.Rel(dir, path)
		exports = append(exports, manifest.Export{
			Source: rel,
			Type:   "skill",
		})
	}

	// Detect standalone SKILL.md in root.
	if _, err := os.Stat(filepath.Join(dir, "SKILL.md")); err == nil {
		exports = append(exports, manifest.Export{
			Source: "SKILL.md",
			Type:   "skill",
		})
	}

	// Detect rules.
	ruleFiles := findFiles(dir, "rules/*.md")
	for _, path := range ruleFiles {
		rel, _ := filepath.Rel(dir, path)
		exports = append(exports, manifest.Export{
			Source: rel,
			Type:   "rule",
		})
	}

	// Detect hooks.
	hookFiles := findFiles(dir, "hooks/*.sh")
	for _, path := range hookFiles {
		rel, _ := filepath.Rel(dir, path)
		exports = append(exports, manifest.Export{
			Source:    rel,
			Type:      "hook",
			HookEvent: "PostToolUse",
		})
	}

	// Detect templates.
	templateFiles := findFiles(dir, "templates/*.md")
	for _, path := range templateFiles {
		rel, _ := filepath.Rel(dir, path)
		exports = append(exports, manifest.Export{
			Source: rel,
			Type:   "template",
		})
	}

	return exports
}

func findFiles(dir, pattern string) []string {
	matches, err := filepath.Glob(filepath.Join(dir, pattern))
	if err != nil {
		return nil
	}
	return matches
}

func deriveProvides(exports []manifest.Export) []string {
	seen := make(map[string]bool)
	var provides []string
	for _, e := range exports {
		if !seen[e.Type] {
			seen[e.Type] = true
			provides = append(provides, e.Type)
		}
	}
	return provides
}
