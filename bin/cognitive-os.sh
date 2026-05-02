#!/usr/bin/env bash
# cognitive-os — CLI entry point
set -euo pipefail

VERSION="0.1.0"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PACKAGE_DIR="$(dirname "$SCRIPT_DIR")"
CONFIG_FILE="cognitive-os.yaml"
source "$PACKAGE_DIR/scripts/_lib/settings-driver.sh"

# ── Helpers ────────────────────────────────────────────────────────────

# Minimal YAML value reader — extracts simple scalar values from YAML
# Usage: yaml_get "key.subkey" file.yaml
yaml_get() {
  local key="$1" file="$2"
  # Only handles flat key: value lines — sufficient for our config
  grep -E "^\s*${key}:" "$file" 2>/dev/null | head -1 | sed 's/^[^:]*:\s*//' | tr -d "'\"\r"
}

# Extract the scalar value from a "key: value" YAML line — no subprocesses.
# Usage: _yaml_val "$line"
_yaml_val() {
  local line="$1"
  local val="${line#*:}"
  val="${val#"${val%%[![:space:]]*}"}"   # strip leading whitespace
  val="${val%"${val##*[![:space:]]}"}"   # strip trailing whitespace
  val="${val#\"}"; val="${val%\"}"       # strip surrounding double-quotes
  val="${val#\'}"; val="${val%\'}"       # strip surrounding single-quotes
  printf '%s' "$val"
}

# Check that cognitive-os.yaml exists in cwd
require_config() {
  if [ ! -f "$CONFIG_FILE" ]; then
    echo "ERROR: $CONFIG_FILE not found in $(pwd)" >&2
    echo "Run 'cognitive-os init' first." >&2
    exit 1
  fi
}

canonical_skills_dir() {
  printf '%s' ".cognitive-os/skills/cos"
}

legacy_builtin_skills_dir() {
  printf '%s' ".cognitive-os/skills"
}

canonical_rules_dir() {
  printf '%s' ".cognitive-os/rules/cos"
}

legacy_builtin_rules_dir() {
  printf '%s' ".cognitive-os/rules"
}

driver_skills_dir() {
  printf '%s' ".claude/skills"
}

driver_rules_dir() {
  if [ -d ".claude/rules/cos" ]; then
    printf '%s' ".claude/rules/cos"
  else
    printf '%s' ".claude/rules"
  fi
}

active_settings_harness() {
  cos_detect_harness "."
}

active_settings_driver_label() {
  cos_settings_driver_label "$(active_settings_harness)"
}

active_settings_driver_path() {
  cos_settings_driver_path "." "$(active_settings_harness)"
}

dir_has_skill_files() {
  local dir="${1:-}"
  [ -n "$dir" ] && [ -d "$dir" ] && find -L "$dir" -name 'SKILL.md' -print -quit 2>/dev/null | grep -q .
}

dir_has_rule_files() {
  local dir="${1:-}"
  [ -n "$dir" ] && [ -d "$dir" ] && find "$dir" -name '*.md' -print -quit 2>/dev/null | grep -q .
}

resolve_local_skill_source() {
  local name="$1"
  if [ -f "$(canonical_skills_dir)/${name}/SKILL.md" ]; then
    printf '%s' "$(canonical_skills_dir)/${name}"
    return
  fi
  if [ -f "$(legacy_builtin_skills_dir)/${name}/SKILL.md" ]; then
    printf '%s' "$(legacy_builtin_skills_dir)/${name}"
    return
  fi
  printf '%s' ""
}

resolve_local_rule_source() {
  local filename="$1"
  if [ -f "$(canonical_rules_dir)/${filename}" ]; then
    printf '%s' "$(canonical_rules_dir)/${filename}"
    return
  fi
  if [ -f "$(legacy_builtin_rules_dir)/${filename}" ]; then
    printf '%s' "$(legacy_builtin_rules_dir)/${filename}"
    return
  fi
  if [ -f "rules/${filename}" ]; then
    printf '%s' "rules/${filename}"
    return
  fi
  printf '%s' ""
}

# ── Usage ──────────────────────────────────────────────────────────────

usage() {
  cat <<EOF
cognitive-os v${VERSION} — Portable AI Agent Operating System

Usage:
  cognitive-os init                        Install Cognitive OS into the current project
  cognitive-os version                     Show version
  cognitive-os doctor                      Check installation health

  cognitive-os sources                     List configured package sources
  cognitive-os sources add <name> <url>    Add a remote source
  cognitive-os search <query>              Search across all enabled sources
  cognitive-os install <type> <name>       Install a component (skill, rule, hook, preset, mcp-server)
  cognitive-os uninstall <type> <name>     Remove an installed component
  cognitive-os list [type]                 List installed components
  cognitive-os update                      Update source indexes

  cognitive-os help                        Show this help

Types: skill, rule, hook, preset, mcp-server

Examples:
  cd your-project
  cognitive-os init                        # Installs .cognitive-os/ and cognitive-os.yaml
  cognitive-os sources                     # List package sources
  cognitive-os search "deep-research"      # Search for a skill
  cognitive-os install skill sdd-apply     # Install a skill from a source
  cognitive-os install preset lean         # Apply a preset configuration
  cognitive-os list skills                 # List installed skills

Documentation: https://github.com/luum-home/luum-cognitive-os
EOF
}

# ── Command: init ──────────────────────────────────────────────────────

cmd_init() {
  local target_dir="${1:-.}"

  if [ -d "$target_dir/.cognitive-os" ]; then
    echo "Cognitive OS is already installed in $target_dir/.cognitive-os"
    read -rp "Overwrite? (y/N): " confirm
    if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
      echo "Aborted."
      exit 0
    fi
    rm -rf "$target_dir/.cognitive-os"
  fi

  echo "Installing Cognitive OS into $target_dir..."
  cp -R "$PACKAGE_DIR/.cognitive-os" "$target_dir/.cognitive-os"

  if [ ! -f "$target_dir/cognitive-os.yaml" ]; then
    cp "$PACKAGE_DIR/cognitive-os.yaml" "$target_dir/cognitive-os.yaml"
  fi

  # Install CLAUDE.md template if not present
  if [ ! -f "$target_dir/.claude/CLAUDE.md" ]; then
    local template_file="$PACKAGE_DIR/templates/CLAUDE.md.template"
    if [ -f "$template_file" ]; then
      mkdir -p "$target_dir/.claude"
      cp "$template_file" "$target_dir/.claude/CLAUDE.md"
      echo "Created .claude/CLAUDE.md from template."
    fi
  else
    echo "Existing .claude/CLAUDE.md preserved (not overwritten)."
  fi

  echo ""
  echo "Cognitive OS installed!"
  echo ""

  # Auto-detect project size for efficiency profile suggestion
  src_count=$(find "$target_dir" \
    \( -path "$target_dir/.cognitive-os" -o -path "$target_dir/.cognitive-os/*" -o -path "$target_dir/.claude" -o -path "$target_dir/.claude/*" \) -prune \
    -o -maxdepth 5 \( -name "*.go" -o -name "*.ts" -o -name "*.py" -o -name "*.java" -o -name "*.rs" \) -print 2>/dev/null | wc -l | tr -d ' ')
  has_docker=false
  [ -f "$target_dir/docker-compose.yml" ] || [ -f "$target_dir/docker-compose.yaml" ] && has_docker=true

  if [ "$src_count" -lt 20 ] && [ "$has_docker" = false ]; then
    suggested="lean"
  elif [ "$src_count" -lt 100 ]; then
    suggested="standard"
  else
    suggested="full"
  fi

  echo "Detected $src_count source files. Suggested efficiency profile: $suggested"
  echo "To apply: cognitive-os install preset $suggested"
  echo ""

  # Suggest preset based on detection
  if [ "$src_count" -lt 20 ] && [ "$has_docker" = false ]; then
    echo "  Suggested preset: startup"
  elif [ "$has_docker" = true ] && [ "$src_count" -gt 100 ]; then
    echo "  Suggested preset: enterprise"
  fi
  echo "  Apply with: cognitive-os install preset <name>"
  echo ""

  # ── Memory Inheritance (Reproduction) ──────────────────────────────────
  # Like biological reproduction: offspring inherit relevant knowledge
  # from the parent organism's experience (Engram).
  echo "  Checking for inheritable memory..."

  seed_file="$target_dir/.cognitive-os/seed-memory.md"
  inherited=0

  # Detect stack for targeted memory search
  stack_keywords=""
  [ -f "$target_dir/package.json" ] && stack_keywords="$stack_keywords node typescript react nextjs"
  [ -f "$target_dir/go.mod" ] && stack_keywords="$stack_keywords go golang gin"
  { [ -f "$target_dir/requirements.txt" ] || [ -f "$target_dir/pyproject.toml" ]; } && stack_keywords="$stack_keywords python django flask fastapi"
  [ -f "$target_dir/Cargo.toml" ] && stack_keywords="$stack_keywords rust"
  { [ -f "$target_dir/pom.xml" ] || [ -f "$target_dir/build.gradle" ]; } && stack_keywords="$stack_keywords java spring kotlin"
  { [ -f "$target_dir/docker-compose.yml" ] || [ -f "$target_dir/docker-compose.yaml" ]; } && stack_keywords="$stack_keywords docker containers infrastructure"

  if [ -n "$stack_keywords" ]; then
    cat > "$seed_file" << 'HEADER'
# Seed Memory — Inherited from Parent Organism

> This file was generated during `cos init` from the parent organism's Engram memory.
> It contains knowledge that may be relevant to this project based on stack detection.
> Review and delete entries that don't apply. Add project-specific knowledge over time.
> This file is NOT loaded into the context window — it's reference material for the agent.

HEADER

    # Append detected stack keywords for agent to use on first session
    echo "## Detected Stack" >> "$seed_file"
    echo "" >> "$seed_file"
    echo "Keywords:$stack_keywords" >> "$seed_file"
    echo "" >> "$seed_file"
    echo "## Inherited Knowledge" >> "$seed_file"
    echo "" >> "$seed_file"
    echo "_The agent will populate this section from Engram on first session start._" >> "$seed_file"
    echo "" >> "$seed_file"

    echo "  Detected stack keywords:$stack_keywords"
    echo "  Seed memory written to .cognitive-os/seed-memory.md"
    echo ""
    echo "  Note: Connect Engram to populate with inherited knowledge from past projects."
    echo "  The agent will search Engram for relevant patterns on first session start."
    inherited=1
  fi

  if [ "$inherited" -eq 0 ]; then
    echo "  No stack detected for memory inheritance. Starting fresh."
  fi

  echo ""
  echo "Next steps:"
  echo "  1. cd $target_dir"
  echo "  2. claude"
  echo "  3. /cognitive-os-init"
  echo ""
}

# ── Command: version ───────────────────────────────────────────────────

cmd_version() {
  echo "cognitive-os v${VERSION}"
}

# ── Command: doctor ────────────────────────────────────────────────────

cmd_doctor() {
  if [ "${1:-}" = "harness" ]; then
    shift
    exec bash "$PACKAGE_DIR/scripts/cos-doctor-harness.sh" "$@"
  fi

  echo "=== Cognitive OS Doctor ==="
  echo ""

  local issues=0

  # Check .cognitive-os exists
  if [ -d ".cognitive-os" ]; then
    echo "[OK] .cognitive-os/ directory found"
  else
    echo "[!!] .cognitive-os/ directory NOT found — run: cognitive-os init"
    issues=$((issues + 1))
  fi

  # Check cognitive-os.yaml
  if [ -f "cognitive-os.yaml" ]; then
    echo "[OK] cognitive-os.yaml found"
  else
    echo "[!!] cognitive-os.yaml NOT found"
    issues=$((issues + 1))
  fi

  # Check hooks
  if [ -d ".cognitive-os/hooks" ]; then
    local hook_count
    hook_count=$(find .cognitive-os/hooks -name '*.sh' -not -path '*/_lib/*' | wc -l)
    echo "[OK] $hook_count hooks found"
  else
    echo "[!!] No hooks directory"
    issues=$((issues + 1))
  fi

  # Check skills
  if [ -d ".cognitive-os/skills" ]; then
    local skill_count
    skill_count=$(find .cognitive-os/skills -name 'SKILL.md' | wc -l)
    echo "[OK] $skill_count skills found"
  else
    echo "[!!] No skills directory"
    issues=$((issues + 1))
  fi

  # Check rules
  if [ -d ".cognitive-os/rules" ]; then
    local rule_count
    rule_count=$(find .cognitive-os/rules -name '*.md' | wc -l)
    echo "[OK] $rule_count rules found"
  else
    echo "[!!] No rules directory"
    issues=$((issues + 1))
  fi

  local settings_driver_label
  local settings_driver_path
  settings_driver_label="$(active_settings_driver_label)"
  settings_driver_path="$(active_settings_driver_path)"

  # Check active settings driver
  if [ -f "$settings_driver_path" ]; then
    echo "[OK] $settings_driver_label found (hooks registered)"
  else
    echo "[--] $settings_driver_label not found — run /cognitive-os-init for the active harness"
  fi

  # Check Docker
  if command -v docker >/dev/null 2>&1; then
    echo "[OK] Docker available"
  else
    echo "[--] Docker not available (optional — needed for observability stack)"
  fi

  # Check sources configuration
  if grep -q '^sources:' "$CONFIG_FILE" 2>/dev/null; then
    local source_count
    source_count=$(grep -c '^\s*- name:' "$CONFIG_FILE" 2>/dev/null || echo "0")
    echo "[OK] $source_count package sources configured"
  else
    echo "[--] No package sources configured in cognitive-os.yaml"
  fi

  echo ""
  if [ "$issues" -eq 0 ]; then
    echo "All checks passed!"
  else
    echo "$issues issue(s) found. Run 'cognitive-os init' to fix."
  fi
}

# ── Command: sources ───────────────────────────────────────────────────

# Parse all registries from cognitive-os.yaml into parallel arrays.
# Populates: _REG_NAMES, _REG_TYPES, _REG_URLS, _REG_PATHS, _REG_ENABLED,
#             _REG_DESCS, _REG_PROVIDES, _REG_COUNT
_parse_registries() {
  _REG_NAMES=() _REG_TYPES=() _REG_URLS=() _REG_PATHS=()
  _REG_ENABLED=() _REG_DESCS=() _REG_PROVIDES=()
  _REG_COUNT=0

  local in_sources_section=false
  local in_sources=false
  local name="" type="" url="" path="" enabled="" description="" provides=""

  _flush_reg() {
    if [ -n "$name" ]; then
      _REG_NAMES+=("$name")
      _REG_TYPES+=("$type")
      _REG_URLS+=("$url")
      _REG_PATHS+=("$path")
      _REG_ENABLED+=("${enabled:-true}")
      _REG_DESCS+=("$description")
      _REG_PROVIDES+=("$provides")
      _REG_COUNT=$((_REG_COUNT + 1))
    fi
    name="" type="" url="" path="" enabled="" description="" provides=""
  }

  while IFS= read -r line; do
    # Detect the top-level 'sources:' section
    if [[ "$line" =~ ^sources: ]]; then
      in_sources_section=true
      continue
    fi

    # If we found the sources section, look for registries: within it
    if $in_sources_section && ! $in_sources; then
      if [[ "$line" =~ ^[[:space:]]*registries: ]]; then
        in_sources=true
        continue
      fi
      # A new top-level key means we left the sources section without finding registries
      if [[ -n "$line" && "$line" =~ ^[a-zA-Z] ]]; then
        in_sources_section=false
        continue
      fi
      continue
    fi

    # Detect end: a non-indented, non-comment, non-empty line while in_sources
    if $in_sources && [[ -n "$line" && "$line" =~ ^[a-zA-Z] ]]; then
      _flush_reg
      break
    fi

    if ! $in_sources; then continue; fi

    # New registry entry
    if [[ "$line" =~ ^[[:space:]]*-[[:space:]]*name: ]]; then
      _flush_reg
      name=$(_yaml_val "${line#*- name}")
      continue
    fi

    # Skip comments and blank lines
    if [[ "$line" =~ ^[[:space:]]*# ]] || [[ -z "${line//[[:space:]]/}" ]]; then
      continue
    fi

    # Parse fields within an entry
    if [[ "$line" =~ ^[[:space:]]*type: ]]; then
      type=$(_yaml_val "$line")
    elif [[ "$line" =~ ^[[:space:]]*url: ]]; then
      url=$(_yaml_val "$line")
    elif [[ "$line" =~ ^[[:space:]]*path: ]]; then
      path=$(_yaml_val "$line")
    elif [[ "$line" =~ ^[[:space:]]*enabled: ]]; then
      enabled=$(_yaml_val "$line")
    elif [[ "$line" =~ ^[[:space:]]*description: ]]; then
      description=$(_yaml_val "$line")
    elif [[ "$line" =~ ^[[:space:]]*provides: ]]; then
      provides=$(_yaml_val "$line")
    fi
  done < "$CONFIG_FILE"

  # Flush final entry if EOF reached while still in sources
  if $in_sources; then
    _flush_reg
  fi
}

cmd_sources() {
  require_config

  if [ "${1:-}" = "add" ]; then
    cmd_sources_add "${2:-}" "${3:-}"
    return
  fi

  echo "=== Configured Package Sources ==="
  echo ""

  _parse_registries

  local i
  for ((i = 0; i < _REG_COUNT; i++)); do
    _print_source "${_REG_NAMES[$i]}" "${_REG_TYPES[$i]}" "${_REG_URLS[$i]}" \
                  "${_REG_PATHS[$i]}" "${_REG_ENABLED[$i]}" "${_REG_DESCS[$i]}" \
                  "${_REG_PROVIDES[$i]}"
  done

  if [ "$_REG_COUNT" -eq 0 ]; then
    echo "  No sources configured. Add sources in cognitive-os.yaml under sources.registries"
  fi
}

_print_source() {
  local name="$1" type="$2" url="$3" path="$4" enabled="$5" description="$6" provides="$7"
  local status="enabled"
  if [ "$enabled" = "false" ]; then
    status="disabled"
  fi

  local location="$url"
  if [ -n "$path" ] && [ -z "$url" ]; then
    location="$path"
  fi

  printf "  %-16s %-8s %-10s %s\n" "$name" "[$type]" "($status)" "$location"
  if [ -n "$description" ]; then
    printf "  %-16s %s\n" "" "$description"
  fi
  if [ -n "$provides" ]; then
    printf "  %-16s provides: %s\n" "" "$provides"
  fi
  echo ""
}

cmd_sources_add() {
  local name="$1" url="$2"

  if [ -z "$name" ] || [ -z "$url" ]; then
    echo "Usage: cognitive-os sources add <name> <url>" >&2
    exit 1
  fi

  require_config

  # Check if source already exists
  if grep -qE "^\s*- name:\s*${name}\s*$" "$CONFIG_FILE" 2>/dev/null; then
    echo "Source '$name' already exists in $CONFIG_FILE" >&2
    exit 1
  fi

  # Append the new source before the end of registries section
  # Find the line with the last registry entry's enabled/provides and append after it
  # Simpler approach: append before the comment block about local/private sources
  if grep -q '# Local/private sources' "$CONFIG_FILE"; then
    sed -i.bak '/# Local\/private sources/i\
\    - name: '"$name"'\
\      type: remote\
\      url: '"$url"'\
\      enabled: true\
' "$CONFIG_FILE"
    rm -f "${CONFIG_FILE}.bak"
  else
    # Fallback: append at the end of the file in sources.registries
    cat >> "$CONFIG_FILE" <<EOF

    - name: $name
      type: remote
      url: $url
      enabled: true
EOF
  fi

  echo "Added source '$name' ($url) to $CONFIG_FILE"
}

# ── Command: search ────────────────────────────────────────────────────

cmd_search() {
  local query="${1:-}"

  if [ -z "$query" ]; then
    echo "Usage: cognitive-os search <query>" >&2
    exit 1
  fi

  require_config

  echo "=== Searching for '$query' ==="
  echo ""

  _parse_registries

  local found=0 i
  for ((i = 0; i < _REG_COUNT; i++)); do
    _search_source "${_REG_NAMES[$i]}" "${_REG_TYPES[$i]}" "${_REG_PATHS[$i]}" \
                   "${_REG_ENABLED[$i]}" "${_REG_URLS[$i]}" "$query" && found=$((found + 1))
  done

  if [ "$found" -eq 0 ]; then
    echo "No results found for '$query'."
  fi
}

_search_source() {
  local name="$1" type="$2" path="$3" enabled="$4" url="$5" query="$6"

  if [ "$enabled" = "false" ]; then
    return 1
  fi

  if [ "$type" = "local" ] && [ -n "$path" ]; then
    if [ -d "$path" ]; then
      echo "[$name] (local: $path)"
      # Search skills
      local results
      results=$(find "$path/skills" -name 'SKILL.md' -path "*${query}*" 2>/dev/null || true)
      if [ -n "$results" ]; then
        echo "$results" | while read -r f; do
          local skill_name
          skill_name=$(basename "$(dirname "$f")")
          echo "  skill: $skill_name"
        done
      fi
      # Search rules
      results=$(find "$path/rules" -name '*.md' 2>/dev/null | xargs grep -li "$query" 2>/dev/null || true)
      if [ -n "$results" ]; then
        echo "$results" | while read -r f; do
          local rule_name
          rule_name=$(basename "$f" .md)
          echo "  rule: $rule_name"
        done
      fi
      # Search hooks
      results=$(find "$path/hooks" -name '*.sh' -not -path '*/_lib/*' 2>/dev/null | xargs grep -li "$query" 2>/dev/null || true)
      if [ -n "$results" ]; then
        echo "$results" | while read -r f; do
          local hook_name
          hook_name=$(basename "$f")
          echo "  hook: $hook_name"
        done
      fi
      echo ""
      return 0
    fi
    return 1
  elif [ "$type" = "remote" ] && [ -n "$url" ]; then
    echo "[$name] (remote: $url)"

    # Skills.sh registry — use registry.skild.sh/discover API
    if echo "$url" | grep -qi 'skild\.\|skills\.sh'; then
      local encoded_query
      encoded_query=$(printf '%s' "$query" | jq -sRr @uri 2>/dev/null || printf '%s' "$query")
      local api_url="https://registry.skild.sh/discover?q=${encoded_query}&limit=10"
      local response
      response=$(curl -s --max-time 5 "$api_url" 2>/dev/null) || true
      if echo "$response" | jq -e '.ok == true and (.items | length > 0)' >/dev/null 2>&1; then
        echo "$response" | jq -r '.items[] | "  skill: \(.title)  — \(.description // "No description" | .[0:100])"' 2>/dev/null
      else
        echo "  No results found — visit $url to search manually"
      fi
      echo ""
      return 0
    fi

    # MCP Registry — use registry.modelcontextprotocol.io/v0.1/servers API
    if echo "$url" | grep -qi 'modelcontextprotocol\|mcp.*registry'; then
      local encoded_query
      encoded_query=$(printf '%s' "$query" | jq -sRr @uri 2>/dev/null || printf '%s' "$query")
      local api_url="https://registry.modelcontextprotocol.io/v0.1/servers?search=${encoded_query}&limit=10"
      local response
      response=$(curl -s --max-time 5 "$api_url" 2>/dev/null) || true
      if echo "$response" | jq -e '.servers | length > 0' >/dev/null 2>&1; then
        echo "$response" | jq -r '.servers[] | "  mcp-server: \(.server.name)  — \(.server.description // "No description" | .[0:100])"' 2>/dev/null
      else
        echo "  No results found — visit $url to search manually"
      fi
      echo ""
      return 0
    fi

    # Generic remote source — no API known
    echo "  Remote search not available for this source — visit $url"
    echo ""
    return 0
  fi

  return 1
}

# ── Command: install ───────────────────────────────────────────────────

cmd_install() {
  local comp_type="${1:-}"
  local comp_name="${2:-}"

  if [ -z "$comp_type" ] || [ -z "$comp_name" ]; then
    echo "Usage: cognitive-os install <type> <name>" >&2
    echo "Types: skill, rule, hook, preset, mcp-server" >&2
    exit 1
  fi

  require_config

  case "$comp_type" in
    skill)   _install_skill "$comp_name" ;;
    rule)    _install_rule "$comp_name" ;;
    hook)    _install_hook "$comp_name" ;;
    preset)  _install_preset "$comp_name" ;;
    mcp-server) _install_mcp_server "$comp_name" ;;
    *)
      echo "Unknown component type: $comp_type" >&2
      echo "Valid types: skill, rule, hook, preset, mcp-server" >&2
      exit 1
      ;;
  esac
}

