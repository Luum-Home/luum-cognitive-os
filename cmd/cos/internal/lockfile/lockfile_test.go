package lockfile

import (
	"os"
	"path/filepath"
	"testing"
)

func TestNewLockfile(t *testing.T) {
	lf := New()

	if lf.LockVersion != LockfileVersion {
		t.Errorf("expected lock_version %q, got %q", LockfileVersion, lf.LockVersion)
	}
	if lf.GeneratedAt == "" {
		t.Error("expected generated_at to be set")
	}
	if lf.Packages == nil {
		t.Error("expected packages map to be initialized")
	}
	if len(lf.Packages) != 0 {
		t.Errorf("expected 0 packages, got %d", len(lf.Packages))
	}
}

func TestAddPackage(t *testing.T) {
	lf := New()

	pkg := LockedPackage{
		Version:    "1.0.0",
		Source:     "github.com/luum/safety-mesh",
		SourceType: "github",
		Resolved:   "https://github.com/luum/safety-mesh",
		Integrity:  "sha256:abc123",
		License:    "MIT",
	}

	lf.AddPackage("@luum/safety-mesh", pkg)

	got := lf.GetPackage("@luum/safety-mesh")
	if got == nil {
		t.Fatal("expected package to exist after AddPackage")
	}
	if got.Version != "1.0.0" {
		t.Errorf("expected version 1.0.0, got %s", got.Version)
	}
	if got.SourceType != "github" {
		t.Errorf("expected source_type github, got %s", got.SourceType)
	}
}

func TestRemovePackage(t *testing.T) {
	lf := New()
	lf.AddPackage("test-pkg", LockedPackage{Version: "1.0.0"})

	if !lf.HasPackage("test-pkg") {
		t.Fatal("expected package to exist before removal")
	}

	lf.RemovePackage("test-pkg")

	if lf.HasPackage("test-pkg") {
		t.Error("expected package to be removed")
	}
	if lf.GetPackage("test-pkg") != nil {
		t.Error("expected GetPackage to return nil after removal")
	}
}

func TestHasPackage(t *testing.T) {
	lf := New()

	if lf.HasPackage("nonexistent") {
		t.Error("expected HasPackage to return false for missing package")
	}

	lf.AddPackage("exists", LockedPackage{Version: "1.0.0"})

	if !lf.HasPackage("exists") {
		t.Error("expected HasPackage to return true for existing package")
	}
}

func TestSaveAndLoad(t *testing.T) {
	dir := t.TempDir()

	original := New()
	original.CosVersion = "0.3.0"
	original.AddPackage("@luum/safety-mesh", LockedPackage{
		Version:    "2.1.0",
		Source:     "github.com/luum/safety-mesh",
		SourceType: "github",
		Resolved:   "https://github.com/luum/safety-mesh",
		Integrity:  "sha256:deadbeef",
		License:    "MIT",
		Exports: []LockedExport{
			{Source: "rules/safety.md", Type: "rule", Target: "rules/safety.md"},
		},
		Audit: AuditResult{
			License:   "pass",
			Secrets:   "pass",
			Injection: "pass",
			Sandbox:   "skipped",
			LastAudit: "2026-03-28T00:00:00Z",
		},
	})

	if err := original.Save(dir); err != nil {
		t.Fatalf("Save failed: %v", err)
	}

	// Verify the file was created.
	path := filepath.Join(dir, LockfileName)
	if _, err := os.Stat(path); err != nil {
		t.Fatalf("lockfile not created at %s: %v", path, err)
	}

	loaded, err := Load(dir)
	if err != nil {
		t.Fatalf("Load failed: %v", err)
	}

	if loaded.LockVersion != LockfileVersion {
		t.Errorf("expected lock_version %q, got %q", LockfileVersion, loaded.LockVersion)
	}
	if loaded.CosVersion != "0.3.0" {
		t.Errorf("expected cos_version 0.3.0, got %s", loaded.CosVersion)
	}
	if !loaded.HasPackage("@luum/safety-mesh") {
		t.Fatal("expected package @luum/safety-mesh in loaded lockfile")
	}

	pkg := loaded.GetPackage("@luum/safety-mesh")
	if pkg.Version != "2.1.0" {
		t.Errorf("expected version 2.1.0, got %s", pkg.Version)
	}
	if pkg.Audit.License != "pass" {
		t.Errorf("expected audit.license pass, got %s", pkg.Audit.License)
	}
	if len(pkg.Exports) != 1 {
		t.Fatalf("expected 1 export, got %d", len(pkg.Exports))
	}
	if pkg.Exports[0].Type != "rule" {
		t.Errorf("expected export type rule, got %s", pkg.Exports[0].Type)
	}
}

