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
RUN_STAMP="${RUN_STAMP:-$(date +%y%m%d_%H%M%S)}"
STATE_VIEW="${STATE_VIEW:-tree}"
OUT="${1:-$ROOT/outputs/dry_run_multiturn_base_$RUN_STAMP}"

"$PYTHON_BIN" "$ROOT/src/run_discovery.py" \
  --category multi_turn_base \
  --bfcl-root "$BFCL_ROOT" \
  --graphs-path "$GRAPHS_PATH" \
  --episode-filter intra_turn_parallel \
  --state-view "$STATE_VIEW" \
  --output-dir "$OUT" \
  --max-episodes 1 \
  --allow-gold-replay-errors \
  --dry-run