_install_skill() {
  local name="$1"
  local target
  target="$(driver_skills_dir)/${name}"

  if [ -d "$target" ]; then
    echo "Skill '$name' is already installed at $target"
    read -rp "Overwrite? (y/N): " confirm
    if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
      echo "Aborted."
      return
    fi
  fi

  # Try local sources first
  local installed=false

  local skill_source
  skill_source="$(resolve_local_skill_source "$name")"
  if [ -n "$skill_source" ] && [ -d "$skill_source" ] && [ -f "$skill_source/SKILL.md" ]; then
    mkdir -p "$target"
    cp -r "$skill_source/"* "$target/"
    echo "Installed skill '$name' from cos-builtin (local)"
    installed=true
  fi

  # Try remote sources: Skills.sh registry
  if ! $installed; then
    echo "Skill '$name' not found in local sources."
    echo "Searching Skills.sh registry..."

    # Search for the skill by name in the registry
    local encoded_name
    encoded_name=$(printf '%s' "$name" | jq -sRr @uri 2>/dev/null || printf '%s' "$name")
    local search_response
    search_response=$(curl -s --max-time 5 "https://registry.skild.sh/discover?q=${encoded_name}&limit=5" 2>/dev/null) || true

    # Try to find an exact or close match
    local skill_source=""
    local skill_title=""
    if echo "$search_response" | jq -e '.ok == true and (.items | length > 0)' >/dev/null 2>&1; then
      # Look for exact name match first, then first result
      skill_source=$(echo "$search_response" | jq -r --arg name "$name" \
        '(.items[] | select(.title == $name or (.title | test($name; "i")))) // .items[0] | .source.url // empty' 2>/dev/null)
      skill_title=$(echo "$search_response" | jq -r --arg name "$name" \
        '(.items[] | select(.title == $name or (.title | test($name; "i")))) // .items[0] | .title // empty' 2>/dev/null)
    fi

    if [ -n "$skill_source" ]; then
      # Source is a GitHub URL — try to fetch raw SKILL.md from it
      # Convert github.com/owner/repo/tree/branch/path to raw URL
      local raw_url
      raw_url=$(echo "$skill_source" | sed -E 's|github\.com/([^/]+)/([^/]+)/tree/([^/]+)/(.*)|raw.githubusercontent.com/\1/\2/\3/\4/SKILL.md|')
      if [ "$raw_url" = "$skill_source" ]; then
        # Conversion failed, try appending SKILL.md
        raw_url="${skill_source}/SKILL.md"
      fi

      echo "  Found: $skill_title"
      echo "  Fetching from: $raw_url"
      mkdir -p "$target"
      if curl -fsSL --max-time 10 "https://${raw_url}" -o "$target/SKILL.md" 2>/dev/null; then
        # Verify we got a markdown file (not HTML error page)
        if head -1 "$target/SKILL.md" | grep -q '<!DOCTYPE\|<html' 2>/dev/null; then
          rm -rf "$target"
          echo "  Download returned HTML instead of SKILL.md content." >&2
          echo "  Install manually from: $skill_source" >&2
          return 1
        fi
        echo "Installed skill '$name' from Skills.sh (remote)"
      else
        rm -rf "$target"
        echo "  Could not download SKILL.md from source." >&2
        echo "  Install manually: skild install $skill_title" >&2
        echo "  Or visit: $skill_source" >&2
        return 1
      fi
    elif [ -n "$skill_title" ]; then
      # Found in registry but no GitHub source URL
      echo "  Found '$skill_title' on Skills.sh but no direct download available." >&2
      echo "  Install using the skild CLI: skild install $skill_title" >&2
      echo "  Or visit: https://hub.skild.sh" >&2
      return 1
    else
      echo "  Skill '$name' not found in Skills.sh registry." >&2
      echo "  Search online:" >&2
      echo "    - https://hub.skild.sh (Skills.sh Hub)" >&2
      echo "    - https://registry.modelcontextprotocol.io (MCP Registry)" >&2
      return 1
    fi
  fi
}

