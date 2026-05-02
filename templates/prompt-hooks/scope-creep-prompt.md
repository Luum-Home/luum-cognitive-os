<!-- SCOPE: both -->
Check if the edited file is within the approved task scope.

Task scope (approved paths):
{{approved_paths}}

Task description: {{task_description}}

Edited file: {{file_path}}

Rules for matching:
- Exact match: file path equals an approved path
- Prefix match: file path starts with an approved directory (e.g., scope "internal/users/" matches "internal/users/handler.go")
- Substring match: approved path appears within the file path

If the file matches ANY approved path by any rule, it is in scope.

Return ONLY valid JSON on a single line, no markdown formatting:
{"in_scope": true|false, "match_type": "exact|prefix|substring|none", "matched_path": "the approved path that matched or null", "file_path": "the edited file path"}

Examples:

Approved paths: ["internal/users/", "tests/unit/test_user"]
Edited file: "internal/users/handler.go"
Output: {"in_scope": true, "match_type": "prefix", "matched_path": "internal/users/", "file_path": "internal/users/handler.go"}

Approved paths: ["internal/users/handler.go", "internal/users/dto.go"]
Edited file: "internal/payments/handler.go"
Output: {"in_scope": false, "match_type": "none", "matched_path": null, "file_path": "internal/payments/handler.go"}

Approved paths: ["src/auth/", "tests/"]
Edited file: "src/auth/middleware/jwt.go"
Output: {"in_scope": true, "match_type": "prefix", "matched_path": "src/auth/", "file_path": "src/auth/middleware/jwt.go"}
