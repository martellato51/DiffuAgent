# think_parallel_v1 구현 계획

날짜: 2026-05-15

## 1. 목표

`think_parallel_v1`의 목표는 LLaDA가 BFCL에서 strict executable tool-call syntax를
맞추지 못하더라도, BFCL function name을 anchor로 하여 hop 단위 action plan을
생성할 수 있는지 확인하는 것이다.

v1은 action recovery와 matching 안정화까지만 다룬다. Denoising dynamics와
dependency label 분석은 v1 결과가 안정된 뒤 후속 단계에서 진행한다.

## 2. v1 범위

v1에서 사용하는 generation mode는 하나다.

```text
exact_name_a
```

모델 출력 형식:

```text
[A1] Use <exact_function_name>: <intended action>. Known inputs: <known entities/arguments>. Unresolved inputs: <inputs from prior tool results, if any>.
```

v1에서 제외하는 것:

```text
initial_config prompt option
Tool-ID / masked schema prompt
[T]/[A] TA mode
dependency/precomputability status prediction
turn-prefix planning
```

`initial_config`를 제외하는 이유는 현재 P0 질문을 action intent recovery로 좁히기
위해서다. 초기 상태를 넣으면 긴 context 처리, state reading, action planning이
섞여 해석이 흐려질 수 있다.

Tool-ID를 제외하는 이유는 masked schema 설계까지 필요해져서, BFCL-native prompt
reference와 실험 단순성이 약해지기 때문이다.

## 3. Prompt 설계

BFCL v3 JSON function schema injection은 유지한다. 즉 function schema는 user
message에 직접 붙이지 않고, BFCL의 `system_prompt_pre_processing_chat_model()`을
통해 system message에 들어간다.

User prompt는 action-only planning diagnostic이다.

```text
You are an expert in planning tool use.

You are given a user request and a set of available BFCL functions.
Your task is not to call the functions.
Your task is to write a concise action-only plan for tool use.

Output format:
[A1] Use <exact_function_name>: <intended action>. Known inputs: <known entities/arguments>. Unresolved inputs: <inputs from prior tool results, if any>.
[A2] Use <exact_function_name>: <intended action>. Known inputs: <known entities/arguments>. Unresolved inputs: <inputs from prior tool results, if any>.

Rules:
- Use the exact labels [A1], [A2], [A3], ...
- Each [A] must describe exactly one intended function/tool action.
- Use the exact function name from the available function schema.
- Do not output executable BFCL function-call syntax.
- Do not output JSON.
- Do not write thoughts, observations, or final summaries.
- A user turn may require multiple tool actions; split them into separate [An] lines.
- Keep the numbering global across the whole request; do not reset at each turn.
- Include known file names, ids, dates, locations, entities, and literal values when they are stated in the user request.
- If an input must come from a prior tool result, put it in Unresolved inputs instead of inventing a concrete value.
- Use only the available functions.
- Include only actions needed to satisfy the user request.
- Do not add verification, inspection, or cleanup actions unless the user explicitly asks for them.
- Do not include extra text before or after the labeled actions.
```

## 4. Parser

Parser는 `[A]` line에서 다음 필드를 구조화한다.

```json
{
  "unit_id": "u1",
  "parse_mode": "exact_name_a",
  "tool_name": "mv",
  "intent": "move log.txt into archive",
  "known_inputs": "log.txt, archive",
  "unresolved_inputs": "none",
  "raw_action": "Use mv: move log.txt into archive. Known inputs: log.txt, archive. Unresolved inputs: none."
}
```

이 구조는 이후 candidate generation과 LLM judge에 들어간다.

## 5. Candidate Generator

Rule-based matcher는 final matcher가 아니라 high-recall candidate generator로만
사용한다.

후보 생성 기준:

```text
1. exact function name match
2. normalized function name mention
3. Known inputs / intent와 gold hop argument의 lexical overlap
4. same-tool 후보는 첫 번째 hop만 고르지 않고 모두 유지
5. 후보가 없으면 top-k fallback 후보를 넣어 judge가 실패 원인을 드러내게 함
```

기본값:

```text
top_k = 5
```

출력:

```text
judge_candidates.jsonl
```

## 6. LLM-as-Judge 설계

Judge는 generated `[A]` 하나와 candidate gold hop 하나를 pairwise로 비교한다.
Judge가 전체 graph에서 자유롭게 정답 hop을 고르지는 않는다.

ParallelAgent의 judge 설계에서 가져오는 원칙:

```text
1. full user goal과 gold trajectory를 context로 보여준다.
2. candidate hop만 highlight한다.
3. label을 바로 고르게 하지 않고 q1-q4 decision procedure로 쪼갠다.
4. few-shot은 경계 사례를 고정하는 용도로 넣는다.
5. Codex CLI의 output schema를 사용해 JSON을 강제한다.
```

판정 질문:

```text
q1_action_relation:
  exact | semantic | partial | no | unclear

q2_input_relation:
  compatible | partially_compatible | incompatible | unresolved_ok | not_applicable

q3_extra_distinct_action:
  yes | no | unclear

q4_hallucinated_argument:
  yes | no | unclear
```

Derived fields:

```text
candidate_action_covered
single_hop_match
match_strength
confidence
better_hop_hint
reason
```

`match_strength`:

```text
exact
semantic
partial
wrong
not_enough_information
```

Compound는 `match_strength`가 아니라 `single_hop_match=false`로 표현한다.

## 7. Judge Few-Shot

Few-shot은 generation prompt가 아니라 judge prompt에만 들어간다.

### Example 1: exact single-hop match

```text
FULL USER GOAL:
Move log.txt into archive.

GOLD TRAJECTORY:
  h1: mv({"source": "log.txt", "destination": "archive"})  <-- candidate

GENERATED ACTION:
[A1] Use mv: move log.txt into archive. Known inputs: log.txt, archive. Unresolved inputs: none.

EXPECTED:
candidate_action_covered=true
single_hop_match=true
match_strength=exact
```

### Example 2: semantic match without exact function name

```text
FULL USER GOAL:
Show the contents of goals.txt.

GOLD TRAJECTORY:
  h1: cat({"file_name": "goals.txt"})  <-- candidate

GENERATED ACTION:
[A1] Display the contents of goals.txt. Known inputs: goals.txt. Unresolved inputs: none.

EXPECTED:
candidate_action_covered=true
single_hop_match=true
match_strength=semantic
```

### Example 3: unresolved argument is acceptable

```text
FULL USER GOAL:
Place an order, then retrieve the details for the order that was just placed.

GOLD TRAJECTORY:
  h1: place_order({"symbol": "NVDA", "amount": 50})
  h2: get_order_details({"order_id": 12446})  <-- candidate

GENERATED ACTION:
[A2] Use get_order_details: retrieve details for the order just placed. Known inputs: none. Unresolved inputs: order_id from place_order result.

EXPECTED:
candidate_action_covered=true
single_hop_match=true
match_strength=exact
```

### Example 4: compound action

```text
FULL USER GOAL:
Go to workspace and search log.txt for Error.

GOLD TRAJECTORY:
  h1: cd({"folder": "workspace"})  <-- candidate
  h2: grep({"file_name": "log.txt", "pattern": "Error"})

GENERATED ACTION:
[A1] Use cd: enter workspace and search log.txt for Error. Known inputs: workspace, log.txt, Error. Unresolved inputs: none.

EXPECTED:
candidate_action_covered=true
single_hop_match=false
match_strength=exact
```

### Example 5: hallucinated argument / wrong target

```text
FULL USER GOAL:
Cancel the order that was just placed.

GOLD TRAJECTORY:
  h1: place_order({"symbol": "NVDA", "amount": 50})
  h2: cancel_order({"order_id": 12446})  <-- candidate

GENERATED ACTION:
[A2] Use cancel_order: cancel order 99999. Known inputs: order 99999. Unresolved inputs: none.

EXPECTED:
candidate_action_covered=false
single_hop_match=false
match_strength=wrong
```

## 8. Output Files

Generation output:

```text
raw_generations.jsonl
think_units.jsonl
token_confidence.jsonl
generation_metrics.json
summary.md
```

Judge output:

```text
judge_candidates.jsonl
judge_pairwise.jsonl
judge_matches.jsonl
judge_metrics.json
summary.md
```

Judge가 끝나면 `summary.md`는 judge summary로 갱신된다.

## 9. 현재 실험 Input / Process / Output

### 9.1 Input

Generation 단계의 입력은 다음 네 가지다.

```text
1. BFCL sample
   - `category=multi_turn_base`
   - `ids-file=test_case_ids_to_generate_v3.json`
   - 각 sample의 `question`과 `function`을 사용한다.

2. Full user goal
   - sample의 user turn만 모아 `[turn n] ...` 형식으로 concat한다.
   - assistant/tool observation은 포함하지 않는다.
   - `initial_config`도 v1에서는 포함하지 않는다.

3. BFCL function schema
   - sample["function"]을 BFCL v3 preprocessor로 처리한다.
   - `system_prompt_pre_processing_chat_model()`을 통해 system message에 들어간다.

4. LLaDA generation config
   - 예: `LLADA_GEN_LENGTH`, `LLADA_STEPS`, `LLADA_BLOCK_LENGTH`, `LLADA_THRESHOLD`
```