_install_rule() {
  local name="$1"
  local target_dir
  target_dir="$(driver_rules_dir)"
  local filename="${name}.md"

  # Add .md extension if not present
  if [[ "$name" == *.md ]]; then
    filename="$name"
    name="${name%.md}"
  fi

  mkdir -p "$target_dir"

  local rule_source
  rule_source="$(resolve_local_rule_source "$filename")"
  if [ -n "$rule_source" ] && [ -f "$rule_source" ]; then
    cp "$rule_source" "$target_dir/${filename}"
    echo "Installed rule '$name' from local rule surfaces -> $target_dir/${filename}"
    return
  fi

  echo "Rule '$name' not found in any local source." >&2
  return 1
}

_install_hook() {
  local name="$1"
  local filename="$name"

  # Add .sh extension if not present
  if [[ "$name" != *.sh ]]; then
    filename="${name}.sh"
  fi

  # Check local source
  if [ -f ".cognitive-os/hooks/${filename}" ]; then
    echo "Hook '$filename' is available in .cognitive-os/hooks/"
    echo "Hooks are registered in $(active_settings_driver_label), not copied."
    echo "Use /cognitive-os-init or scripts/apply-efficiency-profile.sh to register hooks."
    return
  fi

  echo "Hook '$filename' not found in .cognitive-os/hooks/" >&2
  return 1
}

