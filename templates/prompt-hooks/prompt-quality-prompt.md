Score this agent prompt for quality on 5 dimensions (each 0-20, total 0-100).

Dimensions:
1. Specificity (0-20): file paths (.go, .ts, .py), directory paths (src/, internal/), function/class names, concrete code references. No specific references = 0, some = 10, detailed = 20.
2. Actionability (0-20): clear action verb (implement, create, fix, refactor, migrate, update, write) paired with a target. Vague action = 0, verb present = 10, verb + target with file = 20.
3. Context (0-20): background info, constraints, prior decisions, architectural patterns, conventions. Missing = 0, some context = 10, rich context or prompt > 200 chars = 20.
4. Measurability (0-20): acceptance criteria, verification commands (exits 0, grep -c, wc -l), expected outcomes. None = 0, mentions verification = 10, explicit acceptance criteria section = 20.
5. Scope clarity (0-20): bounded scope with counts ("3 files", "this endpoint") vs unbounded ("all", "every", "entire" without numbers). Unbounded = 0, bounded language = 10, explicit counts = 20.

Quality levels: score < 30 = "warning", 30-60 = "info", > 60 = "good".

If score < 30, include specific suggestions for improvement in the suggestions array.

Return ONLY valid JSON on a single line, no markdown formatting:
{"score": N, "specificity": N, "actionability": N, "context": N, "measurability": N, "scope_clarity": N, "level": "warning|info|good", "suggestions": ["suggestion1"]}

Examples:

Input: "Fix the bugs"
Output: {"score": 10, "specificity": 0, "actionability": 10, "context": 0, "measurability": 0, "scope_clarity": 0, "level": "warning", "suggestions": ["Add specific file paths or function names", "Define acceptance criteria with verification commands", "Specify bounded scope (which bugs, how many)"]}

Input: "Implement GetUserByID in internal/users/application/use_cases/get_user_by_id.go using ginext. Follow the existing repository pattern. Acceptance criteria: go build exits 0, go test ./internal/users/... exits 0."
Output: {"score": 90, "specificity": 20, "actionability": 20, "context": 15, "measurability": 20, "scope_clarity": 15, "level": "good", "suggestions": []}

Input: "Refactor all the services to use the new pattern"
Output: {"score": 20, "specificity": 0, "actionability": 10, "context": 5, "measurability": 0, "scope_clarity": 5, "level": "warning", "suggestions": ["Add specific file paths for the services to refactor", "Add acceptance criteria with verification commands", "Specify how many services and which ones"]}

The agent prompt to evaluate:
---
{{prompt}}
---
