#!/usr/bin/env bash
# merge-settings.sh — Merge Cognitive OS hooks into an existing .claude/settings.json
#
# Usage: bash merge-settings.sh <existing_settings.json> <cos_hooks.json> [output_file]
#
# If output_file is omitted, writes to stdout.
#
# Rules:
#   - Never removes existing hooks (project hooks preserved)
#   - Adds COS hooks that don't already exist (dedup by command string)
#   - COS hooks are identifiable by containing "hooks/" in the command path
#   - Idempotent: running twice produces the same result
#   - Preserves all existing settings keys (permissions, env, etc.)
#
# Requires: jq
set -euo pipefail

if ! command -v jq >/dev/null 2>&1; then
  echo "Error: jq is required for settings merge." >&2
  exit 1
fi

EXISTING="${1:-}"
COS_HOOKS="${2:-}"
OUTPUT="${3:-/dev/stdout}"

if [ -z "$EXISTING" ] || [ -z "$COS_HOOKS" ]; then
  echo "Usage: merge-settings.sh <existing_settings.json> <cos_hooks.json> [output_file]" >&2
  exit 1
fi

if [ ! -f "$EXISTING" ]; then
  echo "Error: existing settings file not found: $EXISTING" >&2
  exit 1
fi

if [ ! -f "$COS_HOOKS" ]; then
  echo "Error: COS hooks file not found: $COS_HOOKS" >&2
  exit 1
fi

# Validate both are valid JSON
jq empty "$EXISTING" 2>/dev/null || { echo "Error: invalid JSON in $EXISTING" >&2; exit 1; }
jq empty "$COS_HOOKS" 2>/dev/null || { echo "Error: invalid JSON in $COS_HOOKS" >&2; exit 1; }

# The merge strategy:
# For each lifecycle event (SessionStart, PreToolUse, PostToolUse, Stop):
#   For each matcher group in COS_HOOKS:
#     Find the matching group in EXISTING (same lifecycle + matcher)
#     If found: merge hooks arrays (dedup by command string)
#     If not found: append the entire matcher group
#
# All non-hooks keys in EXISTING are preserved untouched.

jq -s '
  # $existing = .[0], $cos = .[1]
  .[0] as $existing | .[1] as $cos |

  # Start with existing settings
  $existing |

  # Ensure .hooks exists
  .hooks //= {} |

  # For each lifecycle event in COS hooks
  reduce ($cos.hooks | to_entries[]) as $event (
    .;
    $event.key as $lifecycle |
    $event.value as $cos_groups |

    # Ensure the lifecycle array exists in result
    .hooks[$lifecycle] //= [] |

    # For each matcher group in COS
    reduce ($cos_groups[]) as $cos_group (
      .;
      $cos_group.matcher as $matcher |
      $cos_group.hooks as $cos_hook_list |

      # Find index of matching group in existing
      (.hooks[$lifecycle] | map(.matcher) | index($matcher)) as $idx |

      if $idx != null then
        # Group exists — merge hooks (dedup by command)
        .hooks[$lifecycle][$idx].hooks as $existing_hooks |
        ($existing_hooks | map(.command)) as $existing_cmds |
        reduce ($cos_hook_list[]) as $h (
          .;
          if ($existing_cmds | index($h.command)) != null then
            .  # already exists, skip
          else
            .hooks[$lifecycle][$idx].hooks += [$h]
          end
        )
      else
        # Group does not exist — append entire group
        .hooks[$lifecycle] += [$cos_group]
      end
    )
  )
' "$EXISTING" "$COS_HOOKS" > "$OUTPUT"