_install_preset() {
  local name="$1"
  local preset_file=""

  # Search for preset file
  for dir in "presets" ".cognitive-os/presets" "$PACKAGE_DIR/presets"; do
    if [ -f "$dir/${name}.yaml" ]; then
      preset_file="$dir/${name}.yaml"
      break
    elif [ -f "$dir/${name}.yml" ]; then
      preset_file="$dir/${name}.yml"
      break
    fi
  done

  if [ -z "$preset_file" ]; then
    echo "Preset '$name' not found." >&2
    echo "Available presets:" >&2
    _list_presets >&2
    return 1
  fi

  echo "=== Installing preset: $name ==="
  echo "Source: $preset_file"
  echo ""

  # Read and display preset info
  local description
  description=$(grep -E '^\s*description:' "$preset_file" 2>/dev/null | head -1 | sed 's/.*description:\s*//' | tr -d "'\"\r")
  if [ -n "$description" ]; then
    echo "Description: $description"
  fi

  # Read efficiency profile
  local profile
  profile=$(grep -E '^\s*efficiency_profile:' "$preset_file" 2>/dev/null | head -1 | sed 's/.*efficiency_profile:\s*//' | tr -d "'\"\r")
  if [ -n "$profile" ]; then
    echo "Efficiency profile: $profile"
    echo ""
    echo "Applying efficiency profile '$profile'..."
    if [ -f "scripts/apply-efficiency-profile.sh" ]; then
      bash "scripts/apply-efficiency-profile.sh" "$profile"
    elif [ -f "$PACKAGE_DIR/scripts/apply-efficiency-profile.sh" ]; then
      bash "$PACKAGE_DIR/scripts/apply-efficiency-profile.sh" "$profile"
    else
      echo "  (apply-efficiency-profile.sh not found — skipping hook configuration)"
    fi
  fi

  # Read capability level
  local cap_level
  cap_level=$(grep -E '^\s*capability_level:' "$preset_file" 2>/dev/null | head -1 | sed 's/.*capability_level:\s*//' | tr -d "'\"\r")
  if [ -n "$cap_level" ]; then
    echo ""
    echo "Setting capability level to $cap_level in cognitive-os.yaml..."
    if grep -q 'level:' cognitive-os.yaml 2>/dev/null; then
      sed -i.bak "s/^\(\s*level:\s*\).*/\1${cap_level}/" cognitive-os.yaml
      rm -f cognitive-os.yaml.bak
    fi
  fi

  # Install listed skills
  local in_skills=false
  while IFS= read -r line; do
    if echo "$line" | grep -qE '^\s*skills:'; then
      in_skills=true
      continue
    fi
    if $in_skills; then
      if echo "$line" | grep -qE '^\s*-\s'; then
        local skill
        skill=$(echo "$line" | sed 's/^\s*-\s*//' | tr -d "'\"\r")
        if [ -n "$skill" ]; then
          echo "  Installing skill: $skill"
          _install_skill "$skill" 2>/dev/null || echo "    (not found — skipping)"
        fi
      else
        in_skills=false
      fi
    fi
  done < "$preset_file"

  echo ""
  echo "Preset '$name' applied."
}