예시 full user goal:

```text
[turn 1] I am alex. Check if the current directory is under my name and list all the visible and hidden contents in the current directory now, please.
[turn 2] Go to workspace directory and move one of the 'log.txt' files into a new directory 'archive'.
[turn 3] Investigate within 'log.txt' for the occurrence of the keyword 'Error'.
[turn 4] Finally, show the last 20 lines the file.
```

Gold graph와 edge는 generation prompt에 들어가지 않는다. Judge 단계에서만
post-hoc matching/evaluation용으로 사용한다.

### 9.2 Process

실험은 두 단계로 분리된다.

```text
Step 1. Generation
  run_llada_discovery.job
    -> prompt 생성
    -> LLaDA generation
    -> raw response 저장
    -> [A] unit parsing
    -> token confidence trace 저장

Step 2. Judge matching
  run_judge_matching.sh
    -> raw_generations.jsonl을 최신 parser로 다시 파싱
    -> candidate gold hop 생성
    -> Codex LLM-as-judge pairwise matching
    -> deterministic resolver
    -> judge metrics 저장
```

Judge가 `raw_generations.jsonl`을 다시 파싱하는 이유는 parser가 개선되더라도 이미
생성한 raw output을 버리지 않고 재평가하기 위해서다.

### 9.3 `raw_generations.jsonl`

한 generation당 한 줄이다. 모델에 들어간 prompt와 raw output을 보존한다.

주요 필드:

| Field | Meaning |
|---|---|
| `question_id` | BFCL sample id |
| `mode` | v1에서는 `exact_name_a` |
| `goal` | full user goal |
| `prompt` | 실제 chat messages. BFCL function schema 포함 |
| `raw_response` | LLaDA가 생성한 원문 |
| `generation_config` | `gen_length`, `steps`, `block_length`, `threshold` 등 |
| `input_tokens` | prompt token 수 |
| `output_tokens` | 생성 block 길이. 현재 구현에서는 보통 `gen_length`와 같다 |

예시 `raw_response`:

```text
[A1] Use ls: List the contents of the current directory. Known inputs: none. Unresolved inputs: none.
[A2] Use mv: Move log.txt to archive. Known inputs: log.txt, archive. Unresolved inputs: none.
```

주의: `output_tokens=128`은 그 자체로 truncation 증거가 아니다. 현재 LLaDA trace
구현은 고정 길이 `gen_length` block을 생성하므로 `output_tokens`는 대개
`gen_length`와 같다. 실제 truncation 여부는 raw text가 중간 문장에서 끊겼는지,
또는 필요한 action이 뒤에서 사라졌는지 별도로 봐야 한다.

### 9.4 `think_units.jsonl`

한 generation당 한 줄이다. `raw_response`를 `[A]` 단위로 파싱한 구조화 결과다.

주요 필드:

| Field | Meaning |
|---|---|
| `parse_mode` | `exact_name_a`, `a_only`, `failed` 등 |
| `parse_error` | parser error. 정상일 때 `null` |
| `units` | parsed action units |

각 unit 예시:

```json
{
  "unit_id": "u2",
  "source_step": 2,
  "tool_name": "mv",
  "intent": "Move log.txt to archive",
  "known_inputs": "log.txt, archive",
  "unresolved_inputs": "none",
  "raw_action": "Use mv: Move log.txt to archive. Known inputs: log.txt, archive. Unresolved inputs: none.",
  "action_hint": "Use mv: Move log.txt to archive",
  "field_spans": {
    "tool_name": {"start": 4, "end": 6},
    "intent": {"start": 8, "end": 34}
  }
}
```

`think_units.jsonl`이라는 이름은 v0와의 호환 때문에 유지한다. v1에는 `[T]`가
없으므로 실제 의미는 "parsed action units"에 가깝다.

### 9.5 `token_confidence.jsonl`

LLaDA denoising trace에서 나온 generated token 단위 정보다. 한 generated token당
한 줄이다.

주요 필드:

| Field | Meaning |
|---|---|
| `position` | generated output 안에서의 token position |
| `token_id` / `token_text` | 생성된 token |
| `confidence` | 해당 token이 commit될 때의 model confidence |
| `commit_step` | denoising 과정에서 token이 확정된 step |
| `block` / `step_in_block` | block-wise generation 내부 위치 |
| `char_start` / `char_end` | decoded raw response 안의 문자 span |

