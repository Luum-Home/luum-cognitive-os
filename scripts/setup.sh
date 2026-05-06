#!/usr/bin/env bash
# SCOPE: project
# Cognitive OS Development Setup
# Usage: ./scripts/setup.sh [--minimal|--standard|--full]
#
# --minimal:  core tools only (python, uv, jq, go)
# --standard: + testing + security basics + engram (default)
# --full:     + all optional tools + Docker services
#
# The script is idempotent: it checks what is already installed and skips it.
set -euo pipefail

# ── Configuration ───────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
PROFILE="${1:---standard}"

# Counters
INSTALLED=0
SKIPPED=0
FAILED=0
WARNINGS=()

# Colors (disabled if not a terminal)
if [ -t 1 ]; then
  GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; BLUE='\033[0;34m'; NC='\033[0m'
else
  GREEN=''; YELLOW=''; RED=''; BLUE=''; NC=''
fi

# ── Helpers ─────────────────────────────────────────────────────────
info()  { echo -e "${BLUE}[INFO]${NC}  $*"; }
ok()    { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; WARNINGS+=("$*"); }
fail()  { echo -e "${RED}[FAIL]${NC}  $*"; }
skip()  { echo -e "${GREEN}[SKIP]${NC}  $* (already installed)"; SKIPPED=$((SKIPPED + 1)); }

has_cmd() { command -v "$1" &>/dev/null; }

install_or_skip() {
  local name="$1" check_cmd="$2" install_fn="$3"
  if has_cmd "$check_cmd"; then
    skip "$name"
  else
    info "Installing $name..."
    if eval "$install_fn"; then
      ok "$name installed"
      INSTALLED=$((INSTALLED + 1))
    else
      fail "$name installation failed"
      FAILED=$((FAILED + 1))
    fi
  fi
}

# ── Profile validation ──────────────────────────────────────────────
case "$PROFILE" in
  --minimal|--standard|--full) ;;
  *)
    echo "Usage: $0 [--minimal|--standard|--full]"
    echo ""
    echo "  --minimal   Core tools only (python, uv, jq, go)"
    echo "  --standard  + testing + security basics + engram (default)"
    echo "  --full      + all optional tools + Docker services"
    exit 1
    ;;
esac

echo "============================================"
echo "  Cognitive OS Development Setup ($PROFILE)"
echo "============================================"
echo ""

# ── 1. Check OS / Homebrew ──────────────────────────────────────────
info "Checking platform..."
OS="$(uname -s)"
ARCH="$(uname -m)"
ok "Platform: $OS $ARCH"

if [ "$OS" = "Darwin" ]; then
  if ! has_cmd brew; then
    info "Installing Homebrew..."
    # NONINTERACTIVE=1 suppresses all interactive prompts (ADR-059 §Phase 2 prerequisite)
    NONINTERACTIVE=1 /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    INSTALLED=$((INSTALLED + 1))
  else
    skip "Homebrew"
  fi
fi

# ── 2. System tools (brew / apt) ───────────────────────────────────
echo ""
info "--- System tools ---"

install_or_skip "jq" "jq" "brew install jq 2>/dev/null || sudo apt-get install -y jq 2>/dev/null"
install_or_skip "gh (GitHub CLI)" "gh" "brew install gh 2>/dev/null || sudo apt-get install -y gh 2>/dev/null"
install_or_skip "git" "git" "brew install git 2>/dev/null || sudo apt-get install -y git 2>/dev/null"

# ── 3. Python via uv ───────────────────────────────────────────────
echo ""
info "--- Python environment ---"

# Install uv
if ! has_cmd uv; then
  info "Installing uv..."
  curl -LsSf https://astral.sh/uv/install.sh | sh
  # Source the env so uv is available in this session
  export PATH="$HOME/.local/bin:$PATH"
  INSTALLED=$((INSTALLED + 1))
else
  skip "uv"
fi