_list_presets() {
  local seen_presets=""
  for dir in "presets" ".cognitive-os/presets" "$PACKAGE_DIR/presets"; do
    if [ -d "$dir" ]; then
      local abs_dir
      abs_dir=$(cd "$dir" 2>/dev/null && pwd) || continue
      if echo "$seen_presets" | grep -qF "$abs_dir"; then continue; fi
      seen_presets="$seen_presets $abs_dir"

      find "$dir" -name '*.yaml' -o -name '*.yml' 2>/dev/null | while read -r f; do
        local pname
        pname=$(basename "$f" | sed -E 's/\.ya?ml$//')
        local pdesc
        pdesc=$(grep -E '^\s*description:' "$f" 2>/dev/null | head -1 | sed 's/.*description:\s*//' | tr -d "'\"\r")
        echo "  $pname — $pdesc"
      done
    fi
  done
}

_install_mcp_server() {
  local name="$1"

  echo "Searching MCP Registry for '$name'..."

  # URL-encode the name for the search param
  local encoded_name
  encoded_name=$(printf '%s' "$name" | jq -sRr @uri 2>/dev/null || printf '%s' "$name")

  local response
  response=$(curl -s --max-time 5 "https://registry.modelcontextprotocol.io/v0.1/servers?search=${encoded_name}&limit=5" 2>/dev/null) || true

  if ! echo "$response" | jq -e '.servers | length > 0' >/dev/null 2>&1; then
    echo "MCP server '$name' not found in the registry." >&2
    echo "Browse available servers at: https://registry.modelcontextprotocol.io" >&2
    return 1
  fi

  # Display matches and their details
  local match_count
  match_count=$(echo "$response" | jq -r '.servers | length' 2>/dev/null)
  echo "Found $match_count result(s):"
  echo ""

  echo "$response" | jq -r '.servers[] |
    "  Name: \(.server.name)\n" +
    "  Description: \(.server.description // "No description" | .[0:120])\n" +
    "  Version: \(.server.version // "unknown")\n" +
    (if .server.repository.url then "  Repository: \(.server.repository.url)\n" else "" end) +
    (if .server.remotes then "  Remote URL: \(.server.remotes[0].url // "N/A")\n" else "" end) +
    ""' 2>/dev/null

  # Try to get install info from the first match
  local server_name
  server_name=$(echo "$response" | jq -r '.servers[0].server.name' 2>/dev/null)
  local repo_url
  repo_url=$(echo "$response" | jq -r '.servers[0].server.repository.url // empty' 2>/dev/null)
  local remote_url
  remote_url=$(echo "$response" | jq -r '.servers[0].server.remotes[0].url // empty' 2>/dev/null)
  local remote_type
  remote_type=$(echo "$response" | jq -r '.servers[0].server.remotes[0].type // empty' 2>/dev/null)

  echo "--- Install Instructions ---"
  echo ""

  if [ -n "$remote_url" ]; then
    echo "Add this MCP server to $(active_settings_driver_label) under mcpServers:"
    echo ""
    # Generate a safe key name from the server name
    local key_name
    key_name=$(echo "$server_name" | sed 's|[/.]|-|g')
    if [ "$remote_type" = "streamable-http" ] || [ "$remote_type" = "sse" ]; then
      echo "  \"$key_name\": {"
      echo "    \"type\": \"${remote_type}\","
      echo "    \"url\": \"${remote_url}\""
      echo "  }"
    else
      echo "  \"$key_name\": {"
      echo "    \"url\": \"${remote_url}\""
      echo "  }"
    fi
    echo ""
  fi

  if [ -n "$repo_url" ]; then
    echo "Source repository: $repo_url"
    echo "Check the repository README for detailed installation instructions."
  fi

  echo ""
  echo "Full details: https://registry.modelcontextprotocol.io"
}

