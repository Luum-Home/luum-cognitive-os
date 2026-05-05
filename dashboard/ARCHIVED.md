# Dashboard — Archived

> **Status:** archived as of 2026-05-05.
> **Authoritative decision:** [ADR-169 — Dashboard Formal Demotion](../docs/adrs/ADR-169-dashboard-formal-demotion.md).
> **Audit that triggered the decision:** [`docs/reports/paperclip-integration-audit-2026-05-05.md`](../docs/reports/paperclip-integration-audit-2026-05-05.md).

## What this directory was

A skeleton Next.js 15 + React 19 + Tailwind 4 admin UI for Cognitive OS, started on 2026-03-29 as a possible Phase 2 of the project. The build reached:

- App skeleton (`app/layout.tsx`, `app/page.tsx`)
- Two routes: `/rules`, `/skills`
- Three components: `header`, `sidebar`, `stat-card`
- API client stub (`lib/cos-api.ts`)
- Dockerfile, package.json, Tailwind config

Last modified: 2026-03-29. Approximately 30% of a usable admin surface.

## Why it was archived

Two days before the dashboard was abandoned, [`docs/paperclip-integration.md`](../docs/paperclip-integration.md) was written (2026-03-27) declaring:

> *"This integration eliminates the need to build a custom web dashboard (originally planned as Phase 2). Instead, Cognitive OS pushes state to Paperclip via its REST API, and Paperclip renders the UX."*
>
> ***"Paperclip is the UI, Cognitive OS is the engine."***

The dashboard was abandoned because that decision was correct: Paperclip already existed as a governance dashboard product, and pushing COS state to it via REST is a smaller surface than maintaining a parallel web app.

The 2026-05-05 audit verified the decision still holds and resulted in **wiring 6 previously-unregistered Paperclip hooks** into `.claude/settings.json` (commit referenced in ADR-169). With those hooks live, Paperclip receives 6 of 7 documented mappings; the seventh (skills marketplace) is intentionally deferred and does not justify the dashboard.

## What you should do

- **Do not depend on this directory.** Nothing in the repo imports from `dashboard/app`, `dashboard/components`, or `dashboard/lib`.
- **Do not resurrect this directory** without a new ADR that explicitly revokes ADR-169 and documents what gap Paperclip cannot cover.
- **For COS UI needs**, use Paperclip via the integration documented in [`docs/paperclip-integration.md`](../docs/paperclip-integration.md) and the runbook [`docs/runbooks/run-cos-in-docker.md`](../docs/runbooks/run-cos-in-docker.md).

## Why the files remain on disk

The directory is preserved (not deleted) so that the demotion is reversible if the falsifiable claim in ADR-169 fires. Deletion would lose the prior architectural exploration. The files are no-ops — `next.config.ts` will not be invoked by any active script.

`node_modules/` and `.next/` are gitignored.
