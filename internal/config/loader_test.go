package config

import (
	"os"
	"path/filepath"
	"runtime"
	"testing"
)

func TestDefaultConfig(t *testing.T) {
	cfg := DefaultConfig()

	if cfg.Dispatch.Provider != "auto" {
		t.Errorf("provider = %q, want %q", cfg.Dispatch.Provider, "auto")
	}
	if !cfg.Dispatch.Parallel {
		t.Error("parallel should default to true")
	}
	if cfg.Dispatch.LogLevel != "info" {
		t.Errorf("log_level = %q, want %q", cfg.Dispatch.LogLevel, "info")
	}
	if cfg.Dispatch.TimeoutMs != 5000 {
		t.Errorf("timeout_ms = %d, want %d", cfg.Dispatch.TimeoutMs, 5000)
	}
	if cfg.Dispatch.Pools.GitWorkers != 1 {
		t.Errorf("git_workers = %d, want %d", cfg.Dispatch.Pools.GitWorkers, 1)
	}
}

func TestResolvedPools_Defaults(t *testing.T) {
	cfg := DefaultConfig()
	pools := cfg.ResolvedPools()

	if pools.CPUWorkers != runtime.NumCPU() {
		t.Errorf("cpu_workers = %d, want %d", pools.CPUWorkers, runtime.NumCPU())
	}
	if pools.IOWorkers != runtime.NumCPU()*2 {
		t.Errorf("io_workers = %d, want %d", pools.IOWorkers, runtime.NumCPU()*2)
	}
	if pools.GitWorkers != 1 {
		t.Errorf("git_workers = %d, want %d", pools.GitWorkers, 1)
	}
}

func TestResolvedPools_Explicit(t *testing.T) {
	cfg := DefaultConfig()
	cfg.Dispatch.Pools.CPUWorkers = 4
	cfg.Dispatch.Pools.IOWorkers = 8
	cfg.Dispatch.Pools.GitWorkers = 2

	pools := cfg.ResolvedPools()

	if pools.CPUWorkers != 4 {
		t.Errorf("cpu_workers = %d, want %d", pools.CPUWorkers, 4)
	}
	if pools.IOWorkers != 8 {
		t.Errorf("io_workers = %d, want %d", pools.IOWorkers, 8)
	}
	if pools.GitWorkers != 2 {
		t.Errorf("git_workers = %d, want %d", pools.GitWorkers, 2)
	}
}

func TestLoad_FromFile(t *testing.T) {
	dir := t.TempDir()
	configFile := filepath.Join(dir, "cos-dispatch.toml")

	content := `
[dispatch]
provider = "claude"
parallel = false
log_level = "debug"
timeout_ms = 3000

[dispatch.pools]
cpu_workers = 2
io_workers = 4
git_workers = 1

[overrides]
disabled_codes = ["COS-SEC-001"]
`
	if err := os.WriteFile(configFile, []byte(content), 0644); err != nil {
		t.Fatalf("write config: %v", err)
	}

	cfg, err := Load(dir, "")
	if err != nil {
		t.Fatalf("Load: %v", err)
	}

	if cfg.Dispatch.Provider != "claude" {
		t.Errorf("provider = %q, want %q", cfg.Dispatch.Provider, "claude")
	}
	if cfg.Dispatch.Parallel {
		t.Error("parallel should be false from config file")
	}
	if cfg.Dispatch.LogLevel != "debug" {
		t.Errorf("log_level = %q, want %q", cfg.Dispatch.LogLevel, "debug")
	}
	if cfg.Dispatch.TimeoutMs != 3000 {
		t.Errorf("timeout_ms = %d, want %d", cfg.Dispatch.TimeoutMs, 3000)
	}
	if len(cfg.Overrides.DisabledCodes) != 1 || cfg.Overrides.DisabledCodes[0] != "COS-SEC-001" {
		t.Errorf("disabled_codes = %v, want [COS-SEC-001]", cfg.Overrides.DisabledCodes)
	}
}

