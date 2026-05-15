#!/usr/bin/env bash
# SCOPE: os-only
# portable.sh — Cross-platform shell helpers for macOS (BSD userland, bash 3.2)
#               and Linux (GNU userland, bash 4+) and WSL.
#
# Source this file in any hook or script that needs portable date/sed/stat/array ops:
#   source "$(dirname "${BASH_SOURCE[0]}")/_lib/portable.sh"
#   (or adjust the relative path as needed)
#
# Provides:
#   portable_date_minus DAYS [BASE_EPOCH]  — echo epoch N days before BASE_EPOCH (default: now)
#   portable_sed_inplace EXPR FILE         — in-place sed substitution
#   portable_stat_mtime FILE               — mtime of FILE as Unix epoch seconds
#   portable_stat_size FILE                — size of FILE in bytes
#   portable_readlines FILE VAR_NAME       — read FILE into array named VAR_NAME (bash 3.2 compat)
#   portable_epoch_now                     — echo current Unix epoch seconds
#
# Detection strategy: feature-test rather than uname, for robustness.
#   - date -v: BSD (macOS) only
#   - stat -f: BSD (macOS) stat; stat -c: GNU stat
#   - sed -i '': BSD sed; sed -i: GNU sed
#
# bash 3.2 compatible — no mapfile, no readarray, no associative arrays.

# ── Guard against double-sourcing ────────────────────────────────────────────
[ "${_PORTABLE_SH_LOADED:-}" = "true" ] && return 0
_PORTABLE_SH_LOADED="true"

# ── Platform detection (feature-test, evaluated once at source time) ─────────

# Detect BSD vs GNU date
# BSD date supports -v (date adjustment); GNU date does not.
if date -v 1970-01-01 >/dev/null 2>&1; then
  _PORTABLE_DATE_BSD=true
else
  _PORTABLE_DATE_BSD=false
fi

# Detect BSD vs GNU sed
# BSD sed requires 'sed -i ""'; GNU sed requires 'sed -i' (empty string is an error).
# We use a temp-file test rather than a no-op on a real file.
_PORTABLE_SED_TYPE="python"  # default: use python3 (universally available) as fallback
if _tmpf="$(mktemp 2>/dev/null)" && [ -f "$_tmpf" ]; then
  echo "test" > "$_tmpf"
  if sed -i '' 's/test/ok/' "$_tmpf" 2>/dev/null && [ "$(cat "$_tmpf")" = "ok" ]; then
    _PORTABLE_SED_TYPE="bsd"
  elif sed -i 's/ok/test/' "$_tmpf" 2>/dev/null && [ "$(cat "$_tmpf")" = "test" ]; then
    _PORTABLE_SED_TYPE="gnu"
  fi
  rm -f "$_tmpf"
fi

# Detect BSD vs GNU stat
# BSD stat: stat -f %m (mtime), stat -f %z (size)
# GNU stat: stat -c %Y (mtime), stat -c %s (size)
_PORTABLE_STAT_TYPE="python"  # default fallback
if stat -f %m / >/dev/null 2>&1; then
  _PORTABLE_STAT_TYPE="bsd"
elif stat -c %Y / >/dev/null 2>&1; then
  _PORTABLE_STAT_TYPE="gnu"
fi

# ── portable_epoch_now ───────────────────────────────────────────────────────
# date +%s is POSIX and works on both BSD and GNU.
portable_epoch_now() {
  date +%s
}

# ── portable_date_minus DAYS [BASE_EPOCH] ────────────────────────────────────
# Echo Unix epoch seconds N days before BASE_EPOCH (defaults to current time).
# DAYS must be a non-negative integer.
#
# Usage:
#   cutoff=$(portable_date_minus 1)        # yesterday (epoch)
#   cutoff=$(portable_date_minus 24)       # 24 days ago (epoch)
#   cutoff=$(portable_date_minus 1 1700000000)  # 1 day before the given epoch
#
# Replaces: date -v-${N}d +%s (BSD) / date -d "-${N} days" +%s (GNU)
portable_date_minus() {
  local days="$1"
  local base_epoch="${2:-}"

  # Default base to current time
  if [ -z "$base_epoch" ]; then
    base_epoch=$(date +%s)
  fi

  # Python3 is the most portable way to do epoch arithmetic reliably across
  # time zones, DST, etc. Python3 is guaranteed available (per task constraints).
  python3 -c "import sys; print(int(sys.argv[1]) - int(sys.argv[2]) * 86400)" \
    "$base_epoch" "$days"
}

