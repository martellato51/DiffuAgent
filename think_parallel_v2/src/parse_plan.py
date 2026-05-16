from __future__ import annotations

import re
from typing import Any


END_PLAN = "<END_PLAN>"
ID_PATTERN = re.compile(r"\$\{?(\d+)\}?")
ACTION_PATTERN = re.compile(
    r"^\s*(?P<idx>\d+)\.\s*(?P<tool>[A-Za-z_][A-Za-z0-9_.]*)\s*\((?P<args>.*)\)\s*$"
)
THOUGHT_PATTERN = re.compile(r"^\s*Thought:\s*(?P<thought>.*)\s*$", re.IGNORECASE)


def _span(start: int, end: int) -> dict[str, int | None]:
    return {"start": start, "end": end}


def _null_span() -> dict[str, int | None]:
    return {"start": None, "end": None}


def _line_offsets(text: str) -> list[tuple[int, str]]:
    offsets: list[tuple[int, str]] = []
    cursor = 0
    for line in text.splitlines(keepends=True):
        offsets.append((cursor, line.rstrip("\r\n")))
        cursor += len(line)
    if text and not text.endswith(("\n", "\r")):
        return offsets
    return offsets


def parse_llmcompiler_plan(
    text: str,
    *,
    valid_tools: set[str] | None = None,
) -> tuple[list[dict[str, Any]], str | None, str]:
    units: list[dict[str, Any]] = []
    errors: list[str] = []
    pending_thought = ""
    seen_end = False

    for line_start, line in _line_offsets(text):
        stripped = line.strip()
        if not stripped:
            continue
        if stripped == END_PLAN or stripped == "<END_OF_PLAN>":
            seen_end = True
            break

        thought_match = THOUGHT_PATTERN.match(line)
        if thought_match:
            thought = thought_match.group("thought").strip()
            pending_thought = (
                f"{pending_thought} {thought}".strip() if pending_thought else thought
            )
            continue

        match = ACTION_PATTERN.match(line)
        if not match:
            continue

        idx = int(match.group("idx"))
        tool_name = match.group("tool")
        args_text = match.group("args").strip()
        deps = sorted({int(item) for item in ID_PATTERN.findall(args_text)})
        action_start = line_start + match.start()
        action_end = line_start + match.end()
        tool_start = line.find(tool_name)
        tool_span = (
            _span(line_start + tool_start, line_start + tool_start + len(tool_name))
            if tool_start >= 0
            else _null_span()
        )
        unit = {
            "unit_id": f"u{len(units) + 1}",
            "node_id": idx,
            "source_step": idx,
            "tool_name": tool_name,
            "args_text": args_text,
            "dependencies": deps,
            "thought": pending_thought,
            "raw_action": stripped,
            "is_valid_tool": None if valid_tools is None else tool_name in valid_tools,
            "response_spans": {
                "action": _span(action_start, action_end),
                "function_name": tool_span,
            },
            "function_name_span": tool_span,
        }
        units.append(unit)
        pending_thought = ""

    node_ids = [unit["node_id"] for unit in units]
    if node_ids != sorted(node_ids):
        errors.append("action ids are not increasing")
    if len(node_ids) != len(set(node_ids)):
        errors.append("action ids are not unique")
    for unit in units:
        for dep in unit["dependencies"]:
            if dep >= unit["node_id"]:
                errors.append(
                    f"action {unit['node_id']} references non-preceding dependency ${dep}"
                )
    if valid_tools is not None:
        invalid = [unit["tool_name"] for unit in units if not unit["is_valid_tool"]]
        if invalid:
            errors.append("invalid tool names: " + ", ".join(sorted(set(invalid))))
    if not seen_end:
        errors.append(f"missing {END_PLAN}")

    parse_mode = "llmcompiler_plan" if units or seen_end else "failed"
    return units, "; ".join(errors) if errors else None, parse_mode


if __name__ == "__main__":
    sample = """Thought: list independent operations first
1. search(query="Ronaldo")
2. search(query="Messi")
3. compare(left=$1, right=${2})
<END_PLAN>
"""
    parsed, error, mode = parse_llmcompiler_plan(sample, valid_tools={"search", "compare"})
    assert error is None
    assert mode == "llmcompiler_plan"
    assert parsed[2]["dependencies"] == [1, 2]
    print("parse_plan smoke OK")