# Check Python version
PYTHON_VERSION=$(python3 --version 2>/dev/null | awk '{print $2}' || echo "0.0.0")
PYTHON_MAJOR=$(echo "$PYTHON_VERSION" | cut -d. -f1)
PYTHON_MINOR=$(echo "$PYTHON_VERSION" | cut -d. -f2)

if [ "$PYTHON_MAJOR" -ge 3 ] && [ "$PYTHON_MINOR" -ge 11 ]; then
  ok "Python $PYTHON_VERSION (>= 3.11)"
else
  warn "Python $PYTHON_VERSION is below 3.11. Consider upgrading: uv python install 3.11"
fi

# Create venv and install deps
if [ ! -d "$PROJECT_DIR/.venv" ]; then
  info "Creating Python virtual environment..."
  (cd "$PROJECT_DIR" && uv venv)
  INSTALLED=$((INSTALLED + 1))
else
  skip "Python venv (.venv)"
fi

info "Installing Python dependencies (profile: $PROFILE)..."
case "$PROFILE" in
  --minimal)
    (cd "$PROJECT_DIR" && uv pip install -e ".")
    ;;
  --standard)
    (cd "$PROJECT_DIR" && uv pip install -e ".[dev]")
    ;;
  --full)
    (cd "$PROJECT_DIR" && uv pip install -e ".[dev]")
    # Extra tools not in pyproject.toml
    (cd "$PROJECT_DIR" && uv pip install cosmic-ray garak 2>/dev/null || true)
    ;;
esac
ok "Python dependencies installed"

# ── 4. Go via goenv ─────────────────────────────────────────────────
echo ""
info "--- Go environment ---"

install_or_skip "goenv" "goenv" "brew install goenv 2>/dev/null"

GO_VERSION_FILE="$PROJECT_DIR/.go-version"
if [ -f "$GO_VERSION_FILE" ]; then
  REQUIRED_GO=$(cat "$GO_VERSION_FILE" | tr -d '[:space:]')
  CURRENT_GO=$(go version 2>/dev/null | awk '{print $3}' | sed 's/go//' || echo "none")

  if [ "$CURRENT_GO" = "$REQUIRED_GO" ]; then
    skip "Go $REQUIRED_GO"
  else
    if has_cmd goenv; then
      info "Installing Go $REQUIRED_GO via goenv..."
      goenv install "$REQUIRED_GO" 2>/dev/null || true
      goenv global "$REQUIRED_GO"
      ok "Go $REQUIRED_GO installed"
      INSTALLED=$((INSTALLED + 1))
    else
      warn "goenv not available. Install Go $REQUIRED_GO manually."
    fi
  fi
else
  warn ".go-version file not found. Skipping Go setup."
fi

# ── 5. engram CLI ───────────────────────────────────────────────────
if [ "$PROFILE" != "--minimal" ]; then
  echo ""
  info "--- engram (persistent memory) ---"
  if has_cmd engram; then
    skip "engram CLI"
  else
    warn "engram CLI not found. Install it and configure in ~/.claude/settings.json"
    warn "  See: https://github.com/Gentleman-Programming/engram"
  fi
fi

# ── 6. CLAMP ────────────────────────────────────────────────────────
if [ "$PROFILE" != "--minimal" ]; then
  echo ""
  info "--- CLAMP (project migration) ---"
  if has_cmd clamp; then
    skip "CLAMP"
  else
    info "Installing CLAMP..."
    CLAMP_DIR="/usr/local/bin"
    if [ ! -w "$CLAMP_DIR" ]; then
      CLAMP_DIR="$HOME/.local/bin"
      mkdir -p "$CLAMP_DIR"
    fi
    if curl -fsSL https://raw.githubusercontent.com/wsagency/claude-move-project/main/clamp -o "$CLAMP_DIR/clamp" 2>/dev/null; then
      chmod +x "$CLAMP_DIR/clamp"
      ok "CLAMP installed to $CLAMP_DIR/clamp"
      INSTALLED=$((INSTALLED + 1))
    else
      warn "CLAMP download failed. Install manually from https://github.com/wsagency/claude-move-project"
    fi
  fi
