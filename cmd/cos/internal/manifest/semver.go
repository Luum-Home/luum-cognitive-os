package manifest

import (
	"fmt"
	"strconv"
	"strings"
)

// ParseVersion extracts major, minor, patch from a semver string.
// Strips any leading "v" prefix and ignores pre-release/build metadata.
func ParseVersion(v string) (major, minor, patch int, err error) {
	v = strings.TrimPrefix(v, "v")

	// Strip pre-release and build metadata.
	if idx := strings.IndexAny(v, "-+"); idx >= 0 {
		v = v[:idx]
	}

	parts := strings.SplitN(v, ".", 3)
	if len(parts) != 3 {
		return 0, 0, 0, fmt.Errorf("invalid semver %q: expected MAJOR.MINOR.PATCH", v)
	}

	major, err = strconv.Atoi(parts[0])
	if err != nil {
		return 0, 0, 0, fmt.Errorf("invalid major version %q: %w", parts[0], err)
	}
	minor, err = strconv.Atoi(parts[1])
	if err != nil {
		return 0, 0, 0, fmt.Errorf("invalid minor version %q: %w", parts[1], err)
	}
	patch, err = strconv.Atoi(parts[2])
	if err != nil {
		return 0, 0, 0, fmt.Errorf("invalid patch version %q: %w", parts[2], err)
	}

	return major, minor, patch, nil
}

// CompareVersions compares two semver strings.
// Returns -1 (a<b), 0 (a==b), or 1 (a>b).
// Pre-release and build metadata are ignored for comparison.
func CompareVersions(a, b string) int {
	aMaj, aMin, aPat, aErr := ParseVersion(a)
	bMaj, bMin, bPat, bErr := ParseVersion(b)

	// Unparseable versions sort last.
	if aErr != nil && bErr != nil {
		return 0
	}
	if aErr != nil {
		return -1
	}
	if bErr != nil {
		return 1
	}

	if aMaj != bMaj {
		return cmpInt(aMaj, bMaj)
	}
	if aMin != bMin {
		return cmpInt(aMin, bMin)
	}
	return cmpInt(aPat, bPat)
}

// MatchesConstraint checks if a version satisfies a constraint string.
//
// Supported constraint formats:
//   - "*"              any version
//   - ""               any version (empty = no constraint)
//   - "1.0.0"          exact match
//   - ">=1.0.0"        greater than or equal
//   - ">1.0.0"         greater than
//   - "<=1.0.0"        less than or equal
//   - "<1.0.0"         less than
//   - "!=1.0.0"        not equal
//   - "^1.2.0"         compatible: >=1.2.0, <2.0.0 (^0.2.3 means >=0.2.3, <0.3.0)
//   - "~1.2.3"         approximately: >=1.2.3, <1.3.0
//   - ">=1.0.0,<2.0.0" comma-separated AND of constraints
func MatchesConstraint(version, constraint string) bool {
	constraint = strings.TrimSpace(constraint)

	// Wildcard or empty constraint matches everything.
	if constraint == "" || constraint == "*" {
		return true
	}

	// Comma-separated constraints are ANDed.
	if strings.Contains(constraint, ",") {
		for _, part := range strings.Split(constraint, ",") {
			if !MatchesConstraint(version, part) {
				return false
			}
		}
		return true
	}

	// Caret: ^MAJOR.MINOR.PATCH
	if strings.HasPrefix(constraint, "^") {
		return matchCaret(version, strings.TrimPrefix(constraint, "^"))
	}

	// Tilde: ~MAJOR.MINOR.PATCH
	if strings.HasPrefix(constraint, "~") {
		return matchTilde(version, strings.TrimPrefix(constraint, "~"))
	}

	// Comparison operators.
	if strings.HasPrefix(constraint, ">=") {
		return CompareVersions(version, strings.TrimSpace(constraint[2:])) >= 0
	}
	if strings.HasPrefix(constraint, "<=") {
		return CompareVersions(version, strings.TrimSpace(constraint[2:])) <= 0
	}
	if strings.HasPrefix(constraint, "!=") {
		return CompareVersions(version, strings.TrimSpace(constraint[2:])) != 0
	}
	if strings.HasPrefix(constraint, ">") {
		return CompareVersions(version, strings.TrimSpace(constraint[1:])) > 0
	}
	if strings.HasPrefix(constraint, "<") {
		return CompareVersions(version, strings.TrimSpace(constraint[1:])) < 0
	}

	// Exact match (bare version string).
	return CompareVersions(version, constraint) == 0
}

// matchCaret implements the ^ (caret/compatible) constraint.
//
// For major > 0: allows changes that do not modify the major version.
//
//	^1.2.3 means >=1.2.3, <2.0.0
//
// For major == 0, minor > 0: allows changes that do not modify the minor version.
//
//	^0.2.3 means >=0.2.3, <0.3.0
//
// For major == 0, minor == 0: allows changes that do not modify the patch version.
//
//	^0.0.3 means >=0.0.3, <0.0.4
func matchCaret(version, target string) bool {
	tMaj, tMin, tPat, err := ParseVersion(target)
	if err != nil {
		return false
	}

	// Version must be >= target.
	if CompareVersions(version, target) < 0 {
		return false
	}

	vMaj, vMin, vPat, err := ParseVersion(version)
	if err != nil {
		return false
	}

	if tMaj > 0 {
		// ^MAJOR.x.x: same major, any minor/patch >= target.
		return vMaj == tMaj
	}
	if tMin > 0 {
		// ^0.MINOR.x: same major and minor.
		return vMaj == tMaj && vMin == tMin
	}
	// ^0.0.PATCH: exact match on all three.
	return vMaj == tMaj && vMin == tMin && vPat == tPat
}

// matchTilde implements the ~ (tilde/approximately) constraint.
// ~1.2.3 means >=1.2.3, <1.3.0 (same major.minor, patch >= target patch).
func matchTilde(version, target string) bool {
	tMaj, tMin, _, err := ParseVersion(target)
	if err != nil {
		return false
	}

	// Version must be >= target.
	if CompareVersions(version, target) < 0 {
		return false
	}

	vMaj, vMin, _, err := ParseVersion(version)
	if err != nil {
		return false
	}

	return vMaj == tMaj && vMin == tMin
}

// cmpInt returns -1, 0, or 1 for integer comparison.
func cmpInt(a, b int) int {
	if a < b {
		return -1
	}
	if a > b {
		return 1
	}
	return 0
}
