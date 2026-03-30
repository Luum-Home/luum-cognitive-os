package registry

import (
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"strings"

	"gopkg.in/yaml.v3"
)

// RegistryType identifies the kind of registry source.
type RegistryType string

const (
	// RegistryGitHubTopic searches GitHub repos with a specific topic.
	RegistryGitHubTopic RegistryType = "github-topic"
	// RegistryGitHubOrg searches repos within a GitHub organization.
	RegistryGitHubOrg RegistryType = "github-org"
	// RegistryGitHubRepo searches within a specific GitHub repository.
	RegistryGitHubRepo RegistryType = "github-repo"
	// RegistryDirectory searches a local directory for packages.
	RegistryDirectory RegistryType = "directory"
	// RegistrySkillsSh searches the skills.sh registry (skills.sh / agentskills.io).
	RegistrySkillsSh RegistryType = "skills-sh"
)

// RegistryConfig represents a single configured package registry.
type RegistryConfig struct {
	Name     string       `yaml:"name"`
	Type     RegistryType `yaml:"type"`
	Topic    string       `yaml:"topic,omitempty"`    // for github-topic
	Org      string       `yaml:"org,omitempty"`      // for github-org
	Repo     string       `yaml:"repo,omitempty"`     // for github-repo
	Path     string       `yaml:"path,omitempty"`     // for directory
	BaseURL  string       `yaml:"base_url,omitempty"` // for skills-sh (custom API URL)
	Enabled  bool         `yaml:"enabled"`
	Priority int          `yaml:"priority"`
}

// packagesConfig is the top-level structure for the packages section of cognitive-os.yaml.
type packagesConfig struct {
	Packages struct {
		Registries []RegistryConfig `yaml:"registries"`
	} `yaml:"packages"`
}

// DefaultRegistries returns the built-in registries that are used when no
// configuration is found. This preserves backward compatibility: cos search
// works exactly as before (GitHub topic search for "cos-package").
func DefaultRegistries() []RegistryConfig {
	return []RegistryConfig{
		{
			Name:     "cos-official",
			Type:     RegistryGitHubTopic,
			Topic:    "cos-package",
			Enabled:  true,
			Priority: 1,
		},
	}
}

// LoadRegistries reads registry configuration from cognitive-os.yaml.
// If the file does not exist or has no registries configured, it returns
// the default registries so that existing behavior is preserved.
func LoadRegistries(projectRoot string) []RegistryConfig {
	configPath := filepath.Join(projectRoot, "cognitive-os.yaml")

	data, err := os.ReadFile(configPath)
	if err != nil {
		return DefaultRegistries()
	}

	var cfg packagesConfig
	if err := yaml.Unmarshal(data, &cfg); err != nil {
		return DefaultRegistries()
	}

	registries := cfg.Packages.Registries
	if len(registries) == 0 {
		return DefaultRegistries()
	}

	return registries
}

// EnabledRegistries returns only the enabled registries, sorted by priority
// (lower priority number = higher precedence).
func EnabledRegistries(registries []RegistryConfig) []RegistryConfig {
	var enabled []RegistryConfig
	for _, r := range registries {
		if r.Enabled {
			enabled = append(enabled, r)
		}
	}

	sort.Slice(enabled, func(i, j int) bool {
		return enabled[i].Priority < enabled[j].Priority
	})

	return enabled
}

// FindRegistry returns the registry with the given name, or nil if not found.
func FindRegistry(registries []RegistryConfig, name string) *RegistryConfig {
	for i := range registries {
		if registries[i].Name == name {
			return &registries[i]
		}
	}
	return nil
}

// AnnotatedResult wraps a SearchResult with the registry it came from.
type AnnotatedResult struct {
	SearchResult
	Registry string `json:"registry"`
}

// SearchAllRegistries searches all enabled registries and returns merged,
// deduplicated results annotated with their source registry.
func SearchAllRegistries(registries []RegistryConfig, query string, limit int) ([]AnnotatedResult, []error) {
	enabled := EnabledRegistries(registries)
	if len(enabled) == 0 {
		return nil, []error{fmt.Errorf("no enabled registries configured")}
	}

	var allResults []AnnotatedResult
	var allErrors []error
	seen := make(map[string]bool) // deduplicate by URL

	for _, reg := range enabled {
		results, err := searchRegistry(reg, query, limit)
		if err != nil {
			allErrors = append(allErrors, fmt.Errorf("registry %q: %w", reg.Name, err))
			continue
		}

		for _, r := range results {
			key := r.URL
			if key == "" {
				key = r.Name
			}
			if seen[key] {
				continue
			}
			seen[key] = true
			allResults = append(allResults, AnnotatedResult{
				SearchResult: r,
				Registry:     reg.Name,
			})
		}
	}

	return allResults, allErrors
}

