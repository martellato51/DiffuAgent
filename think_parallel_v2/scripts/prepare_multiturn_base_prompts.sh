#!/usr/bin/env bash
set -euo pipefail

ROOT="/home/ilju/research/DiffuAgent/think_parallel_v2"
ENV_FILE="${ENV_FILE:-/home/ilju/research/DiffuAgent/env.sh}"
if [[ -f "$ENV_FILE" ]]; then
  source "$ENV_FILE"
fi

PYTHON_BIN="${PYTHON_BIN:-${LLADA_PYTHON:-/home/ilju/miniconda3/envs/llada8b/bin/python}}"
BFCL_ROOT="${BFCL_ROOT:-/home/ilju/research/DiffuAgent/unified_envs/gorilla_bfcl_v3/berkeley-function-call-leaderboard}"
GRAPHS_PATH="${GRAPHS_PATH:-/home/ilju/research/ParallelAgent/data/annotations/bfcl_v3_think_parallel_multi_turn_base_graphs.jsonl}"
MODE="${MODE:-llmcompiler_explicit_dag}"

case "$MODE" in
  llmcompiler_plan|llmcompiler_explicit_dag)
    DEFAULT_PREPARED_PROMPTS="$ROOT/prepared/multi_turn_base_intra_turn_parallel_explicit_prompts.jsonl"
    ;;
  llmcompiler_flat_plan)
    DEFAULT_PREPARED_PROMPTS="$ROOT/prepared/multi_turn_base_intra_turn_parallel_flat_prompts.jsonl"
    ;;
  *)
    echo "Unsupported MODE: $MODE" >&2
    exit 1
    ;;
esac

PREPARED_PROMPTS="${PREPARED_PROMPTS:-$DEFAULT_PREPARED_PROMPTS}"

"$PYTHON_BIN" "$ROOT/src/prepare_prompts.py" \
  --category multi_turn_base \
  --mode "$MODE" \
  --bfcl-root "$BFCL_ROOT" \
  --graphs-path "$GRAPHS_PATH" \
  --episode-filter intra_turn_parallel \
  --prepared-prompts-path "$PREPARED_PROMPTS"
