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
OUT="${1:-$ROOT/outputs/dry_run_multiturn_base}"

"$PYTHON_BIN" "$ROOT/src/run_discovery.py" \
  --category multi_turn_base \
  --bfcl-root "$BFCL_ROOT" \
  --graphs-path "$GRAPHS_PATH" \
  --episode-filter intra_turn_parallel \
  --output-dir "$OUT" \
  --max-episodes 1 \
  --allow-gold-replay-errors \
  --dry-run