// SearchOneRegistry searches a single named registry.
func SearchOneRegistry(registries []RegistryConfig, name string, query string, limit int) ([]AnnotatedResult, error) {
	reg := FindRegistry(registries, name)
	if reg == nil {
		return nil, fmt.Errorf("registry %q not found", name)
	}
	if !reg.Enabled {
		return nil, fmt.Errorf("registry %q is disabled", name)
	}

	results, err := searchRegistry(*reg, query, limit)
	if err != nil {
		return nil, err
	}

	annotated := make([]AnnotatedResult, len(results))
	for i, r := range results {
		annotated[i] = AnnotatedResult{
			SearchResult: r,
			Registry:     reg.Name,
		}
	}
	return annotated, nil
}

// searchRegistry dispatches to the appropriate search function based on type.
func searchRegistry(reg RegistryConfig, query string, limit int) ([]SearchResult, error) {
	switch reg.Type {
	case RegistryGitHubTopic:
		topic := reg.Topic
		if topic == "" {
			topic = "cos-package"
		}
		return SearchGitHubTopic(query, topic, limit)
	case RegistryGitHubOrg:
		if reg.Org == "" {
			return nil, fmt.Errorf("github-org registry %q missing org field", reg.Name)
		}
		return SearchGitHubOrg(reg.Org, query, limit)
	case RegistryGitHubRepo:
		if reg.Repo == "" {
			return nil, fmt.Errorf("github-repo registry %q missing repo field", reg.Name)
		}
		return SearchGitHubRepoContents(reg.Repo, query, limit)
	case RegistryDirectory:
		if reg.Path == "" {
			return nil, fmt.Errorf("directory registry %q missing path field", reg.Name)
		}
		return SearchLocal(reg.Path, query)
	case RegistrySkillsSh:
		baseURL := reg.BaseURL
		if baseURL == "" {
			baseURL = SkillsShDefaultBaseURL
		}
		return SearchSkillsSh(query, baseURL, limit)
	default:
		return nil, fmt.Errorf("unknown registry type %q for %q", reg.Type, reg.Name)
	}
}

// SaveRegistries writes the registries back to cognitive-os.yaml, updating
// only the packages.registries section. It reads the full file, modifies
// the section, and writes it back.
func SaveRegistries(projectRoot string, registries []RegistryConfig) error {
	configPath := filepath.Join(projectRoot, "cognitive-os.yaml")

	data, err := os.ReadFile(configPath)
	if err != nil && !os.IsNotExist(err) {
		return fmt.Errorf("reading config: %w", err)
	}

	var root yaml.Node
	if len(data) > 0 {
		if err := yaml.Unmarshal(data, &root); err != nil {
			return fmt.Errorf("parsing config: %w", err)
		}
	}

	// For simplicity, we write a supplementary section. A full YAML
	// round-trip that preserves comments is complex; instead we use
	// the existing structure if present or append.
	// This implementation marshals and appends if needed.
	if root.Kind == 0 {
		// Empty file — create from scratch.
		out := struct {
			Packages struct {
				Registries []RegistryConfig `yaml:"registries"`
			} `yaml:"packages"`
		}{}
		out.Packages.Registries = registries
		outData, err := yaml.Marshal(out)
		if err != nil {
			return fmt.Errorf("marshaling config: %w", err)
		}
		return os.WriteFile(configPath, outData, 0644)
	}

	// File exists — update using simple string replacement approach.
	// We serialize just the registries and update the packages section.
	regData, err := yaml.Marshal(struct {
		Registries []RegistryConfig `yaml:"registries"`
	}{Registries: registries})
	if err != nil {
		return fmt.Errorf("marshaling registries: %w", err)
	}

	content := string(data)

	// Check if packages.registries section already exists.
	if strings.Contains(content, "packages:") && strings.Contains(content, "registries:") {
		// Find and replace the registries block. This is a best-effort
		// approach; for production we'd use a proper YAML editor.
		// For now, warn the user to edit manually.
		return fmt.Errorf("packages.registries section already exists in %s. Please edit manually:\n\npackages:\n  %s",
			configPath, strings.ReplaceAll(string(regData), "\n", "\n  "))
	}

	// Append the packages section.
	appendStr := fmt.Sprintf("\npackages:\n  %s", strings.ReplaceAll(string(regData), "\n", "\n  "))
	content += appendStr

	return os.WriteFile(configPath, []byte(content), 0644)
}
