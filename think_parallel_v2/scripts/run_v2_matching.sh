#!/usr/bin/env bash
set -euo pipefail

ROOT="${ROOT:-/home/ilju/research/DiffuAgent/think_parallel_v2}"
PYTHON_BIN="${PYTHON_BIN:-python}"
OUTPUT_DIR="${OUTPUT_DIR:-${1:-$ROOT/outputs/smoke_explicit}}"
GRAPHS_PATH="${GRAPHS_PATH:-/home/ilju/research/ParallelAgent/data/annotations/bfcl_v3_think_parallel_multi_turn_base_graphs.jsonl}"
SCORE_THRESHOLD="${SCORE_THRESHOLD:-100}"

echo "Start P0 deterministic matcher: $(date)"
echo "ROOT: $ROOT"
echo "PYTHON_BIN: $PYTHON_BIN"
echo "OUTPUT_DIR: $OUTPUT_DIR"
echo "GRAPHS_PATH: $GRAPHS_PATH"
echo "SCORE_THRESHOLD: $SCORE_THRESHOLD"

"$PYTHON_BIN" "$ROOT/src/match_v2_outputs.py" \
  --output-dir "$OUTPUT_DIR" \
  --graphs-path "$GRAPHS_PATH" \
  --score-threshold "$SCORE_THRESHOLD"

echo "Done P0 deterministic matcher: $(date)"
