# ADR-003: SQLite over JSONL for Pattern Storage

## Status

Accepted

## Context

The auto-improvement pipeline needs to store and query execution history. Options:
1. JSONL files (used by klaudiush and existing Cognitive OS metrics)
2. SQLite database
3. External database (PostgreSQL, Redis)

The pattern detector needs: time-window aggregations, GROUP BY validator/error_code, JOIN between executions and patterns, and sequence correlation queries. JSONL requires loading entire files into memory and implementing these operations in Go.

## Decision

SQLite for the pattern tracking database. JSONL for compatibility with existing Cognitive OS metrics that other hooks/skills consume. The Tracker writes to SQLite; a separate exporter writes JSONL summaries to `.cognitive-os/metrics/` for tools that consume that directory.

Use `modernc.org/sqlite` (pure Go, no CGo) to avoid build complexity.

## Consequences

- Indexed queries, aggregation, and ACID transactions out of the box
- No CGo dependency with `modernc.org/sqlite`
- Database file at `.cognitive-os/patterns.db` (gitignored)
- Dual-write to SQLite + JSONL adds slight complexity but maintains backward compatibility
- Migration from klaudiush's JSONL patterns is a one-time import
- SQLite file locks mean only one cos-dispatch instance can write at a time (acceptable since hooks are per-session)