func TestLoadMissing(t *testing.T) {
	dir := t.TempDir()

	lf, err := Load(dir)
	if err != nil {
		t.Fatalf("Load on missing file should not error, got: %v", err)
	}
	if lf.LockVersion != LockfileVersion {
		t.Errorf("expected default lock_version %q, got %q", LockfileVersion, lf.LockVersion)
	}
	if len(lf.Packages) != 0 {
		t.Errorf("expected 0 packages from missing file, got %d", len(lf.Packages))
	}
}

func TestLoadCorrupted(t *testing.T) {
	dir := t.TempDir()
	path := filepath.Join(dir, LockfileName)

	if err := os.WriteFile(path, []byte("not: [valid: yaml: {{"), 0644); err != nil {
		t.Fatalf("failed to write corrupted file: %v", err)
	}

	_, err := Load(dir)
	if err == nil {
		t.Error("expected error when loading corrupted YAML")
	}
}

func TestAddPackageOverwrites(t *testing.T) {
	lf := New()

	lf.AddPackage("pkg", LockedPackage{Version: "1.0.0", License: "MIT"})
	lf.AddPackage("pkg", LockedPackage{Version: "2.0.0", License: "Apache-2.0"})

	pkg := lf.GetPackage("pkg")
	if pkg == nil {
		t.Fatal("expected package to exist")
	}
	if pkg.Version != "2.0.0" {
		t.Errorf("expected version 2.0.0 after overwrite, got %s", pkg.Version)
	}
	if pkg.License != "Apache-2.0" {
		t.Errorf("expected license Apache-2.0 after overwrite, got %s", pkg.License)
	}
	if len(lf.Packages) != 1 {
		t.Errorf("expected 1 package after overwrite, got %d", len(lf.Packages))
	}
}

func TestGetPackage_NotFound(t *testing.T) {
	lf := New()

	pkg := lf.GetPackage("nonexistent")
	if pkg != nil {
		t.Error("expected GetPackage to return nil for nonexistent package")
	}
}

func TestSaveAndLoad_WithAuditResult(t *testing.T) {
	dir := t.TempDir()

	original := New()
	original.AddPackage("audit-pkg", LockedPackage{
		Version: "1.0.0",
		License: "MIT",
		Audit: AuditResult{
			License:   "pass",
			Secrets:   "fail",
			Injection: "warning",
			Sandbox:   "skipped",
			LastAudit: "2026-03-28T12:00:00Z",
		},
	})

	if err := original.Save(dir); err != nil {
		t.Fatalf("Save failed: %v", err)
	}

	loaded, err := Load(dir)
	if err != nil {
		t.Fatalf("Load failed: %v", err)
	}

	pkg := loaded.GetPackage("audit-pkg")
	if pkg == nil {
		t.Fatal("expected audit-pkg to exist")
	}

	if pkg.Audit.License != "pass" {
		t.Errorf("expected audit.License 'pass', got %q", pkg.Audit.License)
	}
	if pkg.Audit.Secrets != "fail" {
		t.Errorf("expected audit.Secrets 'fail', got %q", pkg.Audit.Secrets)
	}
	if pkg.Audit.Injection != "warning" {
		t.Errorf("expected audit.Injection 'warning', got %q", pkg.Audit.Injection)
	}
	if pkg.Audit.Sandbox != "skipped" {
		t.Errorf("expected audit.Sandbox 'skipped', got %q", pkg.Audit.Sandbox)
	}
	if pkg.Audit.LastAudit != "2026-03-28T12:00:00Z" {
		t.Errorf("expected audit.LastAudit '2026-03-28T12:00:00Z', got %q", pkg.Audit.LastAudit)
	}
}

