#!/usr/bin/env bash
# Create a GitHub Release for Cognitive OS
# Auto-generates release notes from the actual codebase state
# Usage: bash scripts/create-release.sh [version]
set -uo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VERSION="${1:-$(cat "$PROJECT_ROOT/VERSION" 2>/dev/null || echo '0.1.0')}"
NOTES_FILE="/tmp/cos-release-notes-${VERSION}.md"

echo "Generating release notes for v${VERSION}..."

# Count actual components
RULES_COUNT=$(find "$PROJECT_ROOT/rules" -name "*.md" -not -name "RULES-COMPACT.md" 2>/dev/null | wc -l | tr -d ' ')
HOOKS_COUNT=$(find "$PROJECT_ROOT/hooks" -name "*.sh" -not -path "*/_*" 2>/dev/null | wc -l | tr -d ' ')
SKILLS_COUNT=$(find "$PROJECT_ROOT/skills" -mindepth 1 -maxdepth 1 -type d -not -name "auto-generated" -not -name "_shared" 2>/dev/null | wc -l | tr -d ' ')
LIBS_COUNT=$(find "$PROJECT_ROOT/lib" -name "*.py" -not -name "__init__.py" 2>/dev/null | wc -l | tr -d ' ')
TESTS_COUNT=$(python3 -m pytest "$PROJECT_ROOT/tests/" --collect-only -q 2>/dev/null | tail -1 | grep -oE '[0-9]+' | head -1 || echo "2700+")
DOCS_COUNT=$(find "$PROJECT_ROOT/docs" -name "*.md" 2>/dev/null | wc -l | tr -d ' ')

# Count Docker services
DOCKER_SERVICES=0
if [ -f "$PROJECT_ROOT/docker-compose.cognitive-os.yml" ]; then
    DOCKER_SERVICES=$(grep -c "^  [a-z].*:" "$PROJECT_ROOT/docker-compose.cognitive-os.yml" 2>/dev/null || echo "0")
fi

# Detect cos CLI version
COS_VERSION=""
if [ -f "$PROJECT_ROOT/cmd/cos/internal/cli/root.go" ]; then
    COS_VERSION=$(grep 'Version:' "$PROJECT_ROOT/cmd/cos/internal/cli/root.go" 2>/dev/null | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1)
fi

# Generate release notes
cat > "$NOTES_FILE" << NOTES
# Cognitive OS v${VERSION}

> "No existe el mejor modelo. Existe la mejor orquestación de modelos."

An open-source operating system for AI coding agents. Makes them safer, smarter, and cheaper through multi-model orchestration.

## Quick Start

\`\`\`bash
bash scripts/cos-init.sh --minimal    # Core rules + hooks
bash scripts/cos-init.sh --standard   # + SDD pipeline + safety mesh
bash scripts/cos-init.sh --full       # Everything
\`\`\`

## What's Included

| Component | Count |
|-----------|-------|
| Rules | ${RULES_COUNT} |
| Hooks | ${HOOKS_COUNT} |
| Skills | ${SKILLS_COUNT} |
| Lib modules | ${LIBS_COUNT} |
| Tests | ${TESTS_COUNT} |
| Docs | ${DOCS_COUNT} |
| Docker services | ${DOCKER_SERVICES} |

## Key Features

- **SDD Pipeline**: Structured development (explore → propose → spec → design → tasks → apply → verify → archive)
- **Safety Mesh**: Multi-layer defense (clarification gate, scope proportionality, anti-hallucination, claim validation, rate limiting)
- **Multi-Model Factory**: 3-layer orchestration (strategic/execution/worker)
- **Agent Bus**: Valkey pub/sub with heartbeat and progress tracking
- **Singularity Controller**: MAPE-K autonomous loop for self-healing
- **cos CLI**: Package manager for AI agent components (v${COS_VERSION:-0.1.0})
- **Performance Monitor**: p50/p95/p99 latency, bottleneck detection
- **Token Economy**: Cost dashboard with real-price predictions
- **Crash Recovery**: Periodic checkpoints via git stash
- **OKR Consequences**: Auto-promote/warn/degrade agents based on performance

## Architecture

5-layer Clean Architecture for Agent OS:
- Layer 1: Rules (behavioral constraints, markdown)
- Layer 2: Skills (agent procedures, markdown)
- Layer 3: Hooks (lifecycle automation, bash)
- Layer 4: Libs (runtime infrastructure, Python)
- Layer 5: Externals (Docker services, APIs)

## Links

- [Quick Start](docs/quickstart.md)
- [Getting Started](docs/getting-started.md)
- [Architecture Principles](docs/architecture-principles.md)
- [FAQ](docs/faq.md)
- [Roadmap](docs/roadmap.md)

## License

Apache-2.0
NOTES

echo ""
echo "Components detected:"
echo "  Rules:    ${RULES_COUNT}"
echo "  Hooks:    ${HOOKS_COUNT}"
echo "  Skills:   ${SKILLS_COUNT}"
echo "  Libs:     ${LIBS_COUNT}"
echo "  Tests:    ${TESTS_COUNT}"
echo "  Docs:     ${DOCS_COUNT}"
echo "  Docker:   ${DOCKER_SERVICES}"
echo ""

if command -v gh >/dev/null 2>&1; then
    echo "Creating GitHub Release..."
    gh release create "v${VERSION}" \
        --title "Cognitive OS v${VERSION}" \
        --notes-file "$NOTES_FILE" \
        --target "release/v${VERSION}"
    echo "✅ Release v${VERSION} created"
else
    echo "Release notes: $NOTES_FILE"
    echo ""
    echo "gh CLI not found. Run:"
    echo "  gh release create v${VERSION} --title 'Cognitive OS v${VERSION}' --notes-file $NOTES_FILE --target release/v${VERSION}"
fi
