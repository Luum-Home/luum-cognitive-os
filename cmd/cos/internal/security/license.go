package security

import (
	"fmt"
	"strings"
)

// LicenseVerdict represents the safety classification of a license.
type LicenseVerdict int

const (
	LicenseSafe    LicenseVerdict = iota // MIT, BSD, Apache, ISC
	LicenseCaution                       // LGPL, MPL
	LicenseBlocked                       // AGPL, SSPL, GPL, BSL, ELv2
	LicenseUnknown                       // Not recognized
)

// String returns a human-readable label for the verdict.
func (v LicenseVerdict) String() string {
	switch v {
	case LicenseSafe:
		return "safe"
	case LicenseCaution:
		return "caution"
	case LicenseBlocked:
		return "blocked"
	default:
		return "unknown"
	}
}

// blockedLicenses maps SPDX identifiers to explanations for blocked licenses.
var blockedLicenses = map[string]string{
	"AGPL-3.0":          "Network copyleft -- forces open-sourcing all SaaS code",
	"AGPL-3.0-only":     "Network copyleft -- forces open-sourcing all SaaS code",
	"AGPL-3.0-or-later": "Network copyleft -- forces open-sourcing all SaaS code",
	"SSPL-1.0":          "Server-side copyleft -- blocks SaaS deployment entirely",
	"GPL-2.0":           "Viral copyleft -- derivative works must be GPL",
	"GPL-2.0-only":      "Viral copyleft -- derivative works must be GPL",
	"GPL-3.0":           "Viral copyleft -- derivative works must be GPL",
	"GPL-3.0-only":      "Viral copyleft -- derivative works must be GPL",
	"BSL-1.1":           "Business source -- cannot compete with vendor",
	"ELv2":              "Elastic License -- cannot offer as managed service",
	"Commons-Clause":    "Cannot sell the software as a service",
	"FSL-1.0":           "Functional Source License -- commercial restrictions",
	// FSL-1.1 is also OUR project's own license starting 2026-05-XX. We block
	// FSL-1.1 as a DEP license (would inherit commercial restrictions from
	// a dep) but use it as our SELF license (we don't inherit from ourselves).
	// See .cognitive-os/strategy/04-license-repo-and-corrections-log.md.
	"FSL-1.1":           "Functional Source License -- commercial restrictions",
}

// cautionLicenses maps SPDX identifiers to explanations for caution licenses.
var cautionLicenses = map[string]string{
	"LGPL-2.1":     "Dynamic linking only -- do not modify or statically link",
	"LGPL-3.0":     "Dynamic linking only -- do not modify or statically link",
	"MPL-2.0":      "File-level copyleft -- changes to MPL files must be open-sourced",
	"Artistic-2.0": "Similar to MPL -- changes to original must be published",
}

// safeLicenses maps SPDX identifiers to explanations for safe licenses.
var safeLicenses = map[string]string{
	"MIT":          "Permissive -- no restrictions",
	"BSD-2-Clause": "Permissive -- maintain copyright",
	"BSD-3-Clause": "Permissive -- maintain copyright",
	"Apache-2.0":   "Permissive -- maintain NOTICE + indicate changes",
	"ISC":          "Permissive -- no restrictions",
	"CC0-1.0":      "Public domain -- no restrictions",
	"Unlicense":    "Public domain -- no restrictions",
	"0BSD":         "Permissive -- no restrictions",
	"WTFPL":        "Permissive -- no restrictions",
	"Zlib":         "Permissive -- no restrictions",
	"CC-BY-4.0":    "Attribution -- maintain credit",
	"CC-BY-SA-4.0": "Attribution share-alike -- maintain credit",
	"PostgreSQL":   "Permissive -- no restrictions",
}

// normalizeSPDX normalizes an SPDX identifier for case-insensitive lookup.
// It returns the canonical form if found, otherwise the trimmed input.
func normalizeSPDX(spdx string) string {
	trimmed := strings.TrimSpace(spdx)
	lower := strings.ToLower(trimmed)

	// Check all maps for a case-insensitive match and return the canonical key.
	for k := range blockedLicenses {
		if strings.ToLower(k) == lower {
			return k
		}
	}
	for k := range cautionLicenses {
		if strings.ToLower(k) == lower {
			return k
		}
	}
	for k := range safeLicenses {
		if strings.ToLower(k) == lower {
			return k
		}
	}
	return trimmed
}

// ClassifyLicense returns the verdict for a given SPDX license identifier.
func ClassifyLicense(spdx string) LicenseVerdict {
	normalized := normalizeSPDX(spdx)

	if _, ok := blockedLicenses[normalized]; ok {
		return LicenseBlocked
	}
	if _, ok := cautionLicenses[normalized]; ok {
		return LicenseCaution
	}
	if _, ok := safeLicenses[normalized]; ok {
		return LicenseSafe
	}
	return LicenseUnknown
}

// LicenseMessage returns a human-readable explanation for the verdict.
func LicenseMessage(spdx string, verdict LicenseVerdict) string {
	normalized := normalizeSPDX(spdx)

	switch verdict {
	case LicenseBlocked:
		if reason, ok := blockedLicenses[normalized]; ok {
			return fmt.Sprintf("BLOCKED: %s -- %s", normalized, reason)
		}
		return fmt.Sprintf("BLOCKED: %s", normalized)
	case LicenseCaution:
		if reason, ok := cautionLicenses[normalized]; ok {
			return fmt.Sprintf("CAUTION: %s -- %s", normalized, reason)
		}
		return fmt.Sprintf("CAUTION: %s", normalized)
	case LicenseSafe:
		if reason, ok := safeLicenses[normalized]; ok {
			return fmt.Sprintf("SAFE: %s -- %s", normalized, reason)
		}
		return fmt.Sprintf("SAFE: %s", normalized)
	default:
		return fmt.Sprintf("UNKNOWN: %s -- not in known license lists, manual review required", normalized)
	}
}
