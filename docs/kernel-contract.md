# Kernel Contract

> Minimal durable core for Cognitive OS.

This document defines the smallest set of system contracts that should be
treated as kernel-level and therefore changed conservatively.

## Kernel Scope

The kernel is intentionally narrow:

- canonical hook context and event model
- policy engine contracts
- policy registry and dispatch semantics
- package manifest specification

Everything else should prefer to live as:

- adapter
- package
- plugin
- gateway module
- provider integration
- execution strategy

## Why This Matters

The AI ecosystem changes too quickly for provider-specific assumptions to live
at the center of the system. The kernel must be stable enough to survive:

- provider turnover
- model deprecation
- gateway churn
- IDE payload changes
- tool schema drift

## Source of Truth

The machine-readable source of truth is:

- [manifests/kernel-contract.yaml](../manifests/kernel-contract.yaml)

That manifest is backed by automated contract tests and manual verification
guidance so the kernel boundary remains explicit, visible, and enforceable.
