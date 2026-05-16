#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "usage: $0 OUTPUT_DIR [extra judge args...]" >&2
  exit 2
fi

OUTPUT_DIR="$1"
shift

EXPERIMENT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DIFFUAGENT_ROOT="$(cd "${EXPERIMENT_ROOT}/.." && pwd)"
RESEARCH_ROOT="${RESEARCH_ROOT:-$(cd "${DIFFUAGENT_ROOT}/.." && pwd)}"

source "${DIFFUAGENT_ROOT}/env.sh"
export BFCL_PROJECT_ROOT="${BFCL_ROOT:-${DIFFUAGENT_ROOT}/unified_envs/gorilla_bfcl_v3/berkeley-function-call-leaderboard}"
export PYTHONPATH="${BFCL_PROJECT_ROOT}:${EXPERIMENT_ROOT}:${PYTHONPATH:-}"

PYTHON="${PYTHON:-${LLADA_PYTHON:-python}}"
GRAPHS="${GRAPHS:-${RESEARCH_ROOT}/ParallelAgent/data/annotations/bfcl_v3_diffuagent_base_graphs.jsonl}"
PARALLEL_AGENT_ROOT="${PARALLEL_AGENT_ROOT:-${RESEARCH_ROOT}/ParallelAgent}"

echo "OUTPUT_DIR: $OUTPUT_DIR"
echo "GRAPHS: $GRAPHS"
echo "PARALLEL_AGENT_ROOT: $PARALLEL_AGENT_ROOT"
echo "PYTHON: $PYTHON"
echo "JUDGE_TOP_K: ${JUDGE_TOP_K:-5}"
echo "JUDGE_MAX_CONCURRENT: ${JUDGE_MAX_CONCURRENT:-4}"
echo "JUDGE_TIMEOUT: ${JUDGE_TIMEOUT:-180}"

"$PYTHON" "$EXPERIMENT_ROOT/src/judge_match_outputs.py" \
  "$OUTPUT_DIR" \
  --graphs "$GRAPHS" \
  --parallel-agent-root "$PARALLEL_AGENT_ROOT" \
  "$@"
