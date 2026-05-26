from __future__ import annotations

import json
import re
from typing import Any


def _clean_labeled_span(value: str) -> str:
    return " ".join(value.strip().split())


def _field_span(text: str, value: str) -> dict[str, int | None]:
    if not value:
        return {"start": None, "end": None}
    start = text.find(value)
    if start < 0:
        return {"start": None, "end": None}
    return {"start": start, "end": start + len(value)}


def _null_span() -> dict[str, int | None]:
    return {"start": None, "end": None}


def _span(start: int, end: int) -> dict[str, int | None]:
    return {"start": start, "end": end}


def _find_marker(text: str, marker: str) -> int:
    return text.lower().find(marker.lower())


def _strip_terminal_period(text: str) -> str:
    return text.strip().rstrip(".").strip()


def _parse_exact_action(action: str) -> dict[str, Any]:
    known_marker = "Known inputs:"
    inputs_marker = "Inputs:"
    unresolved_marker = "Unresolved inputs:"
    known_pos = _find_marker(action, known_marker)
    inputs_pos = _find_marker(action, inputs_marker)
    unresolved_pos = _find_marker(action, unresolved_marker)

    head_end = len(action)
    for marker_pos in [known_pos, inputs_pos, unresolved_pos]:
        if marker_pos >= 0:
            head_end = min(head_end, marker_pos)
    head = action[:head_end].strip()

    known_inputs = ""
    unresolved_inputs = ""
    input_field_pos = known_pos if known_pos >= 0 else inputs_pos
    input_field_marker = known_marker if known_pos >= 0 else inputs_marker
    if input_field_pos >= 0:
        known_start = input_field_pos + len(input_field_marker)
        known_end = (
            unresolved_pos
            if unresolved_pos >= 0 and unresolved_pos > input_field_pos
            else len(action)
        )
        known_inputs = _strip_terminal_period(action[known_start:known_end])
    if unresolved_pos >= 0:
        unresolved_start = unresolved_pos + len(unresolved_marker)
        unresolved_inputs = _strip_terminal_period(action[unresolved_start:])

    tool_name = None
    intent = head
    match = re.match(
        r"^\s*(?:Use\s+)?(?P<tool>[A-Za-z_][A-Za-z0-9_.]*)\s*:\s*(?P<intent>.*)$",
        head,
        flags=re.IGNORECASE,
    )
    if match:
        tool_name = match.group("tool").strip()
        intent = match.group("intent").strip()
    else:
        loose = re.match(
            r"^\s*Use\s+(?P<tool>[A-Za-z_][A-Za-z0-9_.]*)\b(?P<intent>.*)$",
            head,
            flags=re.IGNORECASE,
        )
        if loose:
            tool_name = loose.group("tool").strip()
            intent = loose.group("intent").strip(" :-")

    intent = _strip_terminal_period(intent)
    action_hint = (
        f"Use {tool_name}: {intent}" if tool_name and intent else action
    )
    arguments_hint = {
        "known_inputs": known_inputs,
        "unresolved_inputs": unresolved_inputs,
    }
    return {
        "tool_name": tool_name,
        "intent": intent,
        "known_inputs": known_inputs,
        "unresolved_inputs": unresolved_inputs,
        "action_hint": action_hint,
        "arguments_hint": arguments_hint,
        "field_spans": {
            "tool_name": _field_span(action, tool_name or ""),
            "intent": _field_span(action, intent),
            "known_inputs": _field_span(action, known_inputs),
            "unresolved_inputs": _field_span(action, unresolved_inputs),
        },
    }


