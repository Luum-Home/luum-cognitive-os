package cli

import (
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"text/template"

	"github.com/spf13/cobra"

	"luum-agent-os/cmd/cos/internal/project"
	"luum-agent-os/cmd/cos/internal/ui"
)

var (
	newTemplate string
	newPhase    string
	newProfile  string
	newSkipInit bool
)

// ValidTemplates lists the supported project templates.
var ValidTemplates = []string{"go", "typescript", "python", "rust", "minimal"}

var newCmd = &cobra.Command{
	Use:   "new <project-name>",
	Short: "Create a new project with COS pre-configured",
	Long: `Create a new project directory with Cognitive OS pre-configured.

Templates:
  go          Go project (go.mod, main.go)
  typescript  TypeScript project (package.json, tsconfig.json)
  python      Python project (pyproject.toml)
  minimal     Just COS config, no stack files

Examples:
  cos new my-api --template go
  cos new my-app --template typescript
  cos new experiment --template minimal --phase stabilization`,
	Args: cobra.ExactArgs(1),
	RunE: runNew,
}

func init() {
	newCmd.Flags().StringVarP(&newTemplate, "template", "t", "minimal", "Project template (go|typescript|python|rust|minimal)")
	newCmd.Flags().StringVar(&newPhase, "phase", "reconstruction", "Initial project phase")
	newCmd.Flags().StringVar(&newProfile, "profile", "standard", "Efficiency profile (lean|standard|full)")
	newCmd.Flags().BoolVar(&newSkipInit, "skip-init", false, "Skip running cos init after scaffolding")
	rootCmd.AddCommand(newCmd)
}

// TemplateData holds the values available in template files.
type TemplateData struct {
	ProjectName string
	Phase       string
	Profile     string
}

func runNew(cmd *cobra.Command, args []string) error {
	projectName := args[0]

	// Validate template name.
	if !isValidTemplate(newTemplate) {
		return fmt.Errorf("unknown template %q: valid templates are %s", newTemplate, strings.Join(ValidTemplates, ", "))
	}

	// Validate phase.
	validPhases := []string{"reconstruction", "stabilization", "production", "maintenance"}
	if !contains(validPhases, newPhase) {
		return fmt.Errorf("unknown phase %q: valid phases are %s", newPhase, strings.Join(validPhases, ", "))
	}

	// Validate profile.
	validProfiles := []string{"lean", "standard", "full"}
	if !contains(validProfiles, newProfile) {
		return fmt.Errorf("unknown profile %q: valid profiles are %s", newProfile, strings.Join(validProfiles, ", "))
	}

	// Check if directory already exists.
	if info, err := os.Stat(projectName); err == nil && info.IsDir() {
		return fmt.Errorf("directory %q already exists", projectName)
	}

	// Find template directory.
	templateRoot, err := findTemplateRoot()
	if err != nil {
		return fmt.Errorf("locating templates: %w", err)
	}

	fmt.Println(ui.TitleStyle.Render("cos new — Create a new project"))
	fmt.Println()

	data := TemplateData{
		ProjectName: projectName,
		Phase:       newPhase,
		Profile:     newProfile,
	}

	// Create project directory.
	if err := os.MkdirAll(projectName, 0755); err != nil {
		return fmt.Errorf("creating project directory: %w", err)
	}

	// Create .claude directory.
	if err := os.MkdirAll(filepath.Join(projectName, ".claude"), 0755); err != nil {
		return fmt.Errorf("creating .claude directory: %w", err)
	}

	// Render template-specific files.
	templateDir := filepath.Join(templateRoot, newTemplate)
	filesRendered, err := renderTemplateDirFS(templateDir, projectName, data)
	if err != nil {
		// Clean up on failure.
		os.RemoveAll(projectName)
		return fmt.Errorf("rendering template files: %w", err)
	}

	// Render shared settings.json template.
	settingsPath := filepath.Join(templateRoot, "settings.json.tmpl")
	if _, statErr := os.Stat(settingsPath); statErr == nil {
		rendered, renderErr := renderSingleTemplateFS(settingsPath, filepath.Join(projectName, ".claude", "settings.json"), data)
		if renderErr != nil {
			fmt.Printf("  %s Could not create .claude/settings.json: %v\n", ui.IconWarning, renderErr)
		} else if rendered {
			filesRendered++
		}
	}

	fmt.Printf("  %s Created %d files in %s/\n", ui.IconCheck, filesRendered, projectName)

	// Initialize git repo.
	if err := initGitRepo(projectName); err != nil {
		fmt.Printf("  %s Could not initialize git: %v\n", ui.IconWarning, err)
	} else {
		fmt.Printf("  %s Initialized git repository\n", ui.IconCheck)
	}

	// Run cos init inside the new directory (if cos-init.sh is reachable).
	if !newSkipInit {
		if err := runCosInit(projectName); err != nil {
			fmt.Printf("  %s Skipped cos init: %v\n", ui.IconWarning, err)
		} else {
			fmt.Printf("  %s Ran cos init (standard mode)\n", ui.IconCheck)
		}
	}

	fmt.Println()
	fmt.Println(ui.SuccessStyle.Render(fmt.Sprintf("%s Project %s created successfully!", ui.IconCheck, projectName)))
	fmt.Println()
	fmt.Println(ui.MutedStyle.Render("Next steps:"))
	fmt.Printf("  cd %s\n", projectName)
	fmt.Println("  # Open Claude Code and start coding")
	fmt.Println()

	return nil
}

