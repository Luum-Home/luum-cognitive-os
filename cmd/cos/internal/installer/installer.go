package installer

import (
	"crypto/sha256"
	"encoding/hex"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"time"

	"luum-agent-os/cmd/cos/internal/lockfile"
	"luum-agent-os/cmd/cos/internal/manifest"
	"luum-agent-os/cmd/cos/internal/resolver"
	"luum-agent-os/cmd/cos/internal/security"
)

// InstallOptions configures the install operation.
type InstallOptions struct {
	Force    bool // bypass security audit
	Generate bool // auto-detect exports without cos-package.yaml
	DryRun   bool // show what would happen without doing it
}

// InstallResult holds the outcome of an install operation.
type InstallResult struct {
	Package   string
	Version   string
	Exports   []ExportTarget
	Audit     *security.AuditReport
	Installed bool
	Message   string
}

// RunInstall executes the full install pipeline.
func RunInstall(spec string, projectRoot string, opts InstallOptions) (*InstallResult, error) {
	result := &InstallResult{}

	// Step 1: Resolve the source.
	source, err := resolver.Resolve(spec)
	if err != nil {
		return nil, fmt.Errorf("resolving %q: %w", spec, err)
	}
	result.Package = source.Name

	// Step 2: Fetch the package.
	fetchedDir, err := resolver.Fetch(source)
	if err != nil {
		return nil, fmt.Errorf("fetching %q: %w", spec, err)
	}
	defer resolver.CleanupFetch(fetchedDir)

	// Step 3: Parse or generate manifest.
	m, err := loadOrGenerateManifest(fetchedDir, opts.Generate)
	if err != nil {
		return nil, err
	}

	result.Package = m.Name
	result.Version = m.Version

	// Step 4: Dry run check.
	if opts.DryRun {
		targets, err := ResolveTargets(m.Exports, projectRoot, fetchedDir, m.Name)
		if err != nil {
			return nil, fmt.Errorf("resolving targets: %w", err)
		}
		result.Exports = targets

		// Run audit for display but don't enforce.
		result.Audit = security.RunAudit(fetchedDir, m.License)
		result.Message = "Dry run complete. No files were modified."
		return result, nil
	}

	// Step 5: Security audit.
	audit := security.RunAudit(fetchedDir, m.License)
	result.Audit = audit

	if !audit.Passed && !opts.Force {
		return result, fmt.Errorf("security audit failed. Use --force to bypass (not recommended)")
	}

	if !audit.Passed && opts.Force {
		audit.Forced = true
	}

	// Step 6: Load lockfile.
	lf, err := lockfile.Load(projectRoot)
	if err != nil {
		return nil, fmt.Errorf("loading lockfile: %w", err)
	}

	// Step 7: Check if already installed.
	if lf.HasPackage(m.Name) && !opts.Force {
		existing := lf.GetPackage(m.Name)
		if existing != nil && existing.Version == m.Version {
			result.Message = fmt.Sprintf("Package %s@%s is already installed. Use --force to reinstall.", m.Name, m.Version)
			return result, nil
		}
	}

	// Step 8: Resolve export targets.
	targets, err := ResolveTargets(m.Exports, projectRoot, fetchedDir, m.Name)
	if err != nil {
		return nil, fmt.Errorf("resolving targets: %w", err)
	}
	result.Exports = targets

	// Step 9: Install exports (copy files).
	if err := Install(targets); err != nil {
		return nil, fmt.Errorf("installing exports: %w", err)
	}

	// Step 10: Register hooks in settings.json.
	settingsPath := filepath.Join(projectRoot, ".claude", "settings.json")
	hookBasePath := filepath.Join(".cognitive-os", "hooks", "cos", m.Name)
	if err := RegisterHooks(settingsPath, m.Exports, hookBasePath); err != nil {
		return nil, fmt.Errorf("registering hooks: %w", err)
	}

	// Step 11: Update lockfile.
	lockedExports := buildLockedExports(targets)
	integrity := computeManifestIntegrity(fetchedDir)

	pkg := lockfile.LockedPackage{
		Version:     m.Version,
		Source:      source.Raw,
		SourceType:  sourceTypeName(source.Type),
		Resolved:    resolvedPath(source),
		Commit:      getGitCommit(fetchedDir),
		Integrity:   integrity,
		License:     m.License,
		InstalledAt: time.Now().UTC().Format(time.RFC3339),
		Exports:     lockedExports,
		Audit:       audit.ToAuditResult(),
		Forced:      audit.Forced,
	}

	lf.AddPackage(m.Name, pkg)

	// Step 12: Save lockfile.
	if err := lf.Save(projectRoot); err != nil {
		return nil, fmt.Errorf("saving lockfile: %w", err)
	}

	// Step 13: Run postinstall script if defined.
	if script, ok := m.Scripts["postinstall"]; ok {
		if err := runScript(script, projectRoot); err != nil {
			// Postinstall failure is not fatal; warn but continue.
			result.Message = fmt.Sprintf("Warning: postinstall script failed: %v", err)
		}
	}

	result.Installed = true
	if result.Message == "" {
		result.Message = fmt.Sprintf("Installed %s@%s successfully", m.Name, m.Version)
	}

	return result, nil
}

