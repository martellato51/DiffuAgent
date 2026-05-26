#!/usr/bin/env bash
set -euo pipefail

ROOT="/home/ilju/research/DiffuAgent/think_parallel_v2"
ENV_FILE="${ENV_FILE:-/home/ilju/research/DiffuAgent/env.sh}"
if [[ -f "$ENV_FILE" ]]; then
  source "$ENV_FILE"
fi

PYTHON_BIN="${PYTHON_BIN:-${LLADA_PYTHON:-/home/ilju/miniconda3/envs/llada8b/bin/python}}"
MODE="${MODE:-llmcompiler_explicit_dag}"
RUN_STAMP="${RUN_STAMP:-$(date +%y%m%d_%H%M%S)}"
STATE_VIEW="${STATE_VIEW:-tree}"

case "$MODE" in
  llmcompiler_plan|llmcompiler_explicit_dag)
    DEFAULT_PREPARED_PROMPTS="$ROOT/prepared/multi_turn_base_intra_turn_parallel_explicit_state_${STATE_VIEW}_prompts.jsonl"
    DEFAULT_OUT="$ROOT/outputs/llada_multiturn_base_explicit_state_${STATE_VIEW}_$RUN_STAMP"
    ;;
  llmcompiler_flat_plan)
    DEFAULT_PREPARED_PROMPTS="$ROOT/prepared/multi_turn_base_intra_turn_parallel_flat_state_${STATE_VIEW}_prompts.jsonl"
    DEFAULT_OUT="$ROOT/outputs/llada_multiturn_base_flat_state_${STATE_VIEW}_$RUN_STAMP"
    ;;
  *)
    echo "Unsupported MODE: $MODE" >&2
    exit 1
    ;;
esac

PREPARED_PROMPTS="${PREPARED_PROMPTS:-$DEFAULT_PREPARED_PROMPTS}"
OUT="${1:-$DEFAULT_OUT}"

export LLADA_GEN_LENGTH="${LLADA_GEN_LENGTH:-128}"
export LLADA_STEPS="${LLADA_STEPS:-128}"
export LLADA_BLOCK_LENGTH="${LLADA_BLOCK_LENGTH:-32}"

if [[ ! -f "$PREPARED_PROMPTS" ]]; then
  echo "Prepared prompts not found: $PREPARED_PROMPTS" >&2
  echo "Run: bash $ROOT/scripts/prepare_multiturn_base_prompts.sh" >&2
  exit 1
fi

if [[ "${LLADA_MODEL_PATH:-}" = /* && ! -d "$LLADA_MODEL_PATH" ]]; then
  echo "LLADA_MODEL_PATH does not exist: $LLADA_MODEL_PATH" >&2
  echo "Set LLADA_MODEL_PATH or update $ENV_FILE." >&2
  exit 1
fi

"$PYTHON_BIN" "$ROOT/src/run_discovery.py" \
  --category multi_turn_base \
  --mode "$MODE" \
  --prepared-prompts-path "$PREPARED_PROMPTS" \
  --output-dir "$OUT"
