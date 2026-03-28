package security

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"io"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"time"

	"luum-agent-os/cmd/cos/internal/lockfile"
)

// GateStatus represents the result of a security gate.
type GateStatus string

const (
	GatePass    GateStatus = "pass"
	GateFail    GateStatus = "fail"
	GateWarning GateStatus = "warning"
	GateSkipped GateStatus = "skipped"
)

// GateResult is the result of a single security gate.
type GateResult struct {
	Name     string
	Status   GateStatus
	Message  string
	Findings []string
}

// AuditReport is the complete security audit result.
type AuditReport struct {
	Package string
	Gates   []GateResult
	Passed  bool
	Forced  bool
}

// RunAudit executes all security gates on a package directory.
// license is the declared license from the manifest.
func RunAudit(packageDir string, license string) *AuditReport {
	report := &AuditReport{
		Package: packageDir,
	}

	// Gate 1: License check.
	report.Gates = append(report.Gates, runLicenseGate(license))

	// Gate 2: Secrets scan.
	report.Gates = append(report.Gates, runSecretsGate(packageDir))

	// Gate 3: Injection scan.
	report.Gates = append(report.Gates, runInjectionGate(packageDir))

	// Gate 4: Parry guard (optional external tool).
	report.Gates = append(report.Gates, runParryGate(packageDir))

	// Determine overall pass/fail.
	report.Passed = true
	for _, gate := range report.Gates {
		if gate.Status == GateFail {
			report.Passed = false
			break
		}
	}

	return report
}

// runLicenseGate checks the declared license against the policy.
func runLicenseGate(license string) GateResult {
	if license == "" {
		return GateResult{
			Name:    "license",
			Status:  GateWarning,
			Message: "No license declared",
		}
	}

	verdict := ClassifyLicense(license)
	msg := LicenseMessage(license, verdict)

	switch verdict {
	case LicenseBlocked:
		return GateResult{
			Name:     "license",
			Status:   GateFail,
			Message:  msg,
			Findings: []string{msg},
		}
	case LicenseCaution:
		return GateResult{
			Name:    "license",
			Status:  GateWarning,
			Message: msg,
		}
	case LicenseUnknown:
		return GateResult{
			Name:    "license",
			Status:  GateWarning,
			Message: msg,
		}
	default:
		return GateResult{
			Name:    "license",
			Status:  GatePass,
			Message: msg,
		}
	}
}

// runSecretsGate scans for hardcoded secrets.
func runSecretsGate(dir string) GateResult {
	findings := ScanSecrets(dir)
	if len(findings) == 0 {
		return GateResult{
			Name:    "secrets",
			Status:  GatePass,
			Message: "No hardcoded secrets detected",
		}
	}

	strs := make([]string, len(findings))
	for i, f := range findings {
		strs[i] = fmt.Sprintf("%s:%d %s (%s)", f.File, f.Line, f.Pattern, f.Snippet)
	}

	return GateResult{
		Name:     "secrets",
		Status:   GateFail,
		Message:  fmt.Sprintf("Found %d hardcoded secret(s)", len(findings)),
		Findings: strs,
	}
}

// runInjectionGate scans for prompt and shell injection patterns.
func runInjectionGate(dir string) GateResult {
	findings := ScanInjection(dir)
	if len(findings) == 0 {
		return GateResult{
			Name:    "injection",
			Status:  GatePass,
			Message: "No injection patterns detected",
		}
	}

	strs := make([]string, len(findings))
	for i, f := range findings {
		strs[i] = fmt.Sprintf("%s:%d [%s] %s", f.File, f.Line, f.Type, f.Pattern)
	}

	return GateResult{
		Name:     "injection",
		Status:   GateFail,
		Message:  fmt.Sprintf("Found %d injection pattern(s)", len(findings)),
		Findings: strs,
	}
}

// parryFinding is the JSON structure returned by parry-guard.
type parryFinding struct {
	File    string `json:"file"`
	Line    int    `json:"line"`
	Message string `json:"message"`
}

// runParryGate runs the optional parry-guard external scanner.
func runParryGate(dir string) GateResult {
	path, err := exec.LookPath("parry-guard")
	if err != nil || path == "" {
		return GateResult{
			Name:    "parry",
			Status:  GateSkipped,
			Message: "parry-guard not installed",
		}
	}

	cmd := exec.Command("parry-guard", "scan", "--format", "json", dir)
	output, err := cmd.Output()
	if err != nil {
		// Non-zero exit means findings.
		if exitErr, ok := err.(*exec.ExitError); ok {
			output = exitErr.Stderr
			if len(cmd.ProcessState.String()) > 0 {
				// Use combined output if available.
				output, _ = cmd.CombinedOutput()
			}
		}
		if len(output) == 0 {
			return GateResult{
				Name:    "parry",
				Status:  GateWarning,
				Message: fmt.Sprintf("parry-guard error: %v", err),
			}
		}
	}

	var pFindings []parryFinding
	if err := json.Unmarshal(output, &pFindings); err != nil {
		// If we cannot parse, treat as warning.
		return GateResult{
			Name:    "parry",
			Status:  GateWarning,
			Message: "parry-guard output could not be parsed",
		}
	}

	if len(pFindings) == 0 {
		return GateResult{
			Name:    "parry",
			Status:  GatePass,
			Message: "parry-guard scan clean",
		}
	}

	strs := make([]string, len(pFindings))
	for i, f := range pFindings {
		strs[i] = fmt.Sprintf("%s:%d %s", f.File, f.Line, f.Message)
	}

	return GateResult{
		Name:     "parry",
		Status:   GateFail,
		Message:  fmt.Sprintf("parry-guard found %d issue(s)", len(pFindings)),
		Findings: strs,
	}
}