func TestSaveAndLoad_WithExports(t *testing.T) {
	dir := t.TempDir()

	original := New()
	original.AddPackage("export-pkg", LockedPackage{
		Version: "2.0.0",
		License: "Apache-2.0",
		Exports: []LockedExport{
			{Source: "SKILL.md", Type: "skill", Target: ".claude/skills/pkg/SKILL.md"},
			{Source: "hooks/check.sh", Type: "hook", Target: ".cognitive-os/hooks/cos/pkg/check.sh", HookEvent: "PostToolUse", HookMatcher: "Bash"},
			{Source: "rules/safety.md", Type: "rule", Target: ".claude/rules/cos/pkg/safety.md"},
		},
	})

	if err := original.Save(dir); err != nil {
		t.Fatalf("Save failed: %v", err)
	}

	loaded, err := Load(dir)
	if err != nil {
		t.Fatalf("Load failed: %v", err)
	}

	pkg := loaded.GetPackage("export-pkg")
	if pkg == nil {
		t.Fatal("expected export-pkg to exist")
	}

	if len(pkg.Exports) != 3 {
		t.Fatalf("expected 3 exports, got %d", len(pkg.Exports))
	}

	// Verify hook export roundtrips with event/matcher.
	hookExport := pkg.Exports[1]
	if hookExport.HookEvent != "PostToolUse" {
		t.Errorf("expected HookEvent 'PostToolUse', got %q", hookExport.HookEvent)
	}
	if hookExport.HookMatcher != "Bash" {
		t.Errorf("expected HookMatcher 'Bash', got %q", hookExport.HookMatcher)
	}
}

func TestSaveAndLoad_EmptyPackages(t *testing.T) {
	dir := t.TempDir()

	original := New()
	// No packages added -- just the empty map.

	if err := original.Save(dir); err != nil {
		t.Fatalf("Save failed: %v", err)
	}

	loaded, err := Load(dir)
	if err != nil {
		t.Fatalf("Load failed: %v", err)
	}

	if loaded.Packages == nil {
		t.Error("expected Packages map to be initialized (not nil)")
	}
	if len(loaded.Packages) != 0 {
		t.Errorf("expected 0 packages, got %d", len(loaded.Packages))
	}
}

func TestSaveAndLoad_WithDependencies(t *testing.T) {
	dir := t.TempDir()

	original := New()
	original.AddPackage("dep-pkg", LockedPackage{
		Version: "1.0.0",
		License: "MIT",
		Dependencies: map[string]string{
			"@luum/core":   ">=1.0.0",
			"@luum/safety": "^2.0.0",
		},
	})

	if err := original.Save(dir); err != nil {
		t.Fatalf("Save failed: %v", err)
	}

	loaded, err := Load(dir)
	if err != nil {
		t.Fatalf("Load failed: %v", err)
	}

	pkg := loaded.GetPackage("dep-pkg")
	if pkg == nil {
		t.Fatal("expected dep-pkg to exist")
	}
	if len(pkg.Dependencies) != 2 {
		t.Errorf("expected 2 dependencies, got %d", len(pkg.Dependencies))
	}
	if pkg.Dependencies["@luum/core"] != ">=1.0.0" {
		t.Errorf("expected core dep '>=1.0.0', got %q", pkg.Dependencies["@luum/core"])
	}
}

func TestSaveAndLoad_ForcedFlag(t *testing.T) {
	dir := t.TempDir()

	original := New()
	original.AddPackage("forced-pkg", LockedPackage{
		Version: "1.0.0",
		License: "AGPL-3.0",
		Forced:  true,
	})

	if err := original.Save(dir); err != nil {
		t.Fatalf("Save failed: %v", err)
	}

	loaded, err := Load(dir)
	if err != nil {
		t.Fatalf("Load failed: %v", err)
	}

	pkg := loaded.GetPackage("forced-pkg")
	if pkg == nil {
		t.Fatal("expected forced-pkg to exist")
	}
	if !pkg.Forced {
		t.Error("expected Forced flag to be true after roundtrip")
	}
}

func TestMultiplePackages(t *testing.T) {
	lf := New()

	lf.AddPackage("pkg-a", LockedPackage{Version: "1.0.0"})
	lf.AddPackage("pkg-b", LockedPackage{Version: "2.0.0"})
	lf.AddPackage("pkg-c", LockedPackage{Version: "3.0.0"})

	if len(lf.Packages) != 3 {
		t.Errorf("expected 3 packages, got %d", len(lf.Packages))
	}

	if !lf.HasPackage("pkg-a") || !lf.HasPackage("pkg-b") || !lf.HasPackage("pkg-c") {
		t.Error("expected all three packages to be present")
	}

	// Remove one and verify the others remain.
	lf.RemovePackage("pkg-b")

	if len(lf.Packages) != 2 {
		t.Errorf("expected 2 packages after removal, got %d", len(lf.Packages))
	}
	if lf.HasPackage("pkg-b") {
		t.Error("expected pkg-b to be removed")
	}
	if !lf.HasPackage("pkg-a") || !lf.HasPackage("pkg-c") {
		t.Error("expected pkg-a and pkg-c to remain")
	}
}
