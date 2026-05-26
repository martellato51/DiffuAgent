#!/usr/bin/env bash
set -euo pipefail

ROOT="${ROOT:-/home/ilju/research/DiffuAgent/think_parallel_v2}"
DIFFUAGENT_ROOT="${DIFFUAGENT_ROOT:-$(cd "$ROOT/.." && pwd)}"
ENV_FILE="${ENV_FILE:-$DIFFUAGENT_ROOT/env.sh}"
if [[ -f "$ENV_FILE" ]]; then
  source "$ENV_FILE"
fi

PYTHON_BIN="${PYTHON_BIN:-${LLADA_PYTHON:-/home/ilju/miniconda3/envs/llada8b/bin/python}}"
CONDITION="${CONDITION:-explicit}"
SMOKE_IDS="${SMOKE_IDS:-multi_turn_base_35,multi_turn_base_39,multi_turn_base_50,multi_turn_base_55,multi_turn_base_56,multi_turn_base_57,multi_turn_base_59,multi_turn_base_62,multi_turn_base_67,multi_turn_base_70,multi_turn_base_71,multi_turn_base_86,multi_turn_base_87,multi_turn_base_88,multi_turn_base_91,multi_turn_base_97,multi_turn_base_143,multi_turn_base_151,multi_turn_base_173,multi_turn_base_185}"
RUN_STAMP="${RUN_STAMP:-$(date +%y%m%d_%H%M%S)}"
STATE_VIEW="${STATE_VIEW:-tree}"

case "$CONDITION" in
  pre_split)
    MODE="llmcompiler_plan"
    PREPARED_PROMPTS="${PREPARED_PROMPTS:-$ROOT/prepared/multi_turn_base_intra_turn_parallel_explicit_state_${STATE_VIEW}_prompts.jsonl}"
    DEFAULT_OUT="$ROOT/outputs/smoke_pre_split_state_${STATE_VIEW}_$RUN_STAMP"
    ;;
  explicit)
    MODE="llmcompiler_explicit_dag"
    PREPARED_PROMPTS="${PREPARED_PROMPTS:-$ROOT/prepared/multi_turn_base_intra_turn_parallel_explicit_state_${STATE_VIEW}_prompts.jsonl}"
    DEFAULT_OUT="$ROOT/outputs/smoke_explicit_state_${STATE_VIEW}_$RUN_STAMP"
    ;;
  flat)
    MODE="llmcompiler_flat_plan"
    PREPARED_PROMPTS="${PREPARED_PROMPTS:-$ROOT/prepared/multi_turn_base_intra_turn_parallel_flat_state_${STATE_VIEW}_prompts.jsonl}"
    DEFAULT_OUT="$ROOT/outputs/smoke_flat_state_${STATE_VIEW}_$RUN_STAMP"
    ;;
  *)
    echo "Unsupported CONDITION: $CONDITION" >&2
    echo "Expected one of: pre_split, explicit, flat" >&2
    exit 1
    ;;
esac

OUT="${OUT:-${OUTPUT_DIR:-$DEFAULT_OUT}}"

if [[ -n "${GPUS:-}" ]]; then
  export CUDA_VISIBLE_DEVICES="$GPUS"
fi

export TOKENIZERS_PARALLELISM="${TOKENIZERS_PARALLELISM:-false}"
export PYTHONUNBUFFERED="${PYTHONUNBUFFERED:-1}"
export PYTORCH_CUDA_ALLOC_CONF="${PYTORCH_CUDA_ALLOC_CONF:-expandable_segments:True}"
export LLADA_TEMPERATURE="${LLADA_TEMPERATURE:-0.0}"
export LLADA_GEN_LENGTH="${LLADA_GEN_LENGTH:-128}"
export LLADA_STEPS="${LLADA_STEPS:-128}"
export LLADA_BLOCK_LENGTH="${LLADA_BLOCK_LENGTH:-32}"
export LLADA_CONTEXT_LENGTH="${LLADA_CONTEXT_LENGTH:-4000}"
export LLADA_ENFORCE_CONTEXT="${LLADA_ENFORCE_CONTEXT:-0}"
export LLADA_TRUNCATE_INPUT="${LLADA_TRUNCATE_INPUT:-0}"
export BFCL_FUNCTION_DOC_SERIALIZATION="${BFCL_FUNCTION_DOC_SERIALIZATION:-json}"

echo "Start: $(date)"
echo "ROOT: $ROOT"
echo "ENV_FILE: $ENV_FILE"
echo "PYTHON_BIN: $PYTHON_BIN"
echo "CONDITION: $CONDITION"
echo "MODE: $MODE"
echo "STATE_VIEW: $STATE_VIEW"
echo "PREPARED_PROMPTS: $PREPARED_PROMPTS"
echo "SMOKE_IDS: $SMOKE_IDS"
echo "RUN_STAMP: $RUN_STAMP"
echo "OUT: $OUT"
echo "LLADA_MODEL_PATH: ${LLADA_MODEL_PATH:-<unset>}"
echo "FAST_DLLM_LLADA_PATH: ${FAST_DLLM_LLADA_PATH:-<unset>}"
echo "LLADA_GEN_LENGTH: $LLADA_GEN_LENGTH"
echo "LLADA_STEPS: $LLADA_STEPS"
echo "LLADA_BLOCK_LENGTH: $LLADA_BLOCK_LENGTH"
echo "CUDA_VISIBLE_DEVICES: ${CUDA_VISIBLE_DEVICES:-<unset>}"

DRY_RUN_ARGS=()
if [[ "${DRY_RUN:-0}" == "1" ]]; then
  DRY_RUN_ARGS+=(--dry-run)
  echo "DRY_RUN: 1"
else
  echo "DRY_RUN: 0"
fi

"$PYTHON_BIN" "$ROOT/src/run_discovery.py" \
  --category multi_turn_base \
  --mode "$MODE" \
  --prepared-prompts-path "$PREPARED_PROMPTS" \
  --ids "$SMOKE_IDS" \
  --output-dir "$OUT" \
  "${DRY_RUN_ARGS[@]}"

echo "Done: $(date)"
echo "Output directory: $OUT"
echo "Summary: $OUT/summary.md"