// findTemplateRoot locates the project-templates directory.
func findTemplateRoot() (string, error) {
	// 1. Check COS_TEMPLATE_DIR env var.
	if dir := os.Getenv("COS_TEMPLATE_DIR"); dir != "" {
		if _, err := os.Stat(dir); err == nil {
			return dir, nil
		}
	}

	// 2. Check relative to COS source (found via project.FindRootOrCwd).
	root := project.FindRootOrCwd()
	candidate := filepath.Join(root, "templates", "project-templates")
	if _, err := os.Stat(candidate); err == nil {
		return candidate, nil
	}

	// 3. Check relative to the executable.
	exe, err := os.Executable()
	if err == nil {
		exeDir := filepath.Dir(exe)
		// Binary might be in bin/ or cmd/cos/, try going up.
		for _, rel := range []string{
			filepath.Join(exeDir, "..", "templates", "project-templates"),
			filepath.Join(exeDir, "..", "..", "templates", "project-templates"),
			filepath.Join(exeDir, "..", "..", "..", "templates", "project-templates"),
		} {
			absRel, _ := filepath.Abs(rel)
			if _, err := os.Stat(absRel); err == nil {
				return absRel, nil
			}
		}
	}

	// 4. Check COS_SOURCE_DIR.
	if dir := os.Getenv("COS_SOURCE_DIR"); dir != "" {
		candidate := filepath.Join(dir, "templates", "project-templates")
		if _, err := os.Stat(candidate); err == nil {
			return candidate, nil
		}
	}

	return "", fmt.Errorf("templates not found; set COS_TEMPLATE_DIR or COS_SOURCE_DIR environment variable")
}

