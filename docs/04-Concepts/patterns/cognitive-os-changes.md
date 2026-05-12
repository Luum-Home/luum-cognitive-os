# Cognitive OS Changes Protocol

## Rule: Plan-First for Cognitive OS Modifications

Any modification to the Cognitive OS itself (hooks, rules, skills, squads, workflows, docs, config) MUST follow the plan-first protocol:

### Before changing Cognitive OS:

1. **Create a plan** in `plans/features/{change-name}.md` or `plans/chores/{change-name}.md`:
   ```markdown
   # {Change Name}

   ## What
   One-sentence description of the change.

   ## Why
   What problem does this solve?

   ## Files affected
   - hooks/{file} — {what changes}
   - rules/{file} — {what changes}
   - skills/{skill}/ — {what changes}

   ## Risks
   - Could break: {what}
   - Rollback: {how}

   ## Definition of Done
   - [ ] Tests pass (`/cognitive-os-test`)
   - [ ] No capability lost (`/capability-snapshot diff`)
   - [ ] Documentation updated
   ```

2. **Run `/capability-snapshot save`** before making changes
3. **Implement the change**
4. **Run `/capability-snapshot diff`** after — verify no unintended losses
5. **Run `/cognitive-os-test`** — verify all layers pass
6. **Commit with reference** to the plan file

### Exceptions (no plan needed):
- Fixing a broken hook (urgent fix)
- Updating metrics/runtime data
- Documentation typos
- Adding a new skill that doesn't modify existing files

### For project-specific changes:
This rule does NOT apply. Project changes follow the project's own workflow (SDD, direct implementation, etc.).

### Plan directory separation:
- `.cognitive-os/plans/` → Cognitive OS changes ONLY (lives in Cognitive OS repo)
- `{project}/plans/` → Project-specific changes (lives in project repo)
- NEVER mix project plans with Cognitive OS plans

### Enforcement:
- Phase reconstruction: WARN if no plan exists
- Phase production: BLOCK if no plan exists for Cognitive OS changes