// loadOrGenerateManifest loads the manifest from fetchedDir or generates one.
func loadOrGenerateManifest(fetchedDir string, generate bool) (*manifest.Manifest, error) {
	manifestPath := filepath.Join(fetchedDir, "cos-package.yaml")

	m, err := manifest.ParseFile(manifestPath)
	if err == nil {
		return m, nil
	}

	if !os.IsNotExist(err) && !generate {
		return nil, fmt.Errorf("parsing manifest: %w", err)
	}

	if !generate {
		return nil, fmt.Errorf("no cos-package.yaml found in package. Use --generate to auto-detect exports")
	}

	// Generate manifest from detected exports.
	return generateManifest(fetchedDir), nil
}

// generateManifest creates a manifest by auto-detecting exports in the directory.
func generateManifest(dir string) *manifest.Manifest {
	var exports []manifest.Export

	// Detect skills.
	skillFiles := findGlob(dir, "skills/*/SKILL.md")
	for _, path := range skillFiles {
		rel, _ := filepath.Rel(dir, path)
		exports = append(exports, manifest.Export{
			Source: rel,
			Type:   "skill",
		})
	}

	// Detect root SKILL.md.
	if _, err := os.Stat(filepath.Join(dir, "SKILL.md")); err == nil {
		exports = append(exports, manifest.Export{
			Source: "SKILL.md",
			Type:   "skill",
		})
	}

	// Detect rules.
	ruleFiles := findGlob(dir, "rules/*.md")
	for _, path := range ruleFiles {
		rel, _ := filepath.Rel(dir, path)
		exports = append(exports, manifest.Export{
			Source: rel,
			Type:   "rule",
		})
	}

	// Detect hooks.
	hookFiles := findGlob(dir, "hooks/*.sh")
	for _, path := range hookFiles {
		rel, _ := filepath.Rel(dir, path)
		exports = append(exports, manifest.Export{
			Source:    rel,
			Type:      "hook",
			HookEvent: "PostToolUse",
		})
	}

	// Detect templates.
	templateFiles := findGlob(dir, "templates/*.md")
	for _, path := range templateFiles {
		rel, _ := filepath.Rel(dir, path)
		exports = append(exports, manifest.Export{
			Source: rel,
			Type:   "template",
		})
	}

	name := filepath.Base(dir)
	return &manifest.Manifest{
		Name:     name,
		Version:  "0.0.0",
		License:  "UNKNOWN",
		Provides: deriveProvides(exports),
		Exports:  exports,
	}
}

// findGlob returns files matching a glob pattern under the given directory.
func findGlob(dir, pattern string) []string {
	matches, _ := filepath.Glob(filepath.Join(dir, pattern))
	return matches
}

// deriveProvides extracts unique export types.
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

// buildLockedExports converts ExportTargets to lockfile format.
func buildLockedExports(targets []ExportTarget) []lockfile.LockedExport {
	exports := make([]lockfile.LockedExport, len(targets))
	for i, t := range targets {
		exports[i] = lockfile.LockedExport{
			Source:      t.Export.Source,
			Type:        t.Export.Type,
			Target:      t.Target,
			HookEvent:   t.Export.HookEvent,
			HookMatcher: t.Export.HookMatcher,
		}
	}
	return exports
}

// computeManifestIntegrity computes a SHA-256 hash of the manifest file.
func computeManifestIntegrity(fetchedDir string) string {
	data, err := os.ReadFile(filepath.Join(fetchedDir, "cos-package.yaml"))
	if err != nil {
		return ""
	}
	h := sha256.Sum256(data)
	return "sha256:" + hex.EncodeToString(h[:])
}

// getGitCommit returns the current git commit hash of a directory.
func getGitCommit(dir string) string {
	cmd := exec.Command("git", "rev-parse", "HEAD")
	cmd.Dir = dir
	out, err := cmd.Output()
	if err != nil {
		return ""
	}

	commit := string(out)
	if len(commit) > 40 {
		commit = commit[:40]
	}
	return commit
}

// sourceTypeName returns the string name for a resolver.SourceType.
func sourceTypeName(t resolver.SourceType) string {
	switch t {
	case resolver.SourceLocal:
		return "local"
	case resolver.SourceGitHub:
		return "github"
	case resolver.SourceURL:
		return "url"
	default:
		return "unknown"
	}
}

// resolvedPath returns the full resolved path or URL for a source.
func resolvedPath(source *resolver.ResolvedSource) string {
	if source.Type == resolver.SourceLocal {
		abs, err := filepath.Abs(source.LocalPath)
		if err != nil {
			return source.LocalPath
		}
		return abs
	}
	return source.URL
}

// runScript executes a shell script in the given working directory.
func runScript(script, workDir string) error {
	cmd := exec.Command("bash", "-c", script)
	cmd.Dir = workDir
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr
	return cmd.Run()
}
