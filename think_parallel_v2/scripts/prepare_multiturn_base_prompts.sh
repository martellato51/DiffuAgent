#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="${ROOT:-$(cd "$SCRIPT_DIR/.." && pwd)}"
DIFFUAGENT_ROOT="${DIFFUAGENT_ROOT:-$(cd "$ROOT/.." && pwd)}"
ENV_FILE="${ENV_FILE:-$DIFFUAGENT_ROOT/env.local.sh}"
if [[ -f "$ENV_FILE" ]]; then
  source "$ENV_FILE"
fi
RESEARCH_ROOT="${RESEARCH_ROOT:-$(cd "$DIFFUAGENT_ROOT/.." && pwd)}"

PYTHON_BIN="${PYTHON_BIN:-${LLADA_PYTHON:-python}}"
BFCL_ROOT="${BFCL_ROOT:-$DIFFUAGENT_ROOT/unified_envs/gorilla_bfcl_v3/berkeley-function-call-leaderboard}"
GRAPHS_PATH="${GRAPHS_PATH:-$RESEARCH_ROOT/ParallelAgent/data/annotations/bfcl_v3_think_parallel_multi_turn_base_graphs.jsonl}"
MODE="${MODE:-llmcompiler_explicit_dag}"
STATE_VIEW="${STATE_VIEW:-tree}"
STATE_VIEW_INCLUDE_FILE_CONTENT="${STATE_VIEW_INCLUDE_FILE_CONTENT:-0}"

case "$MODE" in
  llmcompiler_plan|llmcompiler_explicit_dag)
    DEFAULT_PREPARED_PROMPTS="$ROOT/prepared/multi_turn_base_intra_turn_parallel_explicit_state_${STATE_VIEW}_prompts.jsonl"
    ;;
  llmcompiler_flat_plan)
    DEFAULT_PREPARED_PROMPTS="$ROOT/prepared/multi_turn_base_intra_turn_parallel_flat_state_${STATE_VIEW}_prompts.jsonl"
    ;;
  *)
    echo "Unsupported MODE: $MODE" >&2
    exit 1
    ;;
esac

PREPARED_PROMPTS="${PREPARED_PROMPTS:-$DEFAULT_PREPARED_PROMPTS}"

STATE_VIEW_ARGS=(--state-view "$STATE_VIEW")
if [[ "$STATE_VIEW_INCLUDE_FILE_CONTENT" == "1" ]]; then
  STATE_VIEW_ARGS+=(--state-view-include-file-content)
fi

"$PYTHON_BIN" "$ROOT/src/prepare_prompts.py" \
  --category multi_turn_base \
  --mode "$MODE" \
  --bfcl-root "$BFCL_ROOT" \
  --graphs-path "$GRAPHS_PATH" \
  --episode-filter intra_turn_parallel \
  --prepared-prompts-path "$PREPARED_PROMPTS" \
  "${STATE_VIEW_ARGS[@]}"
