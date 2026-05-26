from __future__ import annotations

import copy
import json
import os
import re
import sys
import uuid
from pathlib import Path
from typing import Any


MULTI_TURN_FUNC_DOC_FILE_MAPPING = {
    "GorillaFileSystem": "gorilla_file_system.json",
    "MathAPI": "math_api.json",
    "MessageAPI": "message_api.json",
    "TwitterAPI": "posting_api.json",
    "TicketAPI": "ticket_api.json",
    "TradingBot": "trading_bot.json",
    "TravelAPI": "travel_booking.json",
    "VehicleControlAPI": "vehicle_control.json",
}


def ensure_bfcl_on_path(bfcl_root: Path) -> None:
    root = str(bfcl_root.resolve())
    if root not in sys.path:
        sys.path.insert(0, root)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            if "_config" not in obj:
                rows.append(obj)
    return rows


def load_json_or_jsonl(path: Path) -> list[dict[str, Any]]:
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError:
        return read_jsonl(path)
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return list(data.values())
    raise TypeError(f"Unsupported JSON payload in {path}")


def category_to_data_name(category: str) -> str:
    return "BFCL_v3_" + category


def load_graphs(path: Path | None) -> dict[str, dict[str, Any]]:
    if path is None:
        return {}
    if not path.exists():
        raise FileNotFoundError(f"Missing graph file: {path}")
    return {row["question_id"]: row for row in read_jsonl(path)}


def load_ids_from_file(path: Path, key: str) -> list[str]:
    with path.open("r", encoding="utf-8") as f:
        payload = json.load(f)
    if isinstance(payload, list):
        return [str(item) for item in payload]
    if not isinstance(payload, dict):
        raise ValueError(f"Expected list or object in id file: {path}")
    ids = payload.get(key)
    if ids is None:
        available = ", ".join(sorted(payload))
        raise ValueError(f"Missing key {key!r} in {path}; available: {available}")
    if not isinstance(ids, list):
        raise ValueError(f"Expected {key!r} in {path} to be a list")
    return [str(item) for item in ids]


def _load_multi_turn_function_docs(bfcl_root: Path, class_name: str) -> list[dict[str, Any]]:
    file_name = MULTI_TURN_FUNC_DOC_FILE_MAPPING.get(class_name)
    if not file_name:
        raise KeyError(f"Unknown multi-turn function collection: {class_name}")
    doc_path = bfcl_root / "bfcl_eval" / "data" / "multi_turn_func_doc" / file_name
    if not doc_path.exists():
        raise FileNotFoundError(f"Missing multi-turn function doc: {doc_path}")
    return read_jsonl(doc_path)


def attach_multi_turn_function_docs(
    bfcl_root: Path,
    records: list[dict[str, Any]],
) -> None:
    for record in records:
        if record.get("function") or "involved_classes" not in record:
            continue
        functions: list[dict[str, Any]] = []
        sources: list[str] = []
        for class_name in record["involved_classes"]:
            file_name = MULTI_TURN_FUNC_DOC_FILE_MAPPING[class_name]
            functions.extend(_load_multi_turn_function_docs(bfcl_root, class_name))
            sources.append(file_name)
        record["function"] = functions
        record["_bfcl_function_doc_sources"] = sources


def load_possible_answers(bfcl_root: Path, category: str) -> dict[str, dict[str, Any]]:
    path = (
        bfcl_root
        / "bfcl_eval"
        / "data"
        / "possible_answer"
        / f"{category_to_data_name(category)}.json"
    )
    if not path.exists():
        raise FileNotFoundError(f"Expected BFCL possible_answer file: {path}")
    return {row["id"]: row for row in load_json_or_jsonl(path)}


def load_bfcl_records(
    bfcl_root: Path,
    category: str,
    ids: list[str] | None,
) -> list[dict[str, Any]]:
    data_path = bfcl_root / "bfcl_eval" / "data" / f"{category_to_data_name(category)}.json"
    if not data_path.exists():
        raise FileNotFoundError(f"Expected BFCL data file: {data_path}")
    records = load_json_or_jsonl(data_path)
    attach_multi_turn_function_docs(bfcl_root, records)
    if ids:
        wanted = set(ids)
        records = [record for record in records if record.get("id") in wanted]
        found = {record.get("id") for record in records}
        missing = sorted(wanted - found)
        if missing:
            raise ValueError(f"Missing BFCL ids in {data_path}: {missing}")
        order = {sample_id: i for i, sample_id in enumerate(ids)}
        records.sort(key=lambda record: order[record["id"]])
    for record in records:
        record["_bfcl_data_source"] = str(data_path)
    return records


def turn_user_text(turn_messages: list[dict[str, str]]) -> str:
    return "\n".join(
        msg.get("content", "")
        for msg in turn_messages
        if msg.get("role") == "user" and msg.get("content")
    ).strip()


def _descendants(graph: dict[str, Any]) -> dict[str, set[str]]:
    hops = graph.get("hops", [])
    ids = [hop["id"] for hop in hops]
    succ: dict[str, set[str]] = {hid: set() for hid in ids}
    for hop in hops:
        hid = hop["id"]
        for dep in hop.get("depends_on", []):
            if dep in succ:
                succ[dep].add(hid)
    closure: dict[str, set[str]] = {hid: {hid} for hid in ids}
    for hid in reversed(ids):
        for nxt in succ[hid]:
            closure[hid] |= closure[nxt]
    return closure


