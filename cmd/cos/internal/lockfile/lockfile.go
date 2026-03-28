package lockfile

import (
	"fmt"
	"os"
	"path/filepath"
	"time"

	"gopkg.in/yaml.v3"
)

// LockfileVersion is the current schema version for the lockfile format.
const LockfileVersion = "1"

// LockfileName is the conventional filename for the lockfile.
const LockfileName = "cos-lock.yaml"

// Lockfile represents the full contents of a cos-lock.yaml file.
type Lockfile struct {
	LockVersion string                   `yaml:"lock_version"`
	CosVersion  string                   `yaml:"cos_version"`
	GeneratedAt string                   `yaml:"generated_at"`
	Packages    map[string]LockedPackage `yaml:"packages"`
}

// LockedPackage holds the resolved, audited state of a single installed package.
type LockedPackage struct {
	Version      string            `yaml:"version"`
	Source       string            `yaml:"source"`
	SourceType   string            `yaml:"source_type"`        // local, github, url
	Resolved     string            `yaml:"resolved"`           // full resolved path/URL
	Commit       string            `yaml:"commit,omitempty"`   // git commit hash
	Integrity    string            `yaml:"integrity"`          // sha256 of manifest
	License      string            `yaml:"license"`
	InstalledAt  string            `yaml:"installed_at"`
	Exports      []LockedExport    `yaml:"exports"`
	Dependencies map[string]string `yaml:"dependencies,omitempty"`
	Audit        AuditResult       `yaml:"audit"`
	Forced       bool              `yaml:"forced,omitempty"`
}

// LockedExport records where a single exported component was installed.
type LockedExport struct {
	Source      string `yaml:"source"`
	Type        string `yaml:"type"`
	Target      string `yaml:"target"`
	HookEvent   string `yaml:"hook_event,omitempty"`
	HookMatcher string `yaml:"hook_matcher,omitempty"`
}

// AuditResult stores the outcome of each audit check at install time.
type AuditResult struct {
	License   string `yaml:"license"`   // pass, fail, warning, skipped
	Secrets   string `yaml:"secrets"`
	Injection string `yaml:"injection"`
	Sandbox   string `yaml:"sandbox"`
	LastAudit string `yaml:"last_audit"`
}

// New creates an empty lockfile with sensible defaults.
func New() *Lockfile {
	return &Lockfile{
		LockVersion: LockfileVersion,
		GeneratedAt: time.Now().UTC().Format(time.RFC3339),
		Packages:    make(map[string]LockedPackage),
	}
}

// Load reads the lockfile from the given directory.
// If the file does not exist, an empty lockfile is returned (not an error).
func Load(dir string) (*Lockfile, error) {
	path := filepath.Join(dir, LockfileName)

	data, err := os.ReadFile(path)
	if err != nil {
		if os.IsNotExist(err) {
			return New(), nil
		}
		return nil, fmt.Errorf("reading lockfile: %w", err)
	}

	var lf Lockfile
	if err := yaml.Unmarshal(data, &lf); err != nil {
		return nil, fmt.Errorf("parsing lockfile YAML: %w", err)
	}

	// Ensure the map is never nil even if the file had an empty packages section.
	if lf.Packages == nil {
		lf.Packages = make(map[string]LockedPackage)
	}

	return &lf, nil
}

// Save writes the lockfile to the given directory, updating GeneratedAt.
func (l *Lockfile) Save(dir string) error {
	l.GeneratedAt = time.Now().UTC().Format(time.RFC3339)

	data, err := yaml.Marshal(l)
	if err != nil {
		return fmt.Errorf("marshalling lockfile: %w", err)
	}

	path := filepath.Join(dir, LockfileName)
	if err := os.WriteFile(path, data, 0644); err != nil {
		return fmt.Errorf("writing lockfile: %w", err)
	}
	return nil
}

// AddPackage adds or updates a package entry in the lockfile.
func (l *Lockfile) AddPackage(name string, pkg LockedPackage) {
	l.Packages[name] = pkg
}

// RemovePackage deletes a package entry from the lockfile.
func (l *Lockfile) RemovePackage(name string) {
	delete(l.Packages, name)
}

// HasPackage reports whether the named package is present in the lockfile.
func (l *Lockfile) HasPackage(name string) bool {
	_, ok := l.Packages[name]
	return ok
}

// GetPackage returns the locked package entry for the given name, or nil if
// the package is not installed.
func (l *Lockfile) GetPackage(name string) *LockedPackage {
	pkg, ok := l.Packages[name]
	if !ok {
		return nil
	}
	return &pkg
}
