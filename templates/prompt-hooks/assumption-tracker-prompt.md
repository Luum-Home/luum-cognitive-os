<!-- SCOPE: both -->
Scan this agent output for assumption language and count assumptions.

Patterns to detect:
- HIGH confidence (explicit assumption language): "I assume", "I'm assuming", "I'll assume", "assuming that", "presumably", "without more info", "in the absence of", "based on context"
- MEDIUM confidence (hedging/uncertainty): "I think", "probably", "likely", "it seems", "appears to be", "I believe", "my best guess", "if I had to guess"

For each match, extract the sentence containing the assumption (max 120 chars).

Severity thresholds: 0-2 assumptions = "ok", 3+ assumptions = "warn".

Return ONLY valid JSON on a single line, no markdown formatting:
{"assumption_count": N, "assumptions": ["[HIGH] sentence1", "[MEDIUM] sentence2"], "severity": "ok|warn"}

Examples:

Input: "I implemented the endpoint using the declared framework. Tests pass with go test ./..."
Output: {"assumption_count": 0, "assumptions": [], "severity": "ok"}

Input: "I assume the database is PostgreSQL. I'll assume the default port is 5432. The migration probably needs a new table."
Output: {"assumption_count": 3, "assumptions": ["[HIGH] I assume the database is PostgreSQL.", "[HIGH] I'll assume the default port is 5432.", "[MEDIUM] The migration probably needs a new table."], "severity": "warn"}

Input: "I believe this should go in the domain layer. It seems like the API expects JSON."
Output: {"assumption_count": 2, "assumptions": ["[MEDIUM] I believe this should go in the domain layer.", "[MEDIUM] It seems like the API expects JSON."], "severity": "ok"}

The agent output to scan:
---
{{agent_output}}
---
