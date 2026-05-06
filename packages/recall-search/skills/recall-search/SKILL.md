<!-- SCOPE: both -->
---
name: recall-search
description: "Search past Claude Code conversations using full-text search. Use when Engram mem_search doesn't find what you're looking for -- recall searches raw conversation transcripts."
allowed-tools:
  - Bash
  - Read
audience: project
summary_line: "\"Search past Claude Code conversations using full-text search."

version: "1.0.0"
platforms: ["claude-code"]
prerequisites: []
routing_patterns:
  - pattern: '\brecall[- ]?search\b'
    confidence: 0.95
  - pattern: '\bsearch\s+(past\s+)?conversations?\b'
    confidence: 0.85
  - pattern: '\bfull[- ]?text\s+search\s+transcript\b'
    confidence: 0.75
---

# Recall Search

## When to Use
- After `mem_search` returns no results for a topic you know was discussed
- When looking for exact phrases or code snippets from past sessions
- When trying to resume a previous session

## Prerequisites
Install recall: `cargo install recall-cli` or download from https://github.com/zippoxer/recall/releases

## Steps
1. Search for the topic: `recall search "{query}" --context 3`
2. If results found, show the relevant conversation context
3. If a session should be resumed: `recall read {session_id}` to get full context
4. Optionally save key findings to Engram for future fast lookup

## Fallback Chain
This skill is the LAST step in the memory search protocol:
1. `mem_search` (Engram -- structured observations)
2. `mem_get_observation` (Engram -- full content)
3. `recall search` (raw conversation transcripts)
