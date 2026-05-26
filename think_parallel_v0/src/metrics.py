from __future__ import annotations

from collections import defaultdict
from statistics import mean
from typing import Any


def row_matched_hop_ids(row: dict[str, Any]) -> list[str]:
    hop_ids = row.get("matched_hop_ids")
    if isinstance(hop_ids, list):
        return [str(hop_id) for hop_id in hop_ids if hop_id]
    hop_id = row.get("matched_hop_id")
    return [str(hop_id)] if hop_id else []


def overlap(a_start: int, a_end: int, b_start: int, b_end: int) -> bool:
    return a_start < b_end and b_start < a_end


def find_unit_span(response: str, think: str) -> tuple[int | None, int | None]:
    if not think:
        return None, None
    pos = response.find(think)
    if pos == -1:
        compact = " ".join(think.split())
        response_compact = " ".join(response.split())
        pos = response_compact.find(compact)
        if pos == -1:
            return None, None
        return None, None
    return pos, pos + len(think)


def token_stats_for_span(
    trace_tokens: list[dict[str, Any]],
    start: int | None,
    end: int | None,
) -> dict[str, Any]:
    if start is None or end is None:
        return {
            "span_found": False,
            "n_tokens": 0,
            "mean_confidence": None,
            "min_confidence": None,
            "bottom_10p_mean_confidence": None,
            "commit_step_mean": None,
        }
    selected = [
        token
        for token in trace_tokens
        if token.get("confidence") is not None
        and overlap(start, end, token.get("char_start", -1), token.get("char_end", -1))
    ]
    if not selected:
        return {
            "span_found": True,
            "n_tokens": 0,
            "mean_confidence": None,
            "min_confidence": None,
            "bottom_10p_mean_confidence": None,
            "commit_step_mean": None,
        }
    confs = [float(token["confidence"]) for token in selected]
    steps = [int(token["commit_step"]) for token in selected if token.get("commit_step") is not None]
    sorted_confs = sorted(confs)
    bottom_n = max(1, int(len(sorted_confs) * 0.1))
    return {
        "span_found": True,
        "n_tokens": len(selected),
        "mean_confidence": mean(confs),
        "min_confidence": min(confs),
        "bottom_10p_mean_confidence": mean(sorted_confs[:bottom_n]),
        "commit_step_mean": mean(steps) if steps else None,
    }