def _parse_a_labeled(text: str) -> tuple[list[dict[str, Any]], str]:
    # Treat only line-start labels as action boundaries. Generated actions may refer
    # to prior steps inside fields, e.g. "Unresolved inputs: [A1]".
    label_pattern = re.compile(r"(?:^|\n)\s*\[A(?P<num>\d+)\]\s*", re.IGNORECASE)
    matches = list(label_pattern.finditer(text))
    if not matches:
        return [], "failed"

    units: list[dict[str, Any]] = []
    exact_count = 0
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        raw_action_segment = text[start:end]
        leading_ws = len(raw_action_segment) - len(raw_action_segment.lstrip())
        trailing_ws = len(raw_action_segment) - len(raw_action_segment.rstrip())
        action_start = start + leading_ws
        action_end = end - trailing_ws
        action = _clean_labeled_span(raw_action_segment)
        if not action:
            continue
        parsed = _parse_exact_action(action)
        if parsed.get("tool_name") and parsed.get("intent"):
            exact_count += 1
        label_match = re.search(r"\[A\d+\]", text[match.start() : match.end()], re.IGNORECASE)
        label_span = _null_span()
        if label_match:
            label_span = _span(
                match.start() + label_match.start(),
                match.start() + label_match.end(),
            )
        function_name_span = _null_span()
        tool_name = parsed.get("tool_name")
        if tool_name:
            tool_start = text.find(str(tool_name), action_start, action_end)
            if tool_start >= 0:
                function_name_span = _span(tool_start, tool_start + len(str(tool_name)))
        response_spans = {
            "label": label_span,
            "action": _span(action_start, action_end),
            "function_name": function_name_span,
        }
        units.append(
            {
                "unit_id": f"u{len(units) + 1}",
                "think": "",
                "dependency_claims": {},
                "can_think_now": None,
                "needs_prior_observation_for_arguments": None,
                "needs_prior_execution_before_action": None,
                "raw_action": action,
                "source_step": int(match.group("num")),
                "function_name_span": function_name_span,
                "response_spans": response_spans,
                **parsed,
            }
        )
    parse_mode = "exact_name_a" if units and exact_count == len(units) else "a_only"
    return units, parse_mode


def _extract_json_candidate(text: str) -> tuple[str, str]:
    fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL | re.IGNORECASE)
    if fence:
        return fence.group(1).strip(), "json_fragment"
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return text[start : end + 1], "json_fragment"
    raise ValueError("No JSON object found in response")


def _parse_json_units(text: str) -> tuple[list[dict[str, Any]], str | None, str]:
    candidate, parse_mode = _extract_json_candidate(text)
    payload = json.loads(candidate)
    units = payload.get("think_units", []) if isinstance(payload, dict) else payload
    if not isinstance(units, list):
        return [], "think_units must be a list", parse_mode
    normalized: list[dict[str, Any]] = []
    for i, unit in enumerate(units, start=1):
        if not isinstance(unit, dict):
            continue
        raw_action = str(unit.get("action_hint") or unit.get("action") or "")
        parsed = _parse_exact_action(raw_action)
        normalized.append(
            {
                "unit_id": str(unit.get("unit_id") or f"u{i}"),
                "think": "",
                "dependency_claims": {},
                "raw_action": raw_action,
                "source_step": i,
                "function_name_span": _null_span(),
                "response_spans": {
                    "label": _null_span(),
                    "action": _null_span(),
                    "function_name": _null_span(),
                },
                **parsed,
            }
        )
    return normalized, None, parse_mode


def parse_think_units(text: str) -> tuple[list[dict[str, Any]], str | None, str]:
    a_units, parse_mode = _parse_a_labeled(text)
    if a_units:
        return a_units, None, parse_mode

    try:
        return _parse_json_units(text)
    except Exception as exc:
        return [], str(exc), "failed"


if __name__ == "__main__":
    sample = (
        "[A1] Use ls: list visible and hidden files. Known inputs: current directory. "
        "Unresolved inputs: none.\n"
        "[A2] Use get_order_details: retrieve details for the just-placed order. "
        "Known inputs: none. Unresolved inputs: order_id from place_order result."
    )
    units, error, mode = parse_think_units(sample)
    assert error is None
    assert mode == "exact_name_a"
    assert units[0]["tool_name"] == "ls"
    assert units[1]["unresolved_inputs"] == "order_id from place_order result"
    print("parse_units smoke OK")
