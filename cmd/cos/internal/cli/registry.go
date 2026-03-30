package cli

import (
	"fmt"

	"github.com/spf13/cobra"

	"luum-agent-os/cmd/cos/internal/project"
	"luum-agent-os/cmd/cos/internal/registry"
	"luum-agent-os/cmd/cos/internal/ui"
)

// Flags for registry add.
var (
	regAddType     string
	regAddTopic    string
	regAddOrg      string
	regAddRepo     string
	regAddPath     string
	regAddPriority int
)

var registryCmd = &cobra.Command{
	Use:   "registry",
	Short: "Manage package registries",
	Long: `Manage package registries for cos search and install.

Registries are configured in cognitive-os.yaml under packages.registries.
Supported types: github-topic, github-org, github-repo, directory, skills-sh.

Examples:
  cos registry list                                    Show configured registries
  cos registry add my-org --type github-org --org MyOrg Add a GitHub org registry
  cos registry enable my-org                           Enable a registry
  cos registry disable my-org                          Disable a registry`,
}

var registryListCmd = &cobra.Command{
	Use:   "list",
	Short: "Show configured registries",
	Args:  cobra.NoArgs,
	RunE:  runRegistryList,
}

var registryAddCmd = &cobra.Command{
	Use:   "add <name>",
	Short: "Add a new registry",
	Long: `Add a new registry to cognitive-os.yaml.

Examples:
  cos registry add my-org --type github-org --org MyOrg
  cos registry add my-skills --type github-repo --repo user/repo
  cos registry add local-pkgs --type directory --path ~/.cos-packages/
  cos registry add custom-topic --type github-topic --topic my-cos-packages`,
	Args: cobra.ExactArgs(1),
	RunE: runRegistryAdd,
}

var registryEnableCmd = &cobra.Command{
	Use:   "enable <name>",
	Short: "Enable a registry",
	Args:  cobra.ExactArgs(1),
	RunE:  runRegistryToggle(true),
}

var registryDisableCmd = &cobra.Command{
	Use:   "disable <name>",
	Short: "Disable a registry",
	Args:  cobra.ExactArgs(1),
	RunE:  runRegistryToggle(false),
}

func init() {
	// Add flags to registry add.
	registryAddCmd.Flags().StringVar(&regAddType, "type", "", "Registry type: github-topic, github-org, github-repo, directory (required)")
	registryAddCmd.Flags().StringVar(&regAddTopic, "topic", "", "GitHub topic (for github-topic type)")
	registryAddCmd.Flags().StringVar(&regAddOrg, "org", "", "GitHub organization (for github-org type)")
	registryAddCmd.Flags().StringVar(&regAddRepo, "repo", "", "GitHub repo in owner/repo format (for github-repo type)")
	registryAddCmd.Flags().StringVar(&regAddPath, "path", "", "Local directory path (for directory type)")
	registryAddCmd.Flags().IntVar(&regAddPriority, "priority", 10, "Priority (lower = searched first)")
	_ = registryAddCmd.MarkFlagRequired("type")

	// Wire up subcommands.
	registryCmd.AddCommand(registryListCmd)
	registryCmd.AddCommand(registryAddCmd)
	registryCmd.AddCommand(registryEnableCmd)
	registryCmd.AddCommand(registryDisableCmd)
	rootCmd.AddCommand(registryCmd)
}

func runRegistryList(cmd *cobra.Command, args []string) error {
	projectRoot := project.FindRootOrCwd()
	registries := registry.LoadRegistries(projectRoot)

	if len(registries) == 0 {
		fmt.Println(ui.MutedStyle.Render("  No registries configured."))
		fmt.Println()
		fmt.Println(ui.MutedStyle.Render("  Add one with: cos registry add <name> --type <type>"))
		return nil
	}

	fmt.Println()
	ui.Step(ui.IconInfo, fmt.Sprintf("Configured registries (%d):", len(registries)))
	fmt.Println()

	for _, r := range registries {
		status := ui.SuccessStyle.Render("enabled")
		if !r.Enabled {
			status = ui.MutedStyle.Render("disabled")
		}

		name := ui.HeaderStyle.Render(fmt.Sprintf("%-20s", r.Name))
		typeFmt := ui.DimStyle.Render(fmt.Sprintf("%-14s", string(r.Type)))
		priority := ui.MutedStyle.Render(fmt.Sprintf("pri:%-3d", r.Priority))

		// Show the source detail.
		detail := registryDetail(r)
		detailFmt := ui.MutedStyle.Render(detail)

		fmt.Printf("  %s  %s  %s  %s  %s\n", name, typeFmt, priority, status, detailFmt)
	}

	fmt.Println()
	return nil
}

