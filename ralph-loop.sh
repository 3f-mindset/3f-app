#!/usr/bin/env bash
set -euo pipefail

# Runs one OpenCode session per iteration. Each session follows ralph/PROMPT.md,
# commits its cohesive change, and the next session continues from the worktree.
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MAX_ITERATIONS="${RALPH_MAX_ITERATIONS:-12}"
MODEL="${RALPH_MODEL:-}"
AGENT="${RALPH_AGENT:-}"
AUTO_APPROVE="${RALPH_AUTO_APPROVE:-0}"
RUN_DIR="$ROOT/ralph/runs"

mkdir -p "$RUN_DIR"

if ! command -v opencode >/dev/null 2>&1; then
  printf 'opencode CLI is required but was not found on PATH.\n' >&2
  exit 1
fi

if [[ "$AUTO_APPROVE" != "0" && "$AUTO_APPROVE" != "1" ]]; then
  printf 'RALPH_AUTO_APPROVE must be 0 or 1.\n' >&2
  exit 1
fi

for ((iteration = 1; iteration <= MAX_ITERATIONS; iteration++)); do
  timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
  log_file="$RUN_DIR/${timestamp}-iteration-${iteration}.log"
  prompt="$(cat "$ROOT/ralph/PROMPT.md")

This is Ralph iteration ${iteration} of ${MAX_ITERATIONS}. Work in ${ROOT}. Begin now."
  command=(opencode run --dir "$ROOT" --title "3F Ralph iteration ${iteration}")

  if [[ -n "$MODEL" ]]; then command+=(--model "$MODEL"); fi
  if [[ -n "$AGENT" ]]; then command+=(--agent "$AGENT"); fi
  if [[ "$AUTO_APPROVE" == "1" ]]; then command+=(--auto); fi

  printf 'Starting Ralph iteration %s/%s. Log: %s\n' "$iteration" "$MAX_ITERATIONS" "$log_file"
  "${command[@]}" "$prompt" 2>&1 | tee "$log_file"

  if grep -q "RALPH_COMPLETE" "$log_file"; then
    printf 'Ralph reports the prioritized backlog is complete.\n'
    exit 0
  fi
  if grep -q "RALPH_BLOCKED:" "$log_file"; then
    printf 'Ralph reported a blocker. See %s\n' "$log_file" >&2
    exit 2
  fi
  if ! grep -qE '^\- \[ \] \*\*P[01]' "$ROOT/TODO.md"; then
    printf 'No unchecked P0/P1 TODO items remain.\n'
    exit 0
  fi
done

printf 'Iteration limit reached. Review %s and TODO.md before running again.\n' "$RUN_DIR" >&2
exit 3
