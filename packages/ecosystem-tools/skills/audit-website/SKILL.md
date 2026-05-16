---
name: audit-website
description: 'Perform a comprehensive 6-category website audit (SEO, Performance,
  Security, Content/UX, Accessibility, Schema.org) with scored checkpoints and a structured
  markdown report. Each item is PASS/FAIL/N-A with an overall grade.

  '
version: 1.0.0
user-invocable: true
auto-generated: false
last-updated: 2026-03-27
license: MIT
metadata:
  author: luum
audience: project
summary_line: Perform a comprehensive 6-category website audit (SEO, Performance,
  Security…
platforms:
- claude-code
prerequisites: []
routing_intents:
- audit this website for SEO and accessibility
- run a comprehensive website quality audit
- score a site for performance security and UX
- generate a website audit report for this URL
- check a web page against audit categories
triggers:
- audit-website
- /audit-website
- 'Website Audit Report: {url}'
- Perform a comprehensive 6-category website audit (SEO, Performance, Security…
---
<!-- SCOPE: both -->
## Purpose

Audit any public website across six quality dimensions, producing actionable
findings with per-category scores and an overall grade. Adapted from the Sprut
Agent Kit website-audit pattern.

## Invocation

`/audit-website <url>`

## What to Do

### Step 1: Validate and Normalize URL

Parse the provided URL. Ensure it starts with `https://` (upgrade `http://` if
needed). Verify the URL is reachable by fetching the page. If it fails, report
the error and stop.

### Step 2: SEO Audit (10 checkpoints)

Check each item and record PASS, FAIL, or N/A:

| # | Checkpoint | Pass Criteria |
|---|-----------|---------------|
| 1 | Title tag | Present and fewer than 60 characters |
| 2 | Meta description | Present and fewer than 160 characters |
| 3 | H1 uniqueness | Exactly one `<h1>` element on the page |
| 4 | Canonical URL | `<link rel="canonical">` present with valid href |
| 5 | Sitemap.xml | `{origin}/sitemap.xml` returns 200 |
| 6 | Robots.txt | `{origin}/robots.txt` returns 200 |
| 7 | Structured data | At least one `<script type="application/ld+json">` block present |
| 8 | Image alt texts | All `<img>` elements have non-empty `alt` attributes |
| 9 | URL structure | Page URL uses lowercase slug-friendly paths (no query params for content pages, no uppercase, no special chars beyond hyphens) |
| 10 | Internal linking | Page contains at least 2 internal links (same origin) |

### Step 3: Performance Audit (6 checkpoints)

Use browser tools, Lighthouse data, or observable signals:

| # | Checkpoint | Pass Criteria |
|---|-----------|---------------|
| 1 | TTFB | Time to First Byte < 200ms (measure via fetch timing or report N/A if not measurable) |
| 2 | LCP | Largest Contentful Paint < 2.5s (from Lighthouse or PageSpeed Insights API, N/A if unavailable) |
| 3 | CLS | Cumulative Layout Shift < 0.1 (from Lighthouse or PageSpeed Insights API, N/A if unavailable) |
| 4 | FID/INP | First Input Delay or Interaction to Next Paint < 200ms (N/A if not measurable) |
| 5 | Image optimization | Images use WebP or AVIF format (check `<img>` src extensions and `<picture>` sources) |
| 6 | JS bundle size | Total JS transferred < 500KB (inspect page resources or report N/A) |

### Step 4: Security Audit (4 checkpoints)

| # | Checkpoint | Pass Criteria |
|---|-----------|---------------|
| 1 | HTTPS | URL uses `https://` and no mixed content warnings |
| 2 | Security headers | Response includes Content-Security-Policy, Strict-Transport-Security, and X-Frame-Options |
| 3 | Mixed content | No HTTP resources loaded on HTTPS page |
| 4 | Server version | `Server` header does not expose version numbers (e.g., `nginx/1.21.0` is a FAIL) |

### Step 5: Content/UX Audit (6 checkpoints)

| # | Checkpoint | Pass Criteria |
|---|-----------|---------------|
| 1 | Mobile responsive | `<meta name="viewport">` present with `width=device-width` |
| 2 | Readable font sizes | Body font size >= 16px (check computed style or CSS declarations) |
| 3 | Contrast ratio | Text meets WCAG AA contrast ratio (4.5:1 for normal text). Report N/A if not determinable from source inspection alone |
| 4 | Clear CTAs | Page contains at least one `<a>` or `<button>` with action-oriented text (e.g., "Sign up", "Get started", "Learn more") |
| 5 | No broken links | Sample up to 10 internal links and verify they return 200 |
| 6 | 404 page | `{origin}/this-page-should-not-exist-404-test` returns a non-empty body (custom 404 page) |

### Step 6: Accessibility Audit (5 checkpoints)

| # | Checkpoint | Pass Criteria |
|---|-----------|---------------|
| 1 | ARIA landmarks | Page has at least one ARIA landmark role (`main`, `navigation`, `banner`, `contentinfo`) or equivalent HTML5 semantic elements (`<main>`, `<nav>`, `<header>`, `<footer>`) |
| 2 | Keyboard navigation | Interactive elements (`<a>`, `<button>`, `<input>`) have no `tabindex="-1"` that removes them from tab order |
| 3 | Skip links | A skip-to-content link exists (anchor targeting `#main`, `#content`, or similar) |
| 4 | Form labels | All `<input>` elements (except `type="hidden"`) have associated `<label>` or `aria-label` |
| 5 | Color-independent info | No reliance on color alone for conveying information (check for icons, text labels, or patterns alongside color indicators). Report N/A if page has no color-coded elements |

### Step 7: Schema.org Audit (3 checkpoints)

| # | Checkpoint | Pass Criteria |
|---|-----------|---------------|
| 1 | Organization or LocalBusiness | JSON-LD contains `@type: Organization` or `@type: LocalBusiness` |
| 2 | BreadcrumbList | JSON-LD contains `@type: BreadcrumbList` or page has breadcrumb navigation markup |
| 3 | FAQ or HowTo | JSON-LD contains `@type: FAQPage` or `@type: HowTo` where content is applicable. N/A if the page is not a FAQ or instructional page |

### Step 8: Calculate Scores

For each category:

```
category_score = passed_count / (total_items - na_count) * 100
```

Overall score = weighted average of all category scores (equal weight per category).

Grade thresholds:
- 90-100: **Excellent**
- 70-89: **Good**
- 50-69: **Needs Work**
- < 50: **Critical**

### Step 9: Generate Report

Output a structured markdown report:

```markdown
# Website Audit Report: {url}

**Date**: {date}
**Overall Grade**: {grade} ({score}%)

## Summary

| Category | Score | Passed | Failed | N/A |
|----------|-------|--------|--------|-----|
| SEO | {score}% | {n} | {n} | {n} |
| Performance | {score}% | {n} | {n} | {n} |
| Security | {score}% | {n} | {n} | {n} |
| Content/UX | {score}% | {n} | {n} | {n} |
| Accessibility | {score}% | {n} | {n} | {n} |
| Schema.org | {score}% | {n} | {n} | {n} |

## Detailed Findings

### SEO ({score}%)

| # | Checkpoint | Result | Details |
|---|-----------|--------|---------|
| 1 | Title tag | PASS/FAIL | {details} |
...

### Performance ({score}%)
...

### Security ({score}%)
...

### Content/UX ({score}%)
...

### Accessibility ({score}%)
...

### Schema.org ({score}%)
...

## Top Recommendations

1. {highest-impact recommendation}
2. {second recommendation}
3. {third recommendation}
```

### Step 10: Save to Engram

Save the audit results:

```
mem_save(
  title: "Website audit: {url}",
  type: "discovery",
  scope: "project",
  topic_key: "docs/website-audit/{domain}",
  content: "{summary with scores and top 5 findings}"
)
```
