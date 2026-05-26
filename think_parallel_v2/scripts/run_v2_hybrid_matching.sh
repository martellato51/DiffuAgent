#!/usr/bin/env bash
set -euo pipefail

ROOT="${ROOT:-/home/ilju/research/DiffuAgent/think_parallel_v2}"
PYTHON_BIN="${PYTHON_BIN:-python}"
OUTPUT_DIR="${OUTPUT_DIR:-${1:-$ROOT/outputs/smoke_explicit}}"
GRAPHS_PATH="${GRAPHS_PATH:-/home/ilju/research/ParallelAgent/data/annotations/bfcl_v3_think_parallel_multi_turn_base_graphs.jsonl}"
PARALLEL_AGENT_ROOT="${PARALLEL_AGENT_ROOT:-/home/ilju/research/ParallelAgent}"

JUDGE_MAX_CONCURRENT="${JUDGE_MAX_CONCURRENT:-4}"
JUDGE_TIMEOUT="${JUDGE_TIMEOUT:-180}"
JUDGE_MAX_RETRIES="${JUDGE_MAX_RETRIES:-2}"
JUDGE_SANDBOX="${JUDGE_SANDBOX:-read-only}"
CODEX_BINARY="${CODEX_BINARY:-codex}"
HIGH_SCORE_THRESHOLD="${HIGH_SCORE_THRESHOLD:-80}"
SEMANTIC_SCORE_THRESHOLD="${SEMANTIC_SCORE_THRESHOLD:-30}"
JUDGE_CONFIDENCE_THRESHOLD="${JUDGE_CONFIDENCE_THRESHOLD:-0.65}"
Q2_CONFIDENCE_THRESHOLD="${Q2_CONFIDENCE_THRESHOLD:-0.75}"

ARGS=(
  --output-dir "$OUTPUT_DIR"
  --graphs-path "$GRAPHS_PATH"
  --parallel-agent-root "$PARALLEL_AGENT_ROOT"
  --max-concurrent "$JUDGE_MAX_CONCURRENT"
  --timeout "$JUDGE_TIMEOUT"
  --max-retries "$JUDGE_MAX_RETRIES"
  --sandbox "$JUDGE_SANDBOX"
  --codex-binary "$CODEX_BINARY"
  --high-score-threshold "$HIGH_SCORE_THRESHOLD"
  --semantic-score-threshold "$SEMANTIC_SCORE_THRESHOLD"
  --confidence-threshold "$JUDGE_CONFIDENCE_THRESHOLD"
  --q2-confidence-threshold "$Q2_CONFIDENCE_THRESHOLD"
)

if [[ -n "${JUDGE_MODEL:-}" ]]; then
  ARGS+=(--model "$JUDGE_MODEL")
fi
if [[ -n "${LIMIT_PAIRS:-}" ]]; then
  ARGS+=(--limit-pairs "$LIMIT_PAIRS")
fi
if [[ "${DRY_RUN_CANDIDATES:-0}" == "1" ]]; then
  ARGS+=(--dry-run-candidates)
fi

echo "Start hybrid matcher: $(date)"
echo "ROOT: $ROOT"
echo "PYTHON_BIN: $PYTHON_BIN"
echo "OUTPUT_DIR: $OUTPUT_DIR"
echo "GRAPHS_PATH: $GRAPHS_PATH"
echo "PARALLEL_AGENT_ROOT: $PARALLEL_AGENT_ROOT"
echo "JUDGE_MAX_CONCURRENT: $JUDGE_MAX_CONCURRENT"
echo "JUDGE_TIMEOUT: $JUDGE_TIMEOUT"
echo "JUDGE_MAX_RETRIES: $JUDGE_MAX_RETRIES"
echo "JUDGE_SANDBOX: $JUDGE_SANDBOX"
echo "JUDGE_MODEL: ${JUDGE_MODEL:-<unset>}"
echo "LIMIT_PAIRS: ${LIMIT_PAIRS:-<unset>}"
echo "DRY_RUN_CANDIDATES: ${DRY_RUN_CANDIDATES:-0}"

"$PYTHON_BIN" "$ROOT/src/judge_match_v2_outputs.py" "${ARGS[@]}"

echo "Done hybrid matcher: $(date)"
