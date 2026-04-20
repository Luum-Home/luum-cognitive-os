#!/usr/bin/env bash
# SCOPE: both
# Symlink-aware file existence checker.
# Use this instead of raw [ -f ] to avoid false "missing" reports on symlinks.
#
# Usage:
#   source "$(dirname "$0")/_lib/file_checker.sh"
#   if file_exists "hooks/my-hook.sh"; then echo "exists"; fi
#   if file_exists_strict "hooks/my-hook.sh"; then echo "exists and target valid"; fi

# Check if a file exists, including symlinks (even if target is missing).
# Returns 0 if the path exists as a regular file OR as a symlink.
file_exists() {
    [ -f "$1" ] || [ -L "$1" ]
}

# Check if a file exists AND if it's a symlink, the target also exists.
# Returns 0 only if the final resolved path is a real file.
file_exists_strict() {
    if [ -L "$1" ]; then
        local target
        target=$(readlink -f "$1" 2>/dev/null) || return 1
        [ -f "$target" ]
    else
        [ -f "$1" ]
    fi
}

# Resolve a path through symlinks to its canonical location.
# Returns the resolved path on stdout, or the original path if resolution fails.
resolve_path() {
    readlink -f "$1" 2>/dev/null || echo "$1"
}

# Check if a path is a symlink with a broken target.
# Returns 0 if the path is a symlink AND the target does NOT exist.
is_broken_symlink() {
    [ -L "$1" ] && ! [ -e "$1" ]
}
