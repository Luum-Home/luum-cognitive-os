// Package config loads and merges cos-dispatch configuration from TOML files,
// environment variables, and CLI flags.
package config

import (
	"fmt"
	"os"
	"path/filepath"
	"runtime"
	"strconv"
	"strings"

	"github.com/BurntSushi/toml"
)

// Config is the top-level cos-dispatch configuration.
type Config struct {
	Dispatch     DispatchConfig     `toml:"dispatch"`
	CognitiveOS CognitiveOSConfig  `toml:"cognitive_os"`
	Transformers []TransformerDef   `toml:"transformers"`
	Plugins      []PluginDef        `toml:"plugins"`
	Overrides    OverridesConfig    `toml:"overrides"`
	Patterns     PatternsConfig     `toml:"patterns"`
}

// DispatchConfig controls the core dispatch behavior.
type DispatchConfig struct {
	Provider  string      `toml:"provider"`
	Parallel  bool        `toml:"parallel"`
	LogLevel  string      `toml:"log_level"`
	TimeoutMs int         `toml:"timeout_ms"`
	Pools     PoolsConfig `toml:"pools"`
}

// PoolsConfig controls the worker pool sizes for parallel execution.
type PoolsConfig struct {
	CPUWorkers int `toml:"cpu_workers"`
	IOWorkers  int `toml:"io_workers"`
	GitWorkers int `toml:"git_workers"`
}

// CognitiveOSConfig holds paths for Cognitive OS integration.
type CognitiveOSConfig struct {
	ConfigPath string `toml:"config_path"`
	MetricsDir string `toml:"metrics_dir"`
	SessionDir string `toml:"session_dir"`
}

// TransformerDef defines a transformer from the config file.
type TransformerDef struct {
	Name     string         `toml:"name"`
	Phase    string         `toml:"phase"`
	Priority int            `toml:"priority"`
	Enabled  bool           `toml:"enabled"`
	Config   map[string]any `toml:"config"`
}

// PluginDef defines an external plugin from the config file.
type PluginDef struct {
	Name      string   `toml:"name"`
	Command   string   `toml:"command"`
	Events    []string `toml:"events"`
	Tools     []string `toml:"tools"`
	Category  string   `toml:"category"`
	TimeoutMs int      `toml:"timeout_ms"`
	Async     bool     `toml:"async"`
}

// OverridesConfig holds global validator overrides.
type OverridesConfig struct {
	DisabledCodes []string `toml:"disabled_codes"`
}

// PatternsConfig controls pattern tracking behavior.
type PatternsConfig struct {
	Enabled          bool             `toml:"enabled"`
	DBPath           string           `toml:"db_path"`
	MinCount         int              `toml:"min_count"`
	AnalysisInterval string           `toml:"analysis_interval"`
	AutoGenerate     AutoGenerateConfig `toml:"auto_generate"`
}

// AutoGenerateConfig controls auto-generation of validators from patterns.
type AutoGenerateConfig struct {
	Enabled             bool    `toml:"enabled"`
	OutputDir           string  `toml:"output_dir"`
	ConfidenceThreshold float64 `toml:"confidence_threshold"`
	RequireReview       bool    `toml:"require_review"`
	MaxPerSession       int     `toml:"max_per_session"`
}

// DefaultConfig returns a Config with sensible defaults.
func DefaultConfig() *Config {
	return &Config{
		Dispatch: DispatchConfig{
			Provider:  "auto",
			Parallel:  true,
			LogLevel:  "info",
			TimeoutMs: 5000,
			Pools: PoolsConfig{
				CPUWorkers: 0, // 0 = runtime.NumCPU()
				IOWorkers:  0, // 0 = runtime.NumCPU() * 2
				GitWorkers: 1,
			},
		},
		CognitiveOS: CognitiveOSConfig{
			ConfigPath: "cognitive-os.yaml",
			MetricsDir: ".cognitive-os/metrics",
			SessionDir: ".cognitive-os/sessions",
		},
		Overrides: OverridesConfig{
			DisabledCodes: []string{},
		},
		Patterns: PatternsConfig{
			Enabled:          true,
			DBPath:           ".cognitive-os/patterns.db",
			MinCount:         3,
			AnalysisInterval: "session_end",
			AutoGenerate: AutoGenerateConfig{
				Enabled:             true,
				OutputDir:           "generated/",
				ConfidenceThreshold: 0.7,
				RequireReview:       true,
				MaxPerSession:       3,
			},
		},
	}
}

