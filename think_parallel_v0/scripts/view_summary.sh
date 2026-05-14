#!/usr/bin/env bash
set -euo pipefail

RUN_DIR="${1:?usage: $0 OUTPUT_DIR}"

echo "== summary.md =="
sed -n '1,200p' "$RUN_DIR/summary.md"

echo
echo "== user requests =="
if command -v jq >/dev/null 2>&1; then
  jq -rs '
    unique_by(.question_id)
    | .[]
    | "## \(.question_id)\n\(.goal // "<missing goal>")\n"
  ' "$RUN_DIR/raw_generations.jsonl"
else
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
fi

echo
echo "== T/A pairs =="
if command -v jq >/dev/null 2>&1; then
  jq -r '
    .question_id as $qid
    | .mode as $mode
    | "## \($qid) \($mode)\n" +
      ([.units[]? |
        (.source_step // .unit_id // "?") as $n
        | if ($mode | endswith("_a")) then
            "[A\($n)] \(.action_hint // "<no-action>")"
          else
            "[T\($n)] \(.think // "")\n[A\($n)] \(.action_hint // "<no-action>")"
          end
      ] | join("\n\n"))
  ' "$RUN_DIR/think_units.jsonl"
else
  python - "$RUN_DIR/think_units.jsonl" <<'PY'
import json
import sys

for line in open(sys.argv[1], encoding="utf-8"):
    item = json.loads(line)
    print(f"## {item['question_id']} {item['mode']}")
    for unit in item.get("units", []):
        n = unit.get("source_step") or unit.get("unit_id") or "?"
        think = unit.get("think") or ""
        action = unit.get("action_hint") or "<no-action>"
        if item["mode"].endswith("_a"):
            print(f"[A{n}] {action}")
        else:
            print(f"[T{n}] {think}")
            print(f"[A{n}] {action}")
        print()
PY
fi

echo
echo "== parsed units =="
if command -v jq >/dev/null 2>&1; then
  jq -r '
    .question_id as $qid
    | .mode as $mode
    | if .parse_error then
        "## \($qid) \($mode)\nPARSE_ERROR: \(.parse_error)\n"
      else
        "## \($qid) \($mode)\n" +
        ([.units[]? |
          if ($mode | endswith("_a")) then
            "- \(.unit_id) \(.action_hint // "<no-action>")"
          else
            "- \(.unit_id) \(.action_hint // "<no-action>") :: \(.think)"
          end
        ] | join("\n"))
      end
  ' "$RUN_DIR/think_units.jsonl"
else
  python - "$RUN_DIR/think_units.jsonl" <<'PY'
import json
import sys

for line in open(sys.argv[1], encoding="utf-8"):
    item = json.loads(line)
    print(f"## {item['question_id']} {item['mode']}")
    if item.get("parse_error"):
        print(f"PARSE_ERROR: {item['parse_error']}")
    else:
        for unit in item.get("units", []):
            action = unit.get("action_hint") or "<no-action>"
            if item["mode"].endswith("_a"):
                print(f"- {unit.get('unit_id')} {action}")
            else:
                print(f"- {unit.get('unit_id')} {action} :: {unit.get('think')}")
    print()
PY
fi

echo
echo "== matched =="
if command -v jq >/dev/null 2>&1; then
  jq -r '
    .question_id as $qid
    | .mode as $mode
    | "## \($qid) \($mode)\n" +
      ([.rows[]? |
        (.matched_hop_ids // ([.matched_hop_id] | map(select(. != null)))) as $hop_ids
        | (.matched_tools // ([.matched_tool] | map(select(. != null)))) as $tools
        | (.gold_edge_label_summaries // ([.gold_edge_label_summary] | map(select(. != null)))) as $labels
        | (if .compound_action then " compound" else "" end) as $compound
        | "- \(.unit_id) -> \(if ($hop_ids | length) > 0 then ($hop_ids | join(",")) else "unmatched" end)" +
        "\($compound) " +
        "[\(if ($labels | length) > 0 then ($labels | join(",")) else "no-label" end)] " +
        "tools=\(if ($tools | length) > 0 then ($tools | join(",")) else "none" end) " +
        "conf=\(.mean_confidence // "null") action=\(.action_hint // "null")"
      ] | join("\n"))
  ' "$RUN_DIR/matched_units.jsonl"
else
  python - "$RUN_DIR/matched_units.jsonl" <<'PY'
import json
import sys

for line in open(sys.argv[1], encoding="utf-8"):
    item = json.loads(line)
    print(f"## {item['question_id']} {item['mode']}")
    for row in item.get("rows", []):
        hop_ids = row.get("matched_hop_ids") or (
            [row["matched_hop_id"]] if row.get("matched_hop_id") else []
        )
        tools = row.get("matched_tools") or (
            [row["matched_tool"]] if row.get("matched_tool") else []
        )
        hop = ",".join(hop_ids) if hop_ids else "unmatched"
        tool_text = ",".join(tools) if tools else "none"
        compound = " compound" if row.get("compound_action") else ""
        labels = row.get("gold_edge_label_summaries") or (
            [row["gold_edge_label_summary"]]
            if row.get("gold_edge_label_summary")
            else []
        )
        label = ",".join(labels) if labels else "no-label"
        conf = row.get("mean_confidence")
        action = row.get("action_hint") or "null"
        print(
            f"- {row.get('unit_id')} -> {hop}{compound} [{label}] "
            f"tools={tool_text} conf={conf} action={action}"
        )
    print()
PY
fi
