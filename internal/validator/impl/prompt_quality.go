package impl

import (
	"context"
	"fmt"
	"regexp"
	"strings"

	"github.com/luum/cos-dispatch/internal/validator"
	"github.com/luum/cos-dispatch/pkg/hook"
)

// PromptQualityValidator scores Agent prompts on five dimensions of quality
// (specificity, actionability, context, measurability, scope clarity), each in
// [0, 20]. Total <30 emits a warning. Ports hooks/prompt-quality.sh.
//
// This validator is advisory and never blocks.
type PromptQualityValidator struct {
	// Specificity
	specFile   *regexp.Regexp
	specPath   *regexp.Regexp
	specSymbol *regexp.Regexp
	// Actionability
	actVerb   *regexp.Regexp
	actInPath *regexp.Regexp
	// Context
	ctxBackground *regexp.Regexp
	ctxConvention *regexp.Regexp
	// Measurability
	measAccept *regexp.Regexp
	measExit   *regexp.Regexp
	measVerify *regexp.Regexp
	// Scope
	scopeCount   *regexp.Regexp
	scopeBounded *regexp.Regexp
	scopeUnbound *regexp.Regexp
	scopeNumber  *regexp.Regexp
}

// NewPromptQualityValidator constructs the validator with all scoring patterns
// pre-compiled.
func NewPromptQualityValidator() *PromptQualityValidator {
	return &PromptQualityValidator{
		specFile:      regexp.MustCompile(`\.(go|ts|py|js|sh|yaml|yml|json|md)\b`),
		specPath:      regexp.MustCompile(`(src/|internal/|pkg/|lib/|hooks/|rules/|skills/|tests/|templates/)`),
		specSymbol:    regexp.MustCompile(`[A-Z][a-z]+[A-Z][a-z]+|[a-z]+_[a-z]+|func |function |class |def `),
		actVerb:       regexp.MustCompile(`(?i)\b(implement|create|add|fix|refactor|migrate|remove|update|write|delete|replace|extract|move)\b`),
		actInPath:     regexp.MustCompile(`(?i)\b(in|for|to|at|within)\b.*\.(go|ts|py|js|sh|yaml|json|md)\b`),
		ctxBackground: regexp.MustCompile(`(?i)\b(because|since|due to|context|background|constraint|requirement|decision|previously|existing|current)\b`),
		ctxConvention: regexp.MustCompile(`(?i)\b(pattern|convention|architecture|standard|follow|use the|using the)\b`),
		measAccept:    regexp.MustCompile(`(?i)(acceptance criteria|success criteria|definition of done|ACCEPTANCE CRITERIA)`),
		measExit:      regexp.MustCompile(`(?i)(exits? 0|should pass|must pass|returns? [0-9]|wc -l|grep -c)`),
		measVerify:    regexp.MustCompile(`(?i)(verify|verification|expected result|expected output|test that)`),
		scopeCount:    regexp.MustCompile(`(?i)[0-9]+\s*(file|endpoint|service|item|route|test|module|function|component|line)`),
		scopeBounded:  regexp.MustCompile(`(?i)\b(only|just|single|specific|this|one|the following)\b`),
		scopeUnbound:  regexp.MustCompile(`(?i)\b(all|every|entire|whole|everything|complete the)\b`),
		scopeNumber:   regexp.MustCompile(`[0-9]+`),
	}
}

func (v *PromptQualityValidator) Name() string { return "prompt-quality" }
func (v *PromptQualityValidator) Category() validator.ValidatorCategory {
	return validator.CategoryCPU
}

// Validate scores the Agent prompt and emits a Warn when total < 30.
func (v *PromptQualityValidator) Validate(_ context.Context, hookCtx *hook.Context) *validator.Result {
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

	specificity := 0
	if v.specFile.MatchString(prompt) {
		specificity += 10
	}
	if v.specPath.MatchString(prompt) {
		specificity += 5
	}
	if v.specSymbol.MatchString(prompt) {
		specificity += 5
	}
	specificity = capScore(specificity)

	actionability := 0
	if v.actVerb.MatchString(prompt) {
		actionability += 10
	}
	if v.actInPath.MatchString(prompt) {
		actionability += 10
	}
	actionability = capScore(actionability)

	contextScore := 0
	if v.ctxBackground.MatchString(prompt) {
		contextScore += 10
	}
	if v.ctxConvention.MatchString(prompt) {
		contextScore += 5
	}
	if len(prompt) > 200 {
		contextScore += 5
	}
	contextScore = capScore(contextScore)

	measurability := 0
	if v.measAccept.MatchString(prompt) {
		measurability += 10
	}
	if v.measExit.MatchString(prompt) {
		measurability += 5
	}
	if v.measVerify.MatchString(prompt) {
		measurability += 5
	}
	measurability = capScore(measurability)

	scopeClarity := 0
	if v.scopeCount.MatchString(prompt) {
		scopeClarity += 10
	}
	if v.scopeBounded.MatchString(prompt) {
		scopeClarity += 5
	}
	// The bash hook adds 5 unless an unbounded scope keyword appears WITHOUT a
	// numeric counter.
	if !(v.scopeUnbound.MatchString(prompt) && !v.scopeNumber.MatchString(prompt)) {
		scopeClarity += 5
	}
	scopeClarity = capScore(scopeClarity)

	total := specificity + actionability + contextScore + measurability + scopeClarity

	if total >= 30 {
		return validator.Pass()
	}

	var suggestions []string
	if specificity < 10 {
		suggestions = append(suggestions, "Add specific file paths, function names, or concrete references")
	}
	if actionability < 10 {
		suggestions = append(suggestions, "Use a clear action verb with a target (e.g., 'implement X in Y')")
	}
	if contextScore < 10 {
		suggestions = append(suggestions, "Include relevant background, constraints, or prior decisions")
	}
	if measurability < 10 {
		suggestions = append(suggestions, "Add acceptance criteria, verification commands, or expected outcomes")
	}
	if scopeClarity < 10 {
		suggestions = append(suggestions, "Define bounded scope (e.g., '3 files', 'this endpoint') instead of unbounded terms")
	}

	msg := fmt.Sprintf("PROMPT QUALITY: LOW (%d/100). Specificity=%d Actionability=%d Context=%d Measurability=%d Scope=%d. Suggestions: %s",
		total, specificity, actionability, contextScore, measurability, scopeClarity,
		strings.Join(suggestions, "; "))

	return &validator.Result{
		Passed:      false,
		ShouldBlock: false, // advisory
		Message:     msg,
		FixHint:     "Improve prompt quality before launching the agent.",
		Reference: validator.Reference{
			Code: "COS-QUAL-002",
			URL:  "docs/04-Concepts/architecture/cos-dispatch/prompt-quality.md",
		},
		Details: map[string]string{
			"score":         fmt.Sprintf("%d", total),
			"specificity":   fmt.Sprintf("%d", specificity),
			"actionability": fmt.Sprintf("%d", actionability),
			"context":       fmt.Sprintf("%d", contextScore),
			"measurability": fmt.Sprintf("%d", measurability),
			"scope_clarity": fmt.Sprintf("%d", scopeClarity),
		},
	}
}

func capScore(s int) int {
	if s > 20 {
		return 20
	}
	return s
}
