package installer

import "path/filepath"

// canonicalSkillsDir returns the future source-of-truth location for portable skills.
func canonicalSkillsDir(projectRoot string) string {
	return filepath.Join(projectRoot, ".cognitive-os", "skills", "cos")
}

// canonicalRulesDir returns the future source-of-truth location for portable rules.
func canonicalRulesDir(projectRoot string) string {
	return filepath.Join(projectRoot, ".cognitive-os", "rules", "cos")
}

// claudeSkillsProjectionDir returns the active Claude projection for skills.
func claudeSkillsProjectionDir(projectRoot string) string {
	return filepath.Join(projectRoot, ".claude", "skills")
}

// claudeRulesProjectionDir returns the active Claude projection for rules.
func claudeRulesProjectionDir(projectRoot string) string {
	return filepath.Join(projectRoot, ".claude", "rules", "cos")
}