// FormatReport returns a human-readable audit report.
func FormatReport(report *AuditReport) string {
	var b strings.Builder

	b.WriteString("Security Audit Report\n")
	b.WriteString(strings.Repeat("=", 40) + "\n\n")

	for _, gate := range report.Gates {
		icon := gateIcon(gate.Status)
		b.WriteString(fmt.Sprintf("  %s %s: %s\n", icon, gate.Name, gate.Message))

		for _, finding := range gate.Findings {
			b.WriteString(fmt.Sprintf("      - %s\n", finding))
		}
	}

	b.WriteString("\n")
	if report.Passed {
		b.WriteString("[PASS] All security gates passed\n")
	} else {
		b.WriteString("[FAIL] One or more security gates failed\n")
	}

	if report.Forced {
		b.WriteString("[WARN] Audit failures were force-overridden\n")
	}

	return b.String()
}

// gateIcon returns a status icon matching ui/styles.go conventions.
func gateIcon(status GateStatus) string {
	switch status {
	case GatePass:
		return "[PASS]"
	case GateFail:
		return "[FAIL]"
	case GateWarning:
		return "[WARN]"
	case GateSkipped:
		return "[INFO]"
	default:
		return "[INFO]"
	}
}

// ComputeFileHashes computes SHA256 hashes for all files in a directory.
// Returns a map of relative_path -> sha256_hex_hash.
// Skips .git/ directory and binary files.
func ComputeFileHashes(dir string) (map[string]string, error) {
	hashes := make(map[string]string)

	err := filepath.Walk(dir, func(path string, info os.FileInfo, err error) error {
		if err != nil {
			return err
		}

		// Get relative path.
		rel, relErr := filepath.Rel(dir, path)
		if relErr != nil {
			return relErr
		}

		// Skip .git directory entirely.
		if rel == ".git" || strings.HasPrefix(rel, ".git"+string(filepath.Separator)) {
			if info.IsDir() {
				return filepath.SkipDir
			}
			return nil
		}

		// Skip directories.
		if info.IsDir() {
			return nil
		}

		// Compute SHA256.
		f, openErr := os.Open(path)
		if openErr != nil {
			return fmt.Errorf("opening %s: %w", rel, openErr)
		}
		defer f.Close()

		h := sha256.New()
		if _, copyErr := io.Copy(h, f); copyErr != nil {
			return fmt.Errorf("hashing %s: %w", rel, copyErr)
		}

		hashes[rel] = hex.EncodeToString(h.Sum(nil))
		return nil
	})

	if err != nil {
		return nil, fmt.Errorf("walking directory %s: %w", dir, err)
	}

	return hashes, nil
}

// VerifyFileHashes checks that all files match their expected hashes.
// Returns list of mismatched or missing files.
func VerifyFileHashes(dir string, expected map[string]string) ([]string, error) {
	var mismatched []string

	for relPath, expectedHash := range expected {
		fullPath := filepath.Join(dir, relPath)

		f, err := os.Open(fullPath)
		if err != nil {
			if os.IsNotExist(err) {
				mismatched = append(mismatched, relPath+" (missing)")
				continue
			}
			return nil, fmt.Errorf("opening %s: %w", relPath, err)
		}

		h := sha256.New()
		if _, copyErr := io.Copy(h, f); copyErr != nil {
			f.Close()
			return nil, fmt.Errorf("hashing %s: %w", relPath, copyErr)
		}
		f.Close()

		actualHash := hex.EncodeToString(h.Sum(nil))
		if actualHash != expectedHash {
			mismatched = append(mismatched, relPath+" (modified)")
		}
	}

	return mismatched, nil
}

// ToAuditResult converts to the lockfile AuditResult format.
func (r *AuditReport) ToAuditResult() lockfile.AuditResult {
	result := lockfile.AuditResult{
		LastAudit: time.Now().UTC().Format(time.RFC3339),
	}

	for _, gate := range r.Gates {
		status := string(gate.Status)
		switch gate.Name {
		case "license":
			result.License = status
		case "secrets":
			result.Secrets = status
		case "injection":
			result.Injection = status
		case "parry":
			result.Sandbox = status
		}
	}

	return result
}
