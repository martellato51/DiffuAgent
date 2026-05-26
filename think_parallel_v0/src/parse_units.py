from __future__ import annotations

import json
import re
from typing import Any


BOOL_FIELDS = {
    "can_think_now",
    "needs_prior_observation_for_arguments",
    "needs_prior_execution_before_action",
}


def _extract_json_candidate(text: str) -> tuple[str, str]:
    fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL | re.IGNORECASE)
    if fence:
        return fence.group(1).strip(), "json_fragment"
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        mode = "json" if start == 0 and end == len(text.strip()) - 1 else "json_fragment"
        return text[start : end + 1], mode
    start = text.find("[")
    end = text.rfind("]")
    if start != -1 and end != -1 and end > start:
        return text[start : end + 1], "json_fragment"
    raise ValueError("No JSON object or list found in response")


def _normalize_units(units: Any) -> tuple[list[dict[str, Any]], str | None]:
    if not isinstance(units, list):
        return [], "think_units must be a list"

    normalized: list[dict[str, Any]] = []
    for i, unit in enumerate(units, start=1):
        if not isinstance(unit, dict):
            continue
        item = {
            "unit_id": str(unit.get("unit_id") or f"u{i}"),
            "think": str(unit.get("think") or unit.get("thought") or ""),
            "action_hint": unit.get("action_hint") or unit.get("action"),
            "arguments_hint": unit.get("arguments_hint") or unit.get("arguments") or {},
            "dependency_claims": unit.get("dependency_claims") or {},
        }
        for field in BOOL_FIELDS:
            value = unit.get(field)
            item[field] = value if isinstance(value, bool) else None
        normalized.append(item)
    return normalized, None


def _parse_json_units(text: str) -> tuple[list[dict[str, Any]], str | None, str]:
    candidate, parse_mode = _extract_json_candidate(text)
    payload = json.loads(candidate)

    if isinstance(payload, list):
        units = payload
    elif isinstance(payload, dict):
        units = payload.get("think_units", [])
    else:
        return [], f"JSON root must be object/list, got {type(payload).__name__}", parse_mode

    normalized, error = _normalize_units(units)
    return normalized, error, parse_mode


def _parse_react_fallback(text: str) -> list[dict[str, Any]]:
    pattern = re.compile(
        r"Thought:\s*(?P<think>.*?)(?:\n|\r\n)Action:\s*(?P<action>.*?)(?=\n\s*(?:Observation:|Thought:)|\Z)",
        re.DOTALL | re.IGNORECASE,
    )
    units: list[dict[str, Any]] = []
    for i, match in enumerate(pattern.finditer(text), start=1):
        think = " ".join(match.group("think").strip().split())
        action = match.group("action").strip().splitlines()[0].strip()
        if not think and not action:
            continue
        units.append(
            {
                "unit_id": f"u{i}",
                "think": think,
                "action_hint": action.split("(", 1)[0].strip() if action else None,
                "arguments_hint": {},
                "dependency_claims": {},
                "can_think_now": True if think else None,
                "needs_prior_observation_for_arguments": None,
                "needs_prior_execution_before_action": None,
            }
        )
    return units


def _clean_labeled_span(value: str) -> str:
    return " ".join(value.strip().split())


def _parse_ta_labeled(text: str) -> list[dict[str, Any]]:
    label_pattern = re.compile(r"\[(?P<kind>[TA])(?P<num>\d+)\]\s*", re.IGNORECASE)
    matches = list(label_pattern.finditer(text))
    if not matches:
        return []

    spans: dict[tuple[str, str], str] = {}
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        kind = match.group("kind").upper()
        num = match.group("num")
        content = _clean_labeled_span(text[start:end])
        if content:
            spans[(kind, num)] = content

    units: list[dict[str, Any]] = []
    ordered_nums = sorted(
        {num for kind, num in spans if kind == "T"},
        key=lambda value: int(value),
    )
    for fallback_index, num in enumerate(ordered_nums, start=1):
        think = spans.get(("T", num), "")
        action = spans.get(("A", num), "")
        if not think and not action:
            continue
        units.append(
            {
                "unit_id": f"u{fallback_index}",
                "think": think,
                "action_hint": action or None,
                "arguments_hint": {},
                "dependency_claims": {},
                "can_think_now": None,
                "needs_prior_observation_for_arguments": None,
                "needs_prior_execution_before_action": None,
                "raw_action": action,
                "source_step": int(num),
            }
        )
    return units


def _parse_a_labeled(text: str) -> list[dict[str, Any]]:
    label_pattern = re.compile(r"\[A(?P<num>\d+)\]\s*", re.IGNORECASE)
    matches = list(label_pattern.finditer(text))
    if not matches:
        return []

    units: list[dict[str, Any]] = []
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        action = _clean_labeled_span(text[start:end])
        if not action:
            continue
        units.append(
            {
                "unit_id": f"u{len(units) + 1}",
                "think": "",
                "action_hint": action,
                "arguments_hint": {},
                "dependency_claims": {},
                "can_think_now": None,
                "needs_prior_observation_for_arguments": None,
                "needs_prior_execution_before_action": None,
                "raw_action": action,
                "source_step": int(match.group("num")),
            }
        )
    return units


def parse_think_units(text: str) -> tuple[list[dict[str, Any]], str | None, str]:
    ta_units = _parse_ta_labeled(text)
    if ta_units:
        return ta_units, None, "ta"

    a_units = _parse_a_labeled(text)
    if a_units:
        return a_units, None, "a_only"

    try:
        return _parse_json_units(text)
    except Exception as exc:
        json_error = str(exc)

    fallback_units = _parse_react_fallback(text)
    if fallback_units:
        return fallback_units, json_error, "react_fallback"
    return [], json_error, "failed"
