# Dashboard — Archived

> **Status:** archived as of 2026-05-05.
> **Authoritative decision:** [ADR-169 — Dashboard Formal Demotion](../docs/adrs/ADR-169-dashboard-formal-demotion.md).

## What this directory was

A skeleton Next.js 15 + React 19 + Tailwind 4 admin UI for Cognitive OS, started on 2026-03-29 as a possible Phase 2 of the project. The build reached:

- App skeleton (`app/layout.tsx`, `app/page.tsx`)
- Two routes: `/rules`, `/skills`
- Three components: `header`, `sidebar`, `stat-card`
- API client stub (`lib/cos-api.ts`)
- Dockerfile, package.json, Tailwind config

Last modified: 2026-03-29. Approximately 30% of a usable admin surface.

## Why it was archived


>



## What you should do

- **Do not depend on this directory.** Nothing in the repo imports from `dashboard/app`, `dashboard/components`, or `dashboard/lib`.

## Why the files remain on disk

The directory is preserved (not deleted) so that the demotion is reversible if the falsifiable claim in ADR-169 fires. Deletion would lose the prior architectural exploration. The files are no-ops — `next.config.ts` will not be invoked by any active script.

`node_modules/` and `.next/` are gitignored.