# ── Command: uninstall ─────────────────────────────────────────────────

cmd_uninstall() {
  local comp_type="${1:-}"
  local comp_name="${2:-}"
  local targets=()

  if [ -z "$comp_type" ] || [ -z "$comp_name" ]; then
    echo "Usage: cognitive-os uninstall <type> <name>" >&2
    echo "Types: skill, rule, hook, preset, mcp-server" >&2
    exit 1
  fi

  require_config

  case "$comp_type" in
    skill)
      targets+=("$(canonical_skills_dir)/${comp_name}")
      targets+=("$(driver_skills_dir)/${comp_name}")
      if [ ! -d "${targets[0]}" ] && [ ! -d "${targets[1]}" ]; then
        echo "Skill '$comp_name' is not installed." >&2
        return 1
      fi
      ;;
    rule)
      local filename="${comp_name}"
      [[ "$filename" != *.md ]] && filename="${filename}.md"
      targets+=("$(canonical_rules_dir)/${filename}")
      targets+=("$(driver_rules_dir)/${filename}")
      if [ ! -f "${targets[0]}" ] && [ ! -f "${targets[1]}" ]; then
        echo "Rule '$comp_name' is not installed in canonical or driver rule surfaces." >&2
        return 1
      fi
      ;;
    hook)
      echo "Hooks are managed via $(active_settings_driver_label), not as individual files." >&2
      echo "Use scripts/apply-efficiency-profile.sh to configure hook sets." >&2
      return 1
      ;;
    mcp-server)
      echo "MCP server uninstallation not yet implemented." >&2
      echo "Remove the server entry manually from $(active_settings_driver_label)" >&2
      return 1
      ;;
    preset)
      echo "Presets configure the system — they cannot be 'uninstalled'." >&2
      echo "Apply a different preset to change configuration: cognitive-os install preset <name>" >&2
      return 1
      ;;
    *)
      echo "Unknown component type: $comp_type" >&2
      exit 1
      ;;
  esac

  echo "About to remove:"
  for target in "${targets[@]}"; do
    if [ -e "$target" ]; then
      echo "  - $target"
    fi
  done
  read -rp "Confirm? (y/N): " confirm
  if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
    echo "Aborted."
    return
  fi

  for target in "${targets[@]}"; do
    [ -e "$target" ] || continue
    rm -rf "$target"
  done
  echo "Removed $comp_type '$comp_name'."
}

