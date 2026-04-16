package impl

import (
	"context"
	"regexp"
	"strings"

	"github.com/luum/cos-dispatch/internal/validator"
	"github.com/luum/cos-dispatch/pkg/hook"
)

// CompletenessCheckerValidator inspects Agent prompts for "red flags" that
// indicate vague scope. Ports hooks/completeness-check.sh.
//
// All findings are advisory (Warn, ShouldBlock=false) — agents still launch.
// The bash hook also writes a metrics JSONL line; that side effect lives in
// the dispatcher now, not in individual validators.
type CompletenessCheckerValidator struct {
	rules []completenessRule
}

type completenessRule struct {
	name    string
	trigger *regexp.Regexp
	exempt  *regexp.Regexp // if matches, the trigger is suppressed
	warning string
}

// NewCompletenessCheckerValidator constructs the validator with the same red
// flag patterns as the bash hook.
func NewCompletenessCheckerValidator() *CompletenessCheckerValidator {
	return &CompletenessCheckerValidator{
		rules: []completenessRule{
			{
				name:    "all-files-no-list",
				trigger: regexp.MustCompile(`(?i)\ball\b.{0,20}\bfiles?\b`),
				exempt:  regexp.MustCompile(`(?i)FILES TO PROCESS|file list|files:$`),
				warning: "RED FLAG: 'all files' mentioned without listing them. Run discovery first (grep/find) and list EVERY file.",
			},
			{
				name:    "migration-no-count",
				trigger: regexp.MustCompile(`(?i)\b(complete|finish|migrate)\b.{0,30}\b(migration|endpoint|service)`),
				exempt:  regexp.MustCompile(`(?i)[0-9]+ (endpoint|file|service|item|route)`),
				warning: "RED FLAG: Migration/completion task without item count. Specify exactly HOW MANY endpoints/files/items.",
			},
			{
				name:    "rebrand-no-grep",
				trigger: regexp.MustCompile(`(?i)\b(rebrand|rename)\b.{0,20}\b(everything|all|every)\b`),
				exempt:  regexp.MustCompile(`(?i)grep|occurrence|[0-9]+ (file|match|occurrence)`),
				warning: "RED FLAG: Rebrand/rename 'everything' without occurrence count. Run grep first to count exact occurrences.",
			},
			{
				name:    "follow-patterns-vague",
				trigger: regexp.MustCompile(`(?i)\bfollow\b.{0,20}\b(pattern|convention|style|approach)\b`),
				exempt:  regexp.MustCompile(`(?i)ginext|EntityWith|ControllerInterface|UseCaseInterface|example:|pattern:`),
				warning: "RED FLAG: 'follow patterns' without specifying WHICH patterns. List exact pattern names and examples.",
			},
			{
				name:    "no-acceptance-criteria",
				trigger: regexp.MustCompile(`.+`), // always triggers
				exempt:  regexp.MustCompile(`(?i)ACCEPTANCE CRITERIA`),
				warning: "RED FLAG: No ACCEPTANCE CRITERIA section. Every agent prompt must include measurable acceptance criteria.",
			},
			{
				name:    "update-docs-no-target",
				trigger: regexp.MustCompile(`(?i)\bupdate\b.{0,15}\b(doc|documentation|readme)\b`),
				exempt:  regexp.MustCompile(`(?i)[a-zA-Z0-9_-]+\.md|specific doc|which doc`),
				warning: "RED FLAG: 'update docs' without specifying WHICH docs. List the exact files to update.",
			},
			{
				name:    "large-scope-no-enum",
				trigger: regexp.MustCompile(`(?i)\b(across|throughout|entire|whole|every)\b.{0,20}\b(codebase|project|repo|backend|frontend)\b`),
				exempt:  regexp.MustCompile(`(?i)SCOPE|FILES TO PROCESS|[0-9]+ (file|item|service)`),
				warning: "RED FLAG: Large scope ('across/throughout/entire') without explicit enumeration. Run /exhaustive-prompt first.",
			},
		},
	}
}

func (v *CompletenessCheckerValidator) Name() string { return "completeness-check" }
func (v *CompletenessCheckerValidator) Category() validator.ValidatorCategory {
	return validator.CategoryCPU
}

// verificationCommandRe matches inline verification commands like
// `command` = 0 or `command` exits 0, used by the long-prompt rule below.
var verificationCommandRe = regexp.MustCompile("`[^`]+`\\s*(=|>=|exits)\\s*[0-9]")

// verificationKeywordRe matches free-text verification mentions.
var verificationKeywordRe = regexp.MustCompile(`(?i)VERIFICATION|verify|verification command`)

// Validate scans the agent prompt for red flags.
func (v *CompletenessCheckerValidator) Validate(_ context.Context, hookCtx *hook.Context) *validator.Result {
	if hookCtx == nil || hookCtx.ToolName != hook.ToolAgent {
		return validator.Pass()
	}

	prompt := hookCtx.ToolInput.Prompt
	if prompt == "" {
		prompt = hookCtx.ToolInput.Description
	}
	if prompt == "" {
		return validator.Pass()
	}

	var warnings []string
	for _, r := range v.rules {
		if !r.trigger.MatchString(prompt) {
			continue
		}
		if r.exempt != nil && r.exempt.MatchString(prompt) {
			continue
		}
		warnings = append(warnings, r.warning)
	}

	// Long-prompt heuristic: prompts > 200 chars must include a verification
	// command or keyword.
	if len(prompt) > 200 {
		if !verificationCommandRe.MatchString(prompt) && !verificationKeywordRe.MatchString(prompt) {
			warnings = append(warnings,
				"RED FLAG: No verification commands found. Include commands with expected results (e.g., `command` = 0).")
		}
	}

	if len(warnings) == 0 {
		return validator.Pass()
	}

	msg := "COMPLETENESS CHECK: " +
		strings.Join(warnings, " | ") +
		" — RECOMMENDATION: Run /exhaustive-prompt to generate a complete, verifiable prompt."
	return &validator.Result{
		Passed:      false,
		ShouldBlock: false, // advisory
		Message:     msg,
		FixHint:     "Run /exhaustive-prompt before launching the agent.",
		Reference: validator.Reference{
			Code: "COS-QUAL-001",
			URL:  "docs/architecture/cos-dispatch/completeness-check.md",
		},
	}
}
