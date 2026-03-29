Score this agent prompt for ambiguity on a 0-100 scale.

Signals to check (add points when detected):
- No file paths or specific code references (+15): the prompt describes a code change but names no specific files, directories, or code locations
- Unbounded scope (+20): words like "all", "every", "complete", "entire" appear without a concrete count (e.g. "47 endpoints" would negate this signal)
- Missing technology/framework specification (+15): the prompt says "implement", "create", "build", or "set up" without naming a language, framework, or library
- Action verbs without clear targets (+20): action like "add auth", "improve performance", "fix bugs" without specifying which files, components, or modules
- Unanswered questions in the prompt (+15): the prompt contains open questions ("which?", "what type?", "where should?") that need answers before work can begin
- Very short prompt under 50 characters (+20): insufficient detail for reliable agent execution
- No success/acceptance criteria (+10): no verification commands, expected results, or pass/fail conditions

Important context:
- A prompt that references a prior conversation ("follow the approach we discussed") is NOT vague if it implies shared context
- A prompt that names specific files, functions, or line numbers is specific even if short
- Acceptance criteria like "tests pass", "build succeeds", "grep returns 0" count as criteria

Return ONLY valid JSON on a single line, no markdown formatting:
{"score": N, "verdict": "PASS|WARN|BLOCK", "questions": ["question1", "question2"]}

Verdict thresholds: score 0-29 = PASS, 30-60 = WARN, 61-100 = BLOCK.
Questions should be specific clarifying questions the user should answer before launching the agent. Include 0 questions for PASS.

Examples:

Input: "Add auth to the project"
Output: {"score": 70, "verdict": "BLOCK", "questions": ["Which files or directories should be modified?", "Which auth framework should be used (JWT, OAuth, session)?", "What are the acceptance criteria?"]}

Input: "Implement GetUserByID in internal/users/application/use_cases/get_user_by_id.go using ginext. Acceptance criteria: go build exits 0, go test ./internal/users/... exits 0."
Output: {"score": 0, "verdict": "PASS", "questions": []}

Input: "Fix all the bugs"
Output: {"score": 75, "verdict": "BLOCK", "questions": ["Which bugs specifically? List file paths or error messages.", "How many bugs are in scope?", "What verification proves each bug is fixed?"]}

Input: "Refactor the user service DTOs in internal/users/application/dtos/ to use the new naming convention. Tests must pass."
Output: {"score": 10, "verdict": "PASS", "questions": []}

The agent prompt to evaluate:
---
{{prompt}}
---