# ── Command: list ──────────────────────────────────────────────────────

cmd_list() {
  local comp_type="${1:-all}"

  require_config

  case "$comp_type" in
    skill|skills)   _list_installed_skills ;;
    rule|rules)     _list_installed_rules ;;
    hook|hooks)     _list_installed_hooks ;;
    preset|presets) _list_available_presets ;;
    all)
      _list_installed_skills
      echo ""
      _list_installed_rules
      echo ""
      _list_installed_hooks
      echo ""
      _list_available_presets
      ;;
    *)
      echo "Unknown type: $comp_type" >&2
      echo "Valid types: skill(s), rule(s), hook(s), preset(s), all" >&2
      exit 1
      ;;
  esac
}

_list_installed_skills() {
  echo "=== Installed Skills ==="

  local skills_driver
  local skills_canonical
  local skills_legacy
  local active_surface=""
  local surface_label="project"

  skills_driver="$(driver_skills_dir)"
  skills_canonical="$(canonical_skills_dir)"
  skills_legacy="$(legacy_builtin_skills_dir)"

  if dir_has_skill_files "$skills_canonical"; then
    active_surface="$skills_canonical"
    surface_label="canonical"
  elif dir_has_skill_files "$skills_driver"; then
    active_surface="$skills_driver"
  elif dir_has_skill_files "$skills_legacy"; then
    active_surface="$skills_legacy"
    surface_label="legacy"
  fi

  if [ -n "$active_surface" ]; then
    local count=0
    while IFS= read -r skill_file; do
      local skill_name
      skill_name=$(basename "$(dirname "$skill_file")")
      printf "  %-30s %s\n" "$skill_name" "(${surface_label}: ${active_surface}/)"
      count=$((count + 1))
    done < <(find -L "$active_surface" -name 'SKILL.md' 2>/dev/null | sort)
    echo "  Total: $count ${surface_label} skill(s)"
  else
    echo "  No project skills installed (${skills_driver}/ not found, canonical fallback empty)"
  fi

  if [ -d "$skills_canonical" ] && [ "$active_surface" != "$skills_canonical" ]; then
    local builtin_count
    builtin_count=$(find -L "$skills_canonical" -name 'SKILL.md' 2>/dev/null | wc -l | tr -d ' ')
    echo "  Canonical: $builtin_count skill(s) in ${skills_canonical}/"
  elif [ -d "$skills_legacy" ] && [ "$active_surface" != "$skills_legacy" ]; then
    local builtin_count
    builtin_count=$(find -L "$skills_legacy" -name 'SKILL.md' 2>/dev/null | wc -l | tr -d ' ')
    echo "  Built-in: $builtin_count skill(s) in ${skills_legacy}/"
  fi
}

