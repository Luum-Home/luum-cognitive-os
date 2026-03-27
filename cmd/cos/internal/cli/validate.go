package cli

import (
	"fmt"
	"os"
	"path/filepath"

	"github.com/spf13/cobra"

	"luum-agent-os/cmd/cos/internal/manifest"
	"luum-agent-os/cmd/cos/internal/ui"
)

var validateCmd = &cobra.Command{
	Use:   "validate",
	Short: "Validate cos-package.yaml in the current directory",
	Long:  "Parse and validate the cos-package.yaml manifest, reporting all errors and warnings.",
	RunE:  runValidate,
}

func init() {
	rootCmd.AddCommand(validateCmd)
}

func runValidate(cmd *cobra.Command, args []string) error {
	cwd, err := os.Getwd()
	if err != nil {
		return fmt.Errorf("getting working directory: %w", err)
	}

	target := filepath.Join(cwd, "cos-package.yaml")
	m, err := manifest.ParseFile(target)
	if err != nil {
		fmt.Println(ui.ErrorStyle.Render(fmt.Sprintf("%s Failed to parse cos-package.yaml", ui.IconCross)))
		fmt.Printf("  %s\n", err)
		os.Exit(1)
	}

	errs := manifest.Validate(m)
	if len(errs) == 0 {
		fmt.Println(ui.SuccessStyle.Render(fmt.Sprintf("%s cos-package.yaml is valid", ui.IconCheck)))
		fmt.Println()
		fmt.Printf("  Name:    %s\n", m.Name)
		fmt.Printf("  Version: %s\n", m.Version)
		fmt.Printf("  License: %s\n", m.License)
		fmt.Printf("  Exports: %d\n", len(m.Exports))
		return nil
	}

	fmt.Println(ui.ErrorStyle.Render(fmt.Sprintf("%s cos-package.yaml has %d validation error(s)", ui.IconCross, len(errs))))
	fmt.Println()
	for _, e := range errs {
		fmt.Printf("  %s %s: %s\n", ui.IconBullet, ui.WarningStyle.Render(e.Field), e.Message)
	}

	os.Exit(1)
	return nil
}