# ── portable_sed_inplace EXPR FILE ──────────────────────────────────────────
# Apply sed expression EXPR to FILE in-place.
#
# Usage:
#   portable_sed_inplace "s/foo/bar/" /path/to/file
#   portable_sed_inplace "/MARKER BEGIN/,/MARKER END/d" /path/to/file
#
# Replaces: sed -i '' (BSD) / sed -i (GNU)
portable_sed_inplace() {
  local expr="$1"
  local file="$2"

  case "$_PORTABLE_SED_TYPE" in
    bsd)
      sed -i '' "$expr" "$file"
      ;;
    gnu)
      sed -i "$expr" "$file"
      ;;
    *)
      # Python3 fallback: read, transform with re or str, write back atomically.
      # Only handles simple substitution patterns via python's re module.
      # For complex range deletions we use a line-by-line approach.
      python3 - "$expr" "$file" <<'PYEOF'
import sys, re, os, tempfile

expr = sys.argv[1]
path = sys.argv[2]

with open(path, 'r', errors='replace') as f:
    lines = f.readlines()

# Parse sed expression types we need to support:
#  s/pattern/replacement/[flags]   — substitution
#  /start/,/end/d                  — range deletion
#  /pattern/d                      — single-line deletion

result = []

# Range deletion: /START/,/END/d
m = re.match(r'^/(.*)/,/(.*)$/d$', expr)
if m:
    start_pat = re.compile(m.group(1))
    end_pat = re.compile(m.group(2))
    in_range = False
    for line in lines:
        if not in_range and start_pat.search(line):
            in_range = True
            continue
        if in_range:
            if end_pat.search(line):
                in_range = False
            continue
        result.append(line)
else:
    # Substitution: s/pat/repl/[g]
    m2 = re.match(r'^s(.)(.+)\1(.*)\1([gGiI]*)$', expr)
    if m2:
        sep, pat, repl, flags = m2.group(1), m2.group(2), m2.group(3), m2.group(4)
        re_flags = 0
        if 'i' in flags.lower():
            re_flags |= re.IGNORECASE
        count = 0 if 'g' in flags else 1
        for line in lines:
            result.append(re.sub(pat, repl, line, count=count, flags=re_flags))
    else:
        # Single-line deletion: /pattern/d
        m3 = re.match(r'^/(.+)/d$', expr)
        if m3:
            pat = re.compile(m3.group(1))
            for line in lines:
                if not pat.search(line):
                    result.append(line)
        else:
            # Unknown expression — write back unchanged to avoid data loss
            result = lines

# Atomic write
tmp = path + '.portable_sed_tmp'
with open(tmp, 'w', errors='replace') as f:
    f.writelines(result)
os.replace(tmp, path)
PYEOF
      ;;
  esac
}

# ── portable_stat_mtime FILE ─────────────────────────────────────────────────
# Echo the modification time of FILE as Unix epoch seconds.
#
# Usage:
#   mtime=$(portable_stat_mtime /path/to/file)
#
# Replaces: stat -f %m (BSD) / stat -c %Y (GNU)
portable_stat_mtime() {
  local file="$1"
  case "$_PORTABLE_STAT_TYPE" in
    bsd)
      stat -f %m "$file"
      ;;
    gnu)
      stat -c %Y "$file"
      ;;
    *)
      # Python3 fallback
      python3 -c "import os, sys; print(int(os.path.getmtime(sys.argv[1])))" "$file"
      ;;
  esac
}

# ── portable_stat_size FILE ──────────────────────────────────────────────────
# Echo the size of FILE in bytes.
#
# Usage:
#   size=$(portable_stat_size /path/to/file)
#
# Replaces: stat -f %z (BSD) / stat -c %s (GNU)
portable_stat_size() {
  local file="$1"

  if [ ! -e "$file" ]; then
    echo "0"
    return 0
  fi

  case "$_PORTABLE_STAT_TYPE" in
    bsd)
      stat -f %z "$file"
      ;;
    gnu)
      stat -c %s "$file"
      ;;
    *)
      # Python3 fallback
      python3 -c "import os, sys; print(os.path.getsize(sys.argv[1]) if os.path.exists(sys.argv[1]) else 0)" "$file"
      ;;
  esac
}

# ── portable_readlines FILE VAR_NAME ─────────────────────────────────────────
# Read all lines from FILE into the array named VAR_NAME.
# bash 3.2 compatible (no mapfile/readarray).
#
# Usage:
#   portable_readlines /path/to/file my_array
#   for item in "${my_array[@]}"; do echo "$item"; done
#
# Replaces: mapfile -t my_array < FILE
#           readarray -t my_array < FILE
#
# IMPORTANT: Sets the array in the CALLER's scope using eval.
#            VAR_NAME must be a valid bash identifier.
portable_readlines() {
  local _prl_file="$1"
  local _prl_varname="$2"
  local _prl_line
  local _prl_idx=0

  # Clear the target array
  eval "${_prl_varname}=()"

  if [ ! -f "$_prl_file" ]; then
    return 0
  fi

  # Read line by line (bash 3.2 compatible, handles empty lines and spaces)
  while IFS= read -r _prl_line || [ -n "$_prl_line" ]; do
    eval "${_prl_varname}[${_prl_idx}]=\$_prl_line"
    _prl_idx=$(( _prl_idx + 1 ))
  done < "$_prl_file"
}