_list_installed_rules() {
  echo "=== Installed Rules ==="

  local rules_driver
  local rules_canonical
  local rules_legacy
  local active_surface=""
  local surface_label="project"

  rules_driver="$(driver_rules_dir)"
  rules_canonical="$(canonical_rules_dir)"
  rules_legacy="$(legacy_builtin_rules_dir)"

  if dir_has_rule_files "$rules_canonical"; then
    active_surface="$rules_canonical"
    surface_label="canonical"
  elif dir_has_rule_files "$rules_driver"; then
    active_surface="$rules_driver"
  elif dir_has_rule_files "$rules_legacy"; then
    active_surface="$rules_legacy"
    surface_label="legacy"
  fi

  if [ -n "$active_surface" ]; then
    local count=0
    while IFS= read -r rule_file; do
      local rule_name
      rule_name=$(basename "$rule_file" .md)
      printf "  %-30s %s\n" "$rule_name" "(${surface_label}: ${active_surface}/)"
      count=$((count + 1))
    done < <(find "$active_surface" -name '*.md' 2>/dev/null | sort)
    echo "  Total: $count ${surface_label} rule(s)"
  else
    echo "  No project rules installed (${rules_driver}/ not found, canonical fallback empty)"
  fi

  if [ -d "$rules_canonical" ] && [ "$active_surface" != "$rules_canonical" ]; then
    local builtin_count
    builtin_count=$(find "$rules_canonical" -name '*.md' 2>/dev/null | wc -l | tr -d ' ')
    echo "  Canonical: $builtin_count rule(s) in ${rules_canonical}/"
  elif [ -d "$rules_legacy" ] && [ "$active_surface" != "$rules_legacy" ]; then
    local builtin_count
    builtin_count=$(find "$rules_legacy" -name '*.md' 2>/dev/null | wc -l | tr -d ' ')
    echo "  Built-in: $builtin_count rule(s) in ${rules_legacy}/"
  elif [ -d "rules" ]; then
    local builtin_count
    builtin_count=$(find rules -name '*.md' 2>/dev/null | wc -l | tr -d ' ')
    echo "  Built-in: $builtin_count rule(s) in rules/"
  fi
}

_list_installed_hooks() {
  echo "=== Installed Hooks ==="

  local settings_driver_label
  local settings_driver_path
  settings_driver_label="$(active_settings_driver_label)"
  settings_driver_path="$(active_settings_driver_path)"

  if [ -d ".cognitive-os/hooks" ]; then
    local count
    count=$(find .cognitive-os/hooks -name '*.sh' -not -path '*/_lib/*' 2>/dev/null | wc -l | tr -d ' ')
    echo "  Available: $count hook(s) in .cognitive-os/hooks/"

    # Show which are registered
    if [ -f "$settings_driver_path" ]; then
      local registered
      registered=$(grep -c '"command"' "$settings_driver_path" 2>/dev/null || echo "0")
      echo "  Registered: $registered hook command(s) in $settings_driver_label"
    else
      echo "  No $settings_driver_label — hooks not registered"
    fi
  else
    echo "  No hooks directory found"
  fi
}

_list_available_presets() {
  echo "=== Available Presets ==="

  local found=false
  local seen_presets=""

  for dir in "presets" ".cognitive-os/presets" "$PACKAGE_DIR/presets"; do
    if [ -d "$dir" ]; then
      # Resolve to absolute path to deduplicate
      local abs_dir
      abs_dir=$(cd "$dir" 2>/dev/null && pwd) || continue
      if echo "$seen_presets" | grep -qF "$abs_dir"; then
        continue
      fi
      seen_presets="$seen_presets $abs_dir"

      while IFS= read -r f; do
        found=true
        local pname
        pname=$(basename "$f" | sed -E 's/\.ya?ml$//')
        local pdesc
        pdesc=$(grep -E '^\s*description:' "$f" 2>/dev/null | head -1 | sed 's/.*description:\s*//' | tr -d "'\"\r")
        printf "  %-16s %s\n" "$pname" "$pdesc"
      done < <(find "$dir" -name '*.yaml' -o -name '*.yml' 2>/dev/null | sort)
    fi
  done

  if ! $found; then
    echo "  No presets found"
  fi
}

# ── Command: update ────────────────────────────────────────────────────

cmd_update() {
  require_config

  echo "=== Updating Source Indexes ==="
  echo ""

  _parse_registries

  local i
  for ((i = 0; i < _REG_COUNT; i++)); do
    _update_source "${_REG_NAMES[$i]}" "${_REG_TYPES[$i]}" "${_REG_URLS[$i]}" "${_REG_ENABLED[$i]}"
  done

  echo ""
  echo "Done."
}

_update_source() {
  local name="$1" type="$2" url="$3" enabled="$4"

  if [ "$enabled" = "false" ]; then
    echo "  [$name] skipped (disabled)"
    return
  fi

  if [ "$type" = "local" ]; then
    echo "  [$name] local source — no update needed"
  elif [ "$type" = "remote" ]; then
    # Verify remote sources are reachable
    if echo "$url" | grep -qi 'skild\.\|skills\.sh'; then
      if curl -s --max-time 5 "https://registry.skild.sh/discover?q=test&limit=1" | jq -e '.ok == true' >/dev/null 2>&1; then
        echo "  [$name] Skills.sh registry — reachable (OK)"
      else
        echo "  [$name] Skills.sh registry — not reachable (check connection)"
      fi
    elif echo "$url" | grep -qi 'modelcontextprotocol\|mcp.*registry'; then
      if curl -s --max-time 5 "https://registry.modelcontextprotocol.io/v0.1/ping" | jq -e '.' >/dev/null 2>&1; then
        echo "  [$name] MCP Registry — reachable (OK)"
      else
        echo "  [$name] MCP Registry — not reachable (check connection)"
      fi
    else
      echo "  [$name] remote source — connectivity check not available ($url)"
    fi
  fi
}

# ── Main ───────────────────────────────────────────────────────────────

case "${1:-help}" in
  init)      cmd_init "${2:-.}" ;;
  version)   cmd_version ;;
  doctor)    shift; cmd_doctor "$@" ;;
  sources)   shift; cmd_sources "$@" ;;
  search)    shift; cmd_search "$@" ;;
  install)   shift; cmd_install "$@" ;;
  uninstall) shift; cmd_uninstall "$@" ;;
  list)      shift; cmd_list "$@" ;;
  update)    cmd_update ;;
  help)      usage ;;
  *)         echo "Unknown command: $1"; usage; exit 1 ;;
esac
