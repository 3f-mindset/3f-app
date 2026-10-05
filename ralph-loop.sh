#!/usr/bin/env bash
set -euo pipefail

# Runs one OpenCode session per iteration. Each session follows ralph/PROMPT.md,
# commits its cohesive change, and the next session continues from the worktree.
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Ensure the tools each iteration needs are on PATH. Non-login shells (and the
# shells spawned inside each OpenCode session) do not source the user profile,
# so without this the loop cannot find opencode, uv, or npm.
for tool_dir in "$HOME/.opencode/bin" "$HOME/.cargo/bin" "$HOME/.local/bin"; do
  if [[ -d "$tool_dir" ]]; then
    PATH="$tool_dir:$PATH"
  fi
done
if ! command -v npm >/dev/null 2>&1 && [[ -d "$HOME/.nvm/versions/node" ]]; then
  nvm_node_bin="$(ls -d "$HOME"/.nvm/versions/node/*/bin 2>/dev/null | sort -V | tail -n 1)"
  if [[ -n "$nvm_node_bin" ]]; then
    PATH="$nvm_node_bin:$PATH"
  fi
fi
export PATH

MAX_ITERATIONS="${RALPH_MAX_ITERATIONS:-12}"
MODEL="${RALPH_MODEL:-}"
AGENT="${RALPH_AGENT:-}"
AUTO_APPROVE="${RALPH_AUTO_APPROVE:-0}"
RUN_DIR="$ROOT/ralph/runs"

mkdir -p "$RUN_DIR"

# Disable opencode snapshots for harness runs. A snapshot embeds a full git diff
# of every changed file in each message.updated event; a cycle that touches
# node_modules or thousands of files writes multi-MB events and bloats the
# session database. See the ralph skill / global AGENTS.md.
RALPH_OPENCODE_CONFIG="${RALPH_OPENCODE_CONFIG:-$HOME/.config/opencode/ralph-harness.json}"
if [[ ! -f "$RALPH_OPENCODE_CONFIG" ]]; then
  mkdir -p "$(dirname "$RALPH_OPENCODE_CONFIG")"
  printf '{"$schema":"https://opencode.ai/config.json","snapshot":false}\n' > "$RALPH_OPENCODE_CONFIG"
fi
export OPENCODE_CONFIG="$RALPH_OPENCODE_CONFIG"

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

  # Always push the session's commits to origin so work is never left local.
  if git -C "$ROOT" remote get-url origin >/dev/null 2>&1; then
    printf 'Pushing %s to origin.\n' "$(git -C "$ROOT" rev-parse --abbrev-ref HEAD)"
    git -C "$ROOT" push origin HEAD || printf 'warning: git push to origin failed; continuing.\n' >&2
  else
    printf 'warning: no origin remote configured; skipping push.\n' >&2
  fi

  if grep -qE '^[[:space:]]*RALPH_COMPLETE[[:space:]]*$' "$log_file"; then
    printf 'Ralph reports the prioritized backlog is complete.\n'
    exit 0
  fi
  if grep -qE '^[[:space:]]*RALPH_BLOCKED:' "$log_file"; then
    printf 'Ralph reported a blocker. See %s\n' "$log_file" >&2
    exit 2
  fi
  if ! grep -qE '^\- \[ \] \*\*P' "$ROOT/TODO.md"; then
    printf 'No unchecked TODO items remain.\n'
    exit 0
  fi
done

printf 'Iteration limit reached. Review %s and TODO.md before running again.\n' "$RUN_DIR" >&2
exit 3