def summarize_metrics(
    rows: list[dict[str, Any]],
    parse_records: list[dict[str, Any]] | None = None,
    eval_records: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    out: dict[str, Any] = {"modes": {}, "overall": {}}
    by_mode: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_mode[row["mode"]].append(row)
    parse_by_mode: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in parse_records or []:
        parse_by_mode[record["mode"]].append(record)
    eval_by_mode: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in eval_records or []:
        eval_by_mode[record["mode"]].append(record)

    modes = sorted(set(by_mode) | set(parse_by_mode) | set(eval_by_mode))
    for mode in modes:
        items = by_mode.get(mode, [])
        matched = [item for item in items if row_matched_hop_ids(item)]
        compound = [item for item in items if item.get("compound_action")]
        by_label: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for item in matched:
            labels = item.get("gold_edge_label_summaries")
            if isinstance(labels, list) and labels:
                for label in labels:
                    by_label[label or "Unknown"].append(item)
            else:
                by_label[item.get("gold_edge_label_summary") or "Unknown"].append(item)

        label_stats = {}
        for label, label_items in sorted(by_label.items()):
            confs = [
                item.get("mean_confidence")
                for item in label_items
                if item.get("mean_confidence") is not None
            ]
            action_confs = [
                item.get("action_mean_confidence")
                for item in label_items
                if item.get("action_mean_confidence") is not None
            ]
            label_stats[label] = {
                "n": len(label_items),
                "n_with_confidence": len(confs),
                "mean_confidence": mean(confs) if confs else None,
                "n_with_action_confidence": len(action_confs),
                "action_mean_confidence": mean(action_confs) if action_confs else None,
            }

        parse_items = parse_by_mode.get(mode, [])
        parse_ok = [
            item for item in parse_items if item.get("parse_mode") != "failed"
        ]
        ta_parse_ok = [
            item for item in parse_items if item.get("parse_mode") == "ta"
        ]
        a_parse_ok = [
            item for item in parse_items if item.get("parse_mode") == "a_only"
        ]
        eval_items = eval_by_mode.get(mode, [])
        gold_total = sum(
            int(item.get("n_gold_hops") or 0)
            for item in eval_items
            if item.get("n_gold_hops") is not None
        )
        matched_gold_total = sum(int(item.get("n_matched_hops") or 0) for item in eval_items)
        unmatched_total = sum(int(item.get("n_unmatched_units") or 0) for item in eval_items)
        missing_total = max(0, gold_total - matched_gold_total) if eval_items else 0

        out["modes"][mode] = {
            "n_units": len(items),
            "n_matched": len(matched),
            "n_unmatched": len(items) - len(matched),
            "match_rate": len(matched) / len(items) if items else 0.0,
            "action_hint_match_rate": len(matched) / len(items) if items else 0.0,
            "n_compound_actions": len(compound),
            "compound_action_rate": len(compound) / len(items) if items else 0.0,
            "n_generations": len(parse_items),
            "format_parse_rate": len(parse_ok) / len(parse_items) if parse_items else None,
            "ta_format_rate": len(ta_parse_ok) / len(parse_items) if parse_items else None,
            "a_only_format_rate": (
                len(a_parse_ok) / len(parse_items) if parse_items else None
            ),
            "tool_selection_recall": (
                matched_gold_total / gold_total if gold_total else None
            ),
            "missing_action_rate": missing_total / gold_total if gold_total else None,
            "hallucinated_action_rate": (
                unmatched_total / len(items) if items else None
            ),
            "labels": label_stats,
            "ranking": {
                "weak_a_above_strong": pairwise_above(
                    by_label.get("Weak-A", []), by_label.get("Strong", [])
                ),
                "independent_above_strong": pairwise_above(
                    by_label.get("Independent", []), by_label.get("Strong", [])
                ),
            },
        }
    out["overall"]["n_units"] = len(rows)
    out["overall"]["n_matched"] = sum(1 for row in rows if row_matched_hop_ids(row))
    out["overall"]["n_compound_actions"] = sum(
        1 for row in rows if row.get("compound_action")
    )
    out["overall"]["compound_action_rate"] = (
        out["overall"]["n_compound_actions"] / len(rows) if rows else 0.0
    )
    if parse_records is not None:
        ok = [record for record in parse_records if record.get("parse_mode") != "failed"]
        out["overall"]["n_generations"] = len(parse_records)
        out["overall"]["format_parse_rate"] = (
            len(ok) / len(parse_records) if parse_records else None
        )
        ta_ok = [record for record in parse_records if record.get("parse_mode") == "ta"]
        out["overall"]["ta_format_rate"] = (
            len(ta_ok) / len(parse_records) if parse_records else None
        )
        a_ok = [
            record for record in parse_records if record.get("parse_mode") == "a_only"
        ]
        out["overall"]["a_only_format_rate"] = (
            len(a_ok) / len(parse_records) if parse_records else None
        )
    return out


def pairwise_above(left: list[dict[str, Any]], right: list[dict[str, Any]]) -> float | None:
    left_confs = [
        item.get("mean_confidence")
        for item in left
        if item.get("mean_confidence") is not None
    ]
    right_confs = [
        item.get("mean_confidence")
        for item in right
        if item.get("mean_confidence") is not None
    ]
    if not left_confs or not right_confs:
        return None
    wins = 0.0
    total = 0
    for left_conf in left_confs:
        for right_conf in right_confs:
            total += 1
            if left_conf > right_conf:
                wins += 1.0
            elif left_conf == right_conf:
                wins += 0.5
    return wins / total if total else None


def render_summary(metrics: dict[str, Any]) -> str:
    lines = ["# BFCL Think Parallel v0 Summary", ""]
    for mode, stats in metrics.get("modes", {}).items():
        lines.append(f"## {mode}")
        lines.append(f"- units: {stats['n_units']}")
        lines.append(f"- matched: {stats['n_matched']}")
        lines.append(f"- match_rate: {stats['match_rate']:.3f}")
        compound_rate = stats.get("compound_action_rate")
        if compound_rate is not None:
            lines.append(
                f"- compound_action_rate: {compound_rate:.3f} "
                f"({stats.get('n_compound_actions', 0)} units)"
            )
        parse_rate = stats.get("format_parse_rate")
        if parse_rate is not None:
            lines.append(f"- format_parse_rate: {parse_rate:.3f}")
        if mode.endswith("_ta") or mode.endswith("_a"):
            ta_rate = stats.get("ta_format_rate")
            if mode.endswith("_ta") and ta_rate is not None:
                lines.append(f"- ta_format_rate: {ta_rate:.3f}")
            a_rate = stats.get("a_only_format_rate")
            if mode.endswith("_a") and a_rate is not None:
                lines.append(f"- a_only_format_rate: {a_rate:.3f}")
            tool_recall = stats.get("tool_selection_recall")
            if tool_recall is not None:
                lines.append(f"- tool_selection_recall: {tool_recall:.3f}")
            missing_rate = stats.get("missing_action_rate")
            if missing_rate is not None:
                lines.append(f"- missing_action_rate: {missing_rate:.3f}")
            hallucinated_rate = stats.get("hallucinated_action_rate")
            if hallucinated_rate is not None:
                lines.append(f"- hallucinated_action_rate: {hallucinated_rate:.3f}")
        for label, label_stats in stats.get("labels", {}).items():
            conf = label_stats.get("mean_confidence")
            conf_text = "null" if conf is None else f"{conf:.4f}"
            action_conf = label_stats.get("action_mean_confidence")
            action_conf_text = "null" if action_conf is None else f"{action_conf:.4f}"
            if mode.endswith("_ta"):
                lines.append(
                    f"- {label}: n={label_stats['n']}, "
                    f"think_mean_confidence={conf_text}, "
                    f"action_mean_confidence={action_conf_text}"
                )
            elif mode.endswith("_a"):
                lines.append(
                    f"- {label}: n={label_stats['n']}, "
                    f"action_mean_confidence={action_conf_text}"
                )
            else:
                lines.append(
                    f"- {label}: n={label_stats['n']}, "
                    f"n_with_confidence={label_stats['n_with_confidence']}, "
                    f"mean_confidence={conf_text}"
                )
        for name, value in stats.get("ranking", {}).items():
            value_text = "null" if value is None else f"{value:.3f}"
            lines.append(f"- ranking.{name}: {value_text}")
        lines.append("")
    return "\n".join(lines)