def _turn_layers(hops: list[dict[str, Any]]) -> list[list[str]]:
    ids = [hop["id"] for hop in hops]
    valid = set(ids)
    remaining = {
        hop["id"]: {dep for dep in hop.get("depends_on", []) if dep in valid}
        for hop in hops
    }
    placed: set[str] = set()
    layers: list[list[str]] = []
    while len(placed) < len(ids):
        layer = [hid for hid in ids if hid not in placed and not (remaining[hid] - placed)]
        if not layer:
            layer = [hid for hid in ids if hid not in placed]
        layers.append(layer)
        placed.update(layer)
    return layers


def graph_turn_stats(graph: dict[str, Any] | None, turn_index: int) -> dict[str, Any]:
    if not graph:
        return {
            "has_graph": False,
            "turn_index": turn_index,
            "gold_hop_ids": [],
            "n_gold_hops": None,
            "n_intra_turn_antichain_pairs": None,
            "turn_width": None,
            "turn_layers": None,
        }
    hops = [hop for hop in graph.get("hops", []) if hop.get("turn") == turn_index]
    hop_ids = [hop["id"] for hop in hops]
    closure = _descendants(graph)
    pairs: list[list[str]] = []
    for i, a in enumerate(hop_ids):
        for b in hop_ids[i + 1 :]:
            if b not in closure.get(a, {a}) and a not in closure.get(b, {b}):
                pairs.append([a, b])
    layers = _turn_layers(hops) if hops else []
    return {
        "has_graph": True,
        "turn_index": turn_index,
        "gold_hop_ids": hop_ids,
        "n_gold_hops": len(hops),
        "n_intra_turn_antichain_pairs": len(pairs),
        "intra_turn_antichain_pairs": pairs,
        "turn_width": max((len(layer) for layer in layers), default=0),
        "turn_layers": layers,
    }


def _episode_matches_filter(
    record: dict[str, Any],
    graph: dict[str, Any] | None,
    episode_filter: str,
) -> bool:
    if episode_filter == "all":
        return True
    if episode_filter == "graph_available":
        return graph is not None
    if episode_filter == "intra_turn_parallel":
        return bool(
            graph
            and graph.get("turn_bound_max_width", 0) >= 2
            and graph.get("n_intra_turn_antichain_pairs", 0) > 0
        )
    if episode_filter == "multi_hop":
        ground_truth = record.get("ground_truth", [])
        return sum(len(turn_calls) for turn_calls in ground_truth) >= 2
    raise ValueError(f"Unsupported episode filter: {episode_filter}")


def build_episode(
    record: dict[str, Any],
    gold: dict[str, Any],
    graph: dict[str, Any] | None,
) -> dict[str, Any]:
    ground_truth = gold.get("ground_truth") or []
    turns: list[dict[str, Any]] = []
    questions = record.get("question") or []
    for turn_index, messages in enumerate(questions):
        gold_calls = ground_truth[turn_index] if turn_index < len(ground_truth) else []
        turns.append(
            {
                "turn_index": turn_index,
                "messages": messages,
                "user_text": turn_user_text(messages),
                "gold_calls": list(gold_calls),
                "graph_stats": graph_turn_stats(graph, turn_index),
            }
        )
    episode = copy.deepcopy(record)
    episode["ground_truth"] = ground_truth
    episode["graph"] = graph
    episode["turns"] = turns
    return episode


def load_multiturn_episodes(
    bfcl_root: Path,
    category: str,
    *,
    ids: list[str] | None = None,
    graphs_path: Path | None = None,
    episode_filter: str = "all",
    max_episodes: int | None = None,
) -> list[dict[str, Any]]:
    records = load_bfcl_records(bfcl_root, category, ids)
    gold_by_id = load_possible_answers(bfcl_root, category)
    graphs = load_graphs(graphs_path)

    episodes: list[dict[str, Any]] = []
    for record in records:
        sample_id = record["id"]
        gold = gold_by_id.get(sample_id)
        if gold is None:
            raise ValueError(f"Missing possible_answer for {sample_id}")
        merged_for_filter = dict(record)
        merged_for_filter["ground_truth"] = gold.get("ground_truth") or []
        graph = graphs.get(sample_id)
        if not _episode_matches_filter(merged_for_filter, graph, episode_filter):
            continue
        episodes.append(build_episode(record, gold, graph))
        if max_episodes is not None and len(episodes) >= max_episodes:
            break
    return episodes


def _safe_model_name(value: str) -> str:
    value = re.sub(r"[^A-Za-z0-9_]+", "_", value)
    return value.strip("_") or "run"


def replay_gold_observations(
    bfcl_root: Path,
    episode: dict[str, Any],
    *,
    run_label: str,
    strict: bool = False,
) -> list[list[str]]:
    """Replay gold calls turn-by-turn and return observations aligned with turns."""
    ensure_bfcl_on_path(bfcl_root)
    from bfcl_eval.eval_checker.multi_turn_eval.multi_turn_utils import (
        execute_multi_turn_func_call,
    )

    sample_id = episode["id"]
    model_name = _safe_model_name(
        f"think_parallel_v2_{run_label}_{sample_id}_{uuid.uuid4().hex[:8]}"
    )
    initial_config = episode["initial_config"]
    involved_classes = episode["involved_classes"]
    test_category = sample_id.rsplit("_", 1)[0]
    long_context = "long_context" in test_category or "composite" in test_category

    all_observations: list[list[str]] = []
    for turn in episode["turns"]:
        try:
            observations, _instances = execute_multi_turn_func_call(
                turn["gold_calls"],
                initial_config,
                involved_classes,
                model_name,
                sample_id,
                long_context=long_context,
                is_evaL_run=False,
            )
        except Exception as exc:
            if strict:
                raise
            observations = [
                f"Error during gold replay: {type(exc).__name__}: {exc}"
                for _ in turn["gold_calls"]
            ]
        obs_list = [str(item) for item in observations]
        turn["gold_observations"] = obs_list
        all_observations.append(obs_list)
    return all_observations