// renderTemplateDirFS walks a filesystem directory and renders all .tmpl files.
func renderTemplateDirFS(dir, destRoot string, data TemplateData) (int, error) {
	count := 0

	entries, err := os.ReadDir(dir)
	if err != nil {
		return 0, fmt.Errorf("reading template directory %s: %w", dir, err)
	}

	for _, entry := range entries {
		if entry.IsDir() {
			// Recurse into subdirectories.
			subCount, err := renderTemplateDirFS(
				filepath.Join(dir, entry.Name()),
				filepath.Join(destRoot, entry.Name()),
				data,
			)
			if err != nil {
				return count, err
			}
			count += subCount
			continue
		}

		srcPath := filepath.Join(dir, entry.Name())

		// Determine output filename: strip .tmpl suffix if present.
		outputName := entry.Name()
		if strings.HasSuffix(outputName, ".tmpl") {
			outputName = strings.TrimSuffix(outputName, ".tmpl")
		}

		// Special case: gitignore -> .gitignore (cannot store .gitignore in git templates easily).
		if outputName == "gitignore" {
			outputName = ".gitignore"
		}

		destPath := filepath.Join(destRoot, outputName)

		rendered, err := renderSingleTemplateFS(srcPath, destPath, data)
		if err != nil {
			return count, err
		}
		if rendered {
			count++
		}
	}

	return count, nil
}

// renderSingleTemplateFS renders one template file from the filesystem to disk.
func renderSingleTemplateFS(srcPath, destPath string, data TemplateData) (bool, error) {
	content, err := os.ReadFile(srcPath)
	if err != nil {
		return false, fmt.Errorf("reading template %s: %w", srcPath, err)
	}

	// Ensure parent directory exists.
	if err := os.MkdirAll(filepath.Dir(destPath), 0755); err != nil {
		return false, fmt.Errorf("creating directory for %s: %w", destPath, err)
	}

	// Parse and execute template.
	tmpl, err := template.New(filepath.Base(srcPath)).Parse(string(content))
	if err != nil {
		return false, fmt.Errorf("parsing template %s: %w", srcPath, err)
	}

	f, err := os.Create(destPath)
	if err != nil {
		return false, fmt.Errorf("creating file %s: %w", destPath, err)
	}
	defer f.Close()

	if err := tmpl.Execute(f, data); err != nil {
		return false, fmt.Errorf("executing template %s: %w", srcPath, err)
	}

	return true, nil
}

// initGitRepo runs git init in the project directory.
func initGitRepo(dir string) error {
	cmd := exec.Command("git", "init")
	cmd.Dir = dir
	cmd.Stdout = nil
	cmd.Stderr = nil
	return cmd.Run()
}

// runCosInit attempts to run cos-init.sh in the project directory.
func runCosInit(dir string) error {
	cosSourceDir := findCosSourceDir()
	if cosSourceDir == "" {
		return fmt.Errorf("cos-init.sh not found; run 'cos init' manually in the project directory")
	}

	initScript := filepath.Join(cosSourceDir, "scripts", "cos-init.sh")
	if _, err := os.Stat(initScript); err != nil {
		return fmt.Errorf("cos-init.sh not found at %s", initScript)
	}

	cmd := exec.Command("bash", initScript, "--standard")
	cmd.Dir = dir
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr
	return cmd.Run()
}

// findCosSourceDir attempts to locate the Cognitive OS source directory.
func findCosSourceDir() string {
	// Check COS_SOURCE_DIR env var.
	if dir := os.Getenv("COS_SOURCE_DIR"); dir != "" {
		return dir
	}

	// Check via project root detection.
	root := project.FindRootOrCwd()
	if _, err := os.Stat(filepath.Join(root, "scripts", "cos-init.sh")); err == nil {
		return root
	}

	// Try relative to executable.
	exe, err := os.Executable()
	if err != nil {
		return ""
	}
	for _, rel := range []string{
		filepath.Join(filepath.Dir(exe), ".."),
		filepath.Join(filepath.Dir(exe), "..", ".."),
		filepath.Join(filepath.Dir(exe), "..", "..", ".."),
	} {
		absRel, _ := filepath.Abs(rel)
		if _, err := os.Stat(filepath.Join(absRel, "scripts", "cos-init.sh")); err == nil {
			return absRel
		}
	}

	return ""
}

func isValidTemplate(name string) bool {
	return contains(ValidTemplates, name)
}

func contains(slice []string, item string) bool {
	for _, s := range slice {
		if s == item {
			return true
		}
	}
	return false
}
