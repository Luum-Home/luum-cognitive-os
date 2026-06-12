# Portable DoD Profiles

Use these profiles as evidence-based overlays on top of the base Definition of Done. They are portable categories, not stack mandates. Apply a profile only when changed files or task scope show that surface is involved.

Before applying a profile, read the checker output:

- `dod_profiles` tells you which work surface changed.
- `stack_signals` tells you which language/framework/package-manager/test-runner
  evidence was detected from manifests and config files.

Bind each checklist item to the detected stack. If `stack_signals` is empty or
does not cover the touched surface, keep the generic DoD, state the uncertainty,
and ask for or inspect project-local validation instructions before making a
stack-specific completion claim.

## Backend API / Server Work

Use for server handlers, API routes, services, jobs, webhooks, auth, persistence, migrations, queues, and scheduled work.

Check:

- Entry points are thin; domain logic lives in services or equivalent reusable modules.
- Inputs are validated at the boundary with the project's configured schema/validation mechanism.
- Auth, authorization, tenant/scope checks, entitlement/plan checks, and rate limits are server-side when relevant.
- Persistence access uses the repository's central data access conventions; no ad-hoc connection, collection, or path logic is introduced.
- Mutations that need atomicity use transactions, locks, idempotency keys, or an equivalent project-native guarantee.
- Errors are typed or normalized; responses do not leak internal stack traces, provider errors, secrets, or PII.
- Webhooks verify provider authenticity, reserve events before mutation, acknowledge quickly, and move heavy work out of the request path.
- Jobs and migrations are idempotent, resumable, auditable, and have rollback or recovery notes.
- Tests cover success, invalid input, unauthenticated/unauthorized access, domain failures, and idempotency or retry behavior when relevant.
- Validation commands are discovered from repo evidence, such as configured unit/integration tests, API contract tests, type checks, lints, or migration dry-runs.

## Frontend Feature / App Work

Use for user-facing screens, routes, feature components, client hooks, forms, app-shell changes, navigation, and state management.

Check:

- Route/page files stay compositional; feature logic lives in feature modules, hooks, services, or equivalent project-local structure.
- Server/client boundaries are explicit for the framework in use; server-only dependencies do not leak into client/browser code.
- Navigation and route parameters use project conventions and validate dynamic input.
- User-visible text follows the project's i18n/localization policy; hardcoded copy is justified when the project has no i18n layer.
- Forms validate inputs, expose accessible labels/errors, and show submitting/disabled state.
- Async views define loading, empty, error, success, and disabled/permission states where applicable.
- Design-system or shared UI primitives are reused before introducing ad-hoc visual patterns.
- Accessibility covers semantic roles, keyboard operation, focus management, labels, alt text, live regions, and contrast where relevant.
- Performance-sensitive changes consider image optimization, code splitting, list virtualization, import size, and measured memoization.
- Analytics, logging, and error reporting use typed/project-approved wrappers and respect consent/privacy rules.
- Tests cover render, critical interactions, async states, validation errors, permissions/entitlements, and localization where relevant.

## UI Component / Design-System Work

Use for reusable components, primitives, design-system buckets, tokens, themes, and shared visual APIs.

Check:

- Public API is explicit: props/types/variants/defaults are documented or inferable from code conventions.
- Shared primitives are factored when two or more components repeat the same slots, variants, token maps, or context behavior.
- Types are centralized according to project convention and avoid coupling public types to implementation values when that would create cycles.
- Tokens or theme variables are namespaced and reference semantic tokens rather than hardcoded visual values when a token system exists.
- Component implementation forwards refs or exposes composition hooks when the project expects composability.
- Variants, sizes, states, slots, and polymorphic behavior are tested or covered by examples/stories.
- Accessibility includes names/descriptions, focus behavior, keyboard interaction, disabled/busy/error state, and screen-reader behavior.
- Public labels are localizable or caller-provided when the component renders user-facing text.
- Barrel/index exports separate values and types when the project uses that convention.
- Refactors migrate consumers, update mocks/imports, remove orphaned tokens/stories/docs, and preserve or document API compatibility.

## Storybook / Component Documentation Work

Use for stories, MDX/component docs, visual examples, interaction examples, and design-system documentation.

Check:

- Stories live in the repository's documented story location and do not import app/feature code into design-system examples unless explicitly allowed.
- Story metadata, args, argTypes, controls, and docs describe every public prop needed by consumers.
- Coverage includes default, variants, sizes, important states, and a matrix when combinations are numerous.
- Interactive components include play/interaction tests using the project's configured Storybook test utilities.
- Accessibility checks are enabled or a documented exception explains why they are deferred.
- Examples use realistic copy/data and avoid placeholder text that hides layout, i18n, or accessibility issues.
- New story categories update story sorting/navigation if the project maintains an ordered taxonomy.
- Visual review or snapshot approval is recorded when the repository uses visual regression tooling.

## Applying Multiple Profiles

Apply every profile touched by the diff. For example, a reusable dialog plus its stories uses both `ui-component` and `storybook-docs`; a checkout mutation plus a client form uses both `backend-api` and `frontend-feature`.

Do not copy these bullets into a PR blindly. Convert them into concrete acceptance criteria and commands for the repository's detected stack and actual configured tooling.