// ResolvedPools returns the pool sizes with zero-values resolved to defaults.
func (c *Config) ResolvedPools() PoolsConfig {
	p := c.Dispatch.Pools
	if p.CPUWorkers <= 0 {
		p.CPUWorkers = runtime.NumCPU()
	}
	if p.IOWorkers <= 0 {
		p.IOWorkers = runtime.NumCPU() * 2
	}
	if p.GitWorkers <= 0 {
		p.GitWorkers = 1
	}
	return p
}

// Load reads configuration from the standard locations, merging in order:
// global config -> project config -> env vars. The projectDir is used to
// locate cos-dispatch.toml. An explicit configPath overrides project discovery.
func Load(projectDir string, configPath string) (*Config, error) {
	cfg := DefaultConfig()

	// 1. Global config
	globalPath := globalConfigPath()
	if globalPath != "" {
		if err := mergeFromFile(cfg, globalPath); err != nil && !os.IsNotExist(err) {
			return nil, fmt.Errorf("global config: %w", err)
		}
	}

	// 2. Project config (or explicit path)
	projectFile := configPath
	if projectFile == "" && projectDir != "" {
		projectFile = filepath.Join(projectDir, "cos-dispatch.toml")
	}
	if projectFile != "" {
		if err := mergeFromFile(cfg, projectFile); err != nil && !os.IsNotExist(err) {
			return nil, fmt.Errorf("project config: %w", err)
		}
	}

	// 3. Environment variable overrides
	applyEnvOverrides(cfg)

	return cfg, nil
}

// globalConfigPath returns the global config file path using XDG conventions.
func globalConfigPath() string {
	configHome := os.Getenv("XDG_CONFIG_HOME")
	if configHome == "" {
		home, err := os.UserHomeDir()
		if err != nil {
			return ""
		}
		configHome = filepath.Join(home, ".config")
	}
	return filepath.Join(configHome, "cos-dispatch", "config.toml")
}

// mergeFromFile decodes a TOML file into the config, overwriting fields that
// are present in the file.
func mergeFromFile(cfg *Config, path string) error {
	data, err := os.ReadFile(path)
	if err != nil {
		return err
	}
	_, err = toml.Decode(string(data), cfg)
	return err
}

// applyEnvOverrides reads COS_DISPATCH_* environment variables and applies
// them to the config.
func applyEnvOverrides(cfg *Config) {
	if v := os.Getenv("COS_DISPATCH_PROVIDER"); v != "" {
		cfg.Dispatch.Provider = v
	}
	if v := os.Getenv("COS_DISPATCH_PARALLEL"); v != "" {
		if b, err := strconv.ParseBool(v); err == nil {
			cfg.Dispatch.Parallel = b
		}
	}
	if v := os.Getenv("COS_DISPATCH_LOG_LEVEL"); v != "" {
		cfg.Dispatch.LogLevel = v
	}
	if v := os.Getenv("COS_DISPATCH_TIMEOUT"); v != "" {
		if n, err := strconv.Atoi(v); err == nil {
			cfg.Dispatch.TimeoutMs = n
		}
	}
	if v := os.Getenv("COS_DISPATCH_PATTERNS_ENABLED"); v != "" {
		if b, err := strconv.ParseBool(v); err == nil {
			cfg.Patterns.Enabled = b
		}
	}
}

// IsCodeDisabled reports whether the given error code is in the disabled list.
func (c *Config) IsCodeDisabled(code string) bool {
	for _, disabled := range c.Overrides.DisabledCodes {
		if strings.EqualFold(disabled, code) {
			return true
		}
	}
	return false
}
