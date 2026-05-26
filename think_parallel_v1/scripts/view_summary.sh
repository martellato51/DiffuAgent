#!/usr/bin/env bash
set -euo pipefail

RUN_DIR="${1:?usage: $0 OUTPUT_DIR}"

echo "== summary.md =="
if [[ -f "$RUN_DIR/summary.md" ]]; then
  sed -n '1,220p' "$RUN_DIR/summary.md"
else
  echo "<missing summary.md>"
fi

echo
echo "== user requests =="
python - "$RUN_DIR/raw_generations.jsonl" <<'PY'
import json
import sys

seen = set()
for line in open(sys.argv[1], encoding="utf-8"):
    item = json.loads(line)
    qid = item.get("question_id")
    if qid in seen:
        continue
    seen.add(qid)
    print(f"## {qid}")
    print(item.get("goal") or "<missing goal>")
    print()
PY

echo
echo "== generated actions =="
python - "$RUN_DIR/think_units.jsonl" <<'PY'
import json
import sys

for line in open(sys.argv[1], encoding="utf-8"):
    item = json.loads(line)
    print(f"## {item['question_id']} {item['mode']} parse={item.get('parse_mode')}")
    if item.get("parse_error"):
        print(f"PARSE_ERROR: {item['parse_error']}")
    for unit in item.get("units", []):
        n = unit.get("source_step") or unit.get("unit_id") or "?"
        print(f"[A{n}] {unit.get('raw_action') or unit.get('action_hint') or '<no-action>'}")
        print(f"  tool={unit.get('tool_name')} intent={unit.get('intent')}")
        print(f"  known={unit.get('known_inputs')} unresolved={unit.get('unresolved_inputs')}")
    print()
PY

if [[ -f "$RUN_DIR/judge_matches.jsonl" ]]; then
  echo
  echo "== judge matches =="
  python - "$RUN_DIR/judge_matches.jsonl" <<'PY'
import json
import sys

for line in open(sys.argv[1], encoding="utf-8"):
    item = json.loads(line)
    print(f"## {item['question_id']} {item['mode']}")
    for row in item.get("rows", []):
        unit = row.get("unit") or {}
        action = unit.get("raw_action") or unit.get("action_hint") or "<no-action>"
        matched = ",".join(row.get("matched_hop_ids") or []) or "unmatched"
        flags = []
        if row.get("compound_action"):
            flags.append("compound")
        if row.get("hallucinated_argument"):
            flags.append("hallucinated_arg")
        if row.get("duplicate_primary_match"):
            flags.append("duplicate")
        flag_text = f" [{' '.join(flags)}]" if flags else ""
        print(
            f"- {row.get('unit_id')} -> {matched}{flag_text} "
            f"primary={row.get('primary_hop_id')} strength={row.get('match_strength')} "
            f"single={row.get('single_hop_match')} conf={row.get('judge_confidence')}"
        )
        print(f"  action={action}")
        if row.get("judge_reason"):
            print(f"  reason={row.get('judge_reason')}")
    print()
PY
else
  echo
  echo "== judge matches =="
  echo "<judge not run yet>"
fi

if [[ -f "$RUN_DIR/judge_metrics.json" ]]; then
  echo
  echo "== judge metrics =="
  python - "$RUN_DIR/judge_metrics.json" <<'PY'
import json
import sys

data = json.load(open(sys.argv[1], encoding="utf-8"))
for key, value in data.get("metrics", {}).items():
    if isinstance(value, float):
        print(f"{key}: {value:.3f}")
    else:
        print(f"{key}: {value}")
PY
fi