func TestLoad_ExplicitPath(t *testing.T) {
	dir := t.TempDir()
	configFile := filepath.Join(dir, "custom.toml")

	content := `
[dispatch]
provider = "codex"
timeout_ms = 1000
`
	if err := os.WriteFile(configFile, []byte(content), 0644); err != nil {
		t.Fatalf("write config: %v", err)
	}

	cfg, err := Load("", configFile)
	if err != nil {
		t.Fatalf("Load: %v", err)
	}

	if cfg.Dispatch.Provider != "codex" {
		t.Errorf("provider = %q, want %q", cfg.Dispatch.Provider, "codex")
	}
	if cfg.Dispatch.TimeoutMs != 1000 {
		t.Errorf("timeout_ms = %d, want %d", cfg.Dispatch.TimeoutMs, 1000)
	}
}

func TestLoad_MissingFile(t *testing.T) {
	// Loading from a nonexistent project dir should return defaults
	cfg, err := Load("/nonexistent/path", "")
	if err != nil {
		t.Fatalf("Load: %v", err)
	}
	if cfg.Dispatch.Provider != "auto" {
		t.Errorf("provider = %q, want %q (default)", cfg.Dispatch.Provider, "auto")
	}
}

func TestEnvOverrides(t *testing.T) {
	t.Setenv("COS_DISPATCH_PROVIDER", "gemini")
	t.Setenv("COS_DISPATCH_PARALLEL", "false")
	t.Setenv("COS_DISPATCH_LOG_LEVEL", "error")
	t.Setenv("COS_DISPATCH_TIMEOUT", "2000")
	t.Setenv("COS_DISPATCH_PATTERNS_ENABLED", "false")

	cfg, err := Load("", "")
	if err != nil {
		t.Fatalf("Load: %v", err)
	}

	if cfg.Dispatch.Provider != "gemini" {
		t.Errorf("provider = %q, want %q", cfg.Dispatch.Provider, "gemini")
	}
	if cfg.Dispatch.Parallel {
		t.Error("parallel should be false from env")
	}
	if cfg.Dispatch.LogLevel != "error" {
		t.Errorf("log_level = %q, want %q", cfg.Dispatch.LogLevel, "error")
	}
	if cfg.Dispatch.TimeoutMs != 2000 {
		t.Errorf("timeout_ms = %d, want %d", cfg.Dispatch.TimeoutMs, 2000)
	}
	if cfg.Patterns.Enabled {
		t.Error("patterns.enabled should be false from env")
	}
}

func TestIsCodeDisabled(t *testing.T) {
	cfg := DefaultConfig()
	cfg.Overrides.DisabledCodes = []string{"COS-SEC-001", "COS-PERF-002"}

	if !cfg.IsCodeDisabled("COS-SEC-001") {
		t.Error("expected COS-SEC-001 to be disabled")
	}
	if !cfg.IsCodeDisabled("cos-sec-001") {
		t.Error("expected case-insensitive match")
	}
	if cfg.IsCodeDisabled("COS-OTHER-999") {
		t.Error("expected COS-OTHER-999 to not be disabled")
	}
}

func TestLoad_WithPluginDefs(t *testing.T) {
	dir := t.TempDir()
	configFile := filepath.Join(dir, "cos-dispatch.toml")

	content := `
[[plugins]]
name = "session-init"
command = "hooks/session-init.sh"
events = ["session_start"]
category = "io"
timeout_ms = 3000

[[plugins]]
name = "semgrep-scan"
command = "hooks/semgrep-scan.sh"
events = ["after_tool"]
tools = ["Edit", "Write"]
category = "io"
async = true
`
	if err := os.WriteFile(configFile, []byte(content), 0644); err != nil {
		t.Fatalf("write config: %v", err)
	}

	cfg, err := Load(dir, "")
	if err != nil {
		t.Fatalf("Load: %v", err)
	}

	if len(cfg.Plugins) != 2 {
		t.Fatalf("plugins count = %d, want 2", len(cfg.Plugins))
	}
	if cfg.Plugins[0].Name != "session-init" {
		t.Errorf("plugin[0].name = %q, want %q", cfg.Plugins[0].Name, "session-init")
	}
	if cfg.Plugins[1].Async != true {
		t.Error("plugin[1].async should be true")
	}
	if len(cfg.Plugins[1].Tools) != 2 {
		t.Errorf("plugin[1].tools = %v, want [Edit Write]", cfg.Plugins[1].Tools)
	}
}