예시:

```json
{
  "question_id": "multi_turn_base_1",
  "mode": "exact_name_a",
  "position": 0,
  "token_text": "[A",
  "confidence": 0.9895,
  "commit_step": 1,
  "char_start": 0,
  "char_end": 2
}
```

이 파일은 judge matching에 직접 쓰지 않는다. 이후 denoising dynamics 분석에서
action span, tool-name span, known-input span, unresolved-input span의 confidence와
commit timing을 집계하기 위한 원자료다.

### 9.6 Judge Output

Judge 단계는 generation이 끝난 뒤 실행한다.

```text
judge_candidates.jsonl
  generated [A] unit별 candidate gold hop 목록

judge_pairwise.jsonl
  generated [A]와 candidate gold hop pair에 대한 Codex judge 원판정

judge_matches.jsonl
  pairwise judge 결과를 deterministic resolver로 정리한 최종 unit-level match

judge_metrics.json
  recall, compound rate, hallucinated argument rate 등 summary metric
```

### 9.7 `Unresolved inputs: [A1]` 해석

`Unresolved inputs: [A1]`는 v1 prompt가 명시적으로 요구한 canonical output은
아니다. 다만 모델이 이전 action result를 짧게 참조하기 위해 이런 표현을 만들 수
있다. 현재 prompt에서는 이 표현을 금지하지 않는다. 지나치게 세밀한 format 제약을
추가하면 BFCL-native action planning이라는 실험 조건이 흐려질 수 있기 때문이다.

더 해석하기 좋은 출력은 다음처럼 prior result를 말로 설명하는 형태다.

```text
Good:
Unresolved inputs: file name from the previous ls result.
Unresolved inputs: order_id from the place_order result.

Not ideal:
Unresolved inputs: [A1].
```

모델이 `[A1]`을 이전 action result의 shorthand처럼 쓸 수 있으므로, parser는 이를
action boundary로 오해하지 않도록 robust하게 처리한다. 구체적으로 줄 시작의
`[A1]`, `[A2]`만 새 action boundary로 보고, field 내부의 `[A1]`는 text reference로
남긴다.

Judge는 문맥상 prior result reference가 분명하면 `unresolved_ok`로 볼 수 있고,
너무 모호하면 `partially_compatible` 또는 `not_enough_information`으로 볼 수 있다.

## 10. Metrics

Main metrics:

| Metric | Definition |
|---|---|
| `format_parse_rate` | output이 parser로 회수 가능한 generation 비율 |
| `candidate_gold_coverage` | gold hop 중 candidate generator 후보에 들어간 비율 |
| `strict_single_action_recall` | `match_strength=exact`이고 `single_hop_match=true`인 gold hop recall |
| `semantic_single_action_recall` | `match_strength in {exact, semantic}`이고 `single_hop_match=true`인 gold hop recall |
| `partial_or_better_recall` | `match_strength in {exact, semantic, partial}`이고 `single_hop_match=true`인 gold hop recall |
| `recall_including_compound` | compound를 포함해 `candidate_action_covered=true`인 gold hop recall |
| `compound_action_rate` | covered action 중 single-hop decomposition에 실패한 generated unit 비율 |
| `hallucinated_argument_rate` | prior result가 필요한 값을 지어낸 generated unit 비율 |
| `unmatched_action_rate` | 어떤 candidate hop에도 covered로 판정되지 않은 generated unit 비율 |

해석:

```text
strict_single_action_recall:
  exact function-name anchored action recovery.

semantic_single_action_recall:
  exact call syntax가 아니어도 action intent가 맞는지 보는 핵심 recall.

recall_including_compound:
  coverage upper bound. Hop을 언급했지만 decomposition이 실패한 경우도 포함한다.
```

## 11. 실행

Generation smoke:

```bash
cd /home/ilju/research/DiffuAgent

RUN_NAME=v1_exact_name_smoke_$(date +%Y%m%d_%H%M%S) \
IDS=multi_turn_base_1 \
MODE=exact_name_a \
bash think_parallel_v1/scripts/run_llada_discovery.job
```

Judge:

```bash
bash think_parallel_v1/scripts/run_judge_matching.sh \
  think_parallel_v1/outputs/$RUN_NAME
```

Summary:

```bash
bash think_parallel_v1/scripts/view_summary.sh \
  think_parallel_v1/outputs/$RUN_NAME
```