fi

# ── 7. Security tools (standard + full) ────────────────────────────
if [ "$PROFILE" = "--standard" ] || [ "$PROFILE" = "--full" ]; then
  echo ""
  info "--- Security tools ---"
  install_or_skip "semgrep" "semgrep" "brew install semgrep 2>/dev/null || pip install semgrep 2>/dev/null"
fi

if [ "$PROFILE" = "--full" ]; then
  echo ""
  info "--- Additional security tools ---"

  # aguara (requires Go)
  if has_cmd go; then
    install_or_skip "aguara" "aguara" "go install github.com/garagon/aguara@latest"
    install_or_skip "mcp-aguara" "mcp-aguara" "go install github.com/garagon/mcp-aguara@latest"
  else
    warn "Go not available, skipping aguara/mcp-aguara install"
  fi

  # parry-guard
  install_or_skip "parry-guard" "parry-guard" "brew install vaporif/tap/parry-guard 2>/dev/null"

  # mcp-scan
  install_or_skip "mcp-scan" "mcp-scan" "pip install mcp-scan 2>/dev/null || pip3 install mcp-scan 2>/dev/null"

  # promptfoo
  if has_cmd npm; then
    install_or_skip "promptfoo" "promptfoo" "npm install -g promptfoo 2>/dev/null"
  else
    warn "npm not available, skipping promptfoo install"
  fi
fi

# ── 8. Docker services (full only) ─────────────────────────────────
if [ "$PROFILE" = "--full" ]; then
  echo ""
  info "--- Docker services ---"
  if has_cmd docker; then
    if docker info &>/dev/null; then
      ok "Docker is running"
      info "Starting infrastructure services..."
      if [ -f "$PROJECT_DIR/scripts/cos-bootstrap.sh" ]; then
        bash "$PROJECT_DIR/scripts/cos-bootstrap.sh" --profile full || warn "Docker bootstrap had issues"
      else
        warn "cos-bootstrap.sh not found, skipping Docker services"
      fi
    else
      warn "Docker is installed but not running. Start Docker Desktop to use infrastructure services."
    fi
  else
    warn "  Install from: https://docs.docker.com/get-docker/"
  fi
fi

# ── 9. Claude Code check ───────────────────────────────────────────
echo ""
info "--- Claude Code ---"
if has_cmd claude; then
  skip "Claude Code CLI"
else
  warn "Claude Code CLI not found. Install from: https://docs.anthropic.com/en/docs/claude-code"
fi

# ── 10. Verify setup ───────────────────────────────────────────────
echo ""
info "Running doctor check..."
if [ -f "$PROJECT_DIR/scripts/doctor.sh" ]; then
  bash "$PROJECT_DIR/scripts/doctor.sh" --quiet || true
fi

# ── Summary ─────────────────────────────────────────────────────────
echo ""
echo "============================================"
echo "  Setup Complete"
echo "============================================"
echo ""
echo "  Installed: $INSTALLED"
echo "  Skipped:   $SKIPPED (already present)"
echo "  Failed:    $FAILED"
echo ""

if [ ${#WARNINGS[@]} -gt 0 ]; then
  echo "  Warnings:"
  for w in "${WARNINGS[@]}"; do
    echo "    - $w"
  done
  echo ""
fi

if [ "$FAILED" -eq 0 ]; then
  echo "  Status: Ready"
else
  echo "  Status: Setup completed with $FAILED failure(s). Check output above."
fi

echo ""
echo "  Next steps:"
echo "    1. cd $PROJECT_DIR"
echo "    2. source .venv/bin/activate"
echo "    3. claude   # start Claude Code"
echo "    4. /cognitive-os-init   # initialize COS in a project"
echo ""
