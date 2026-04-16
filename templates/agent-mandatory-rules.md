## MANDATORY PROJECT RULES (injected by subagent-context-injector)

These rules are automatically injected into every sub-agent's context via the SubagentStart hook. They are non-negotiable.

### Filesystem: Symlinks
This project uses symlinks extensively (hooks/ → packages/*/hooks/, tests/ → packages/*/tests/).
- ALWAYS use `readlink -f <path>` before classifying any file as missing
- ALWAYS use `ls -la <path>` to verify symlinks before reporting absence
- Use `file_exists_strict()` from `hooks/_lib/file_checker.sh` for file checks
- NEVER report a file as 'missing' or 'ghost' without verifying with readlink -f
- Previous audits reported false 'missing' files due to naive checks — do NOT repeat this

### Auditing
- When counting components, resolve symlinks first — a symlink and its target are ONE component
- Cross-validate findings: if you find N 'missing' items, verify EACH ONE individually before reporting N
- Use /audit-integrity skill for standardized component audits

### Code Quality
- Do NOT create tests that only verify file existence — tests MUST execute code and verify behavior
- Do NOT add metadata fields to files unless code exists to consume them
- Do NOT add config flags unless code exists to read them

### Engram
- Save important discoveries to engram via mem_save before returning
- Search engram for prior context before starting work that might have been done before

### Performance
- Do NOT add `python3 -c` calls inside while-read loops (O(n) subprocess spawns)
- Consolidate multiple Python calls into a single script
- If adding a hook, estimate its latency impact