// registryDetail returns a human-readable detail string for a registry.
func registryDetail(r registry.RegistryConfig) string {
	switch r.Type {
	case registry.RegistryGitHubTopic:
		topic := r.Topic
		if topic == "" {
			topic = "cos-package"
		}
		return fmt.Sprintf("topic:%s", topic)
	case registry.RegistryGitHubOrg:
		return fmt.Sprintf("org:%s", r.Org)
	case registry.RegistryGitHubRepo:
		return fmt.Sprintf("repo:%s", r.Repo)
	case registry.RegistryDirectory:
		return fmt.Sprintf("path:%s", r.Path)
	case registry.RegistrySkillsSh:
		baseURL := r.BaseURL
		if baseURL == "" {
			baseURL = registry.SkillsShDefaultBaseURL
		}
		return fmt.Sprintf("url:%s", baseURL)
	default:
		return string(r.Type)
	}
}

func runRegistryAdd(cmd *cobra.Command, args []string) error {
	name := args[0]
	projectRoot := project.FindRootOrCwd()
	registries := registry.LoadRegistries(projectRoot)

	// Check for duplicate name.
	if registry.FindRegistry(registries, name) != nil {
		return fmt.Errorf("registry %q already exists", name)
	}

	regType := registry.RegistryType(regAddType)

	// Validate type-specific required fields.
	switch regType {
	case registry.RegistryGitHubTopic:
		if regAddTopic == "" {
			regAddTopic = "cos-package"
		}
	case registry.RegistryGitHubOrg:
		if regAddOrg == "" {
			return fmt.Errorf("--org is required for github-org type")
		}
	case registry.RegistryGitHubRepo:
		if regAddRepo == "" {
			return fmt.Errorf("--repo is required for github-repo type")
		}
	case registry.RegistryDirectory:
		if regAddPath == "" {
			return fmt.Errorf("--path is required for directory type")
		}
	case registry.RegistrySkillsSh:
		// No required fields — base_url is optional.
	default:
		return fmt.Errorf("unknown registry type %q. Valid types: github-topic, github-org, github-repo, directory, skills-sh", regAddType)
	}

	newReg := registry.RegistryConfig{
		Name:     name,
		Type:     regType,
		Topic:    regAddTopic,
		Org:      regAddOrg,
		Repo:     regAddRepo,
		Path:     regAddPath,
		Enabled:  true,
		Priority: regAddPriority,
	}

	registries = append(registries, newReg)

	if err := registry.SaveRegistries(projectRoot, registries); err != nil {
		// SaveRegistries may return an error with instructions for manual editing.
		fmt.Println(ui.WarningStyle.Render(fmt.Sprintf("%s %s", ui.IconWarning, err.Error())))
		fmt.Println()
		fmt.Println("Add the following to cognitive-os.yaml manually:")
		fmt.Println()
		fmt.Printf("packages:\n  registries:\n")
		for _, r := range registries {
			fmt.Printf("    - name: %s\n      type: %s\n      enabled: %v\n      priority: %d\n",
				r.Name, r.Type, r.Enabled, r.Priority)
			if r.Topic != "" {
				fmt.Printf("      topic: %s\n", r.Topic)
			}
			if r.Org != "" {
				fmt.Printf("      org: %s\n", r.Org)
			}
			if r.Repo != "" {
				fmt.Printf("      repo: %s\n", r.Repo)
			}
			if r.Path != "" {
				fmt.Printf("      path: %s\n", r.Path)
			}
		}
		return nil
	}

	fmt.Println(ui.SuccessStyle.Render(fmt.Sprintf("%s Registry %q added successfully", ui.IconSuccess, name)))
	return nil
}

func runRegistryToggle(enable bool) func(cmd *cobra.Command, args []string) error {
	return func(cmd *cobra.Command, args []string) error {
		name := args[0]
		projectRoot := project.FindRootOrCwd()
		registries := registry.LoadRegistries(projectRoot)

		reg := registry.FindRegistry(registries, name)
		if reg == nil {
			return fmt.Errorf("registry %q not found", name)
		}

		if reg.Enabled == enable {
			action := "enabled"
			if !enable {
				action = "disabled"
			}
			fmt.Println(ui.MutedStyle.Render(fmt.Sprintf("  Registry %q is already %s", name, action)))
			return nil
		}

		reg.Enabled = enable

		action := "enabled"
		if !enable {
			action = "disabled"
		}

		if err := registry.SaveRegistries(projectRoot, registries); err != nil {
			fmt.Println(ui.WarningStyle.Render(fmt.Sprintf(
				"%s Could not update config automatically: %s",
				ui.IconWarning, err.Error(),
			)))
			fmt.Println()
			fmt.Printf("Set enabled: %v for registry %q in cognitive-os.yaml manually.\n", enable, name)
			return nil
		}

		fmt.Println(ui.SuccessStyle.Render(fmt.Sprintf("%s Registry %q %s", ui.IconSuccess, name, action)))
		return nil
	}
}

