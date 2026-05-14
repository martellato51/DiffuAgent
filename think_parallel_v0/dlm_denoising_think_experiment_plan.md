# DLM Denoising 기반 Think Generation 실험 계획

이 문서는 `think_parallel_v0`에서 **지금 바로 해야 할 실험**과 **나중에 확장할 실험**을 분리한다. 핵심 연구 질문은 다음이다.

> LLaDA 같은 DLM은 BFCL에서 strict tool-call format을 잘 맞추지 못하더라도, tool use 직전에 필요한 think/action rationale은 생성할 수 있는가?

그리고 후속 질문은 다음이다.

> 생성된 think/action span의 denoising dynamics 안에 dependency type을 구분할 수 있는 힌트가 있는가?

중요한 원칙: 모델에게 `Strong`, `Weak-D`, `Weak-A`, `Independent`를 직접 맞추게 하지 않는다. 이 label은 ParallelAgent annotation을 이용한 **post-hoc 분석 축**으로만 사용한다.

---

## 1. 현재 구현 상태

현재 `think_parallel_v0`에는 이미 돌아가는 실험 runner가 있다. 현재 active 구현은 **zero-shot `[T][A]` planning-only** 중심이다.

### 구현되어 있는 것

- BFCL multi-turn record 로딩
  - `src/bfcl_data.py`
  - BFCL sample과 ParallelAgent graph/edge JSONL을 읽는다.

- LLaDA generation + denoising trace 수집
  - `src/llada_trace.py`
  - token confidence, commit step, character position 등을 기록한다.

- BFCL schema 기반 prompt 생성
  - `src/prompt_builder.py`
  - 구현된 active mode:
    - `goal_tools_a`
    - `goal_init_tools_a`
    - `both_a`
    - `goal_tools_ta`
    - `goal_init_tools_ta`
    - `both_ta`

- `[T][A]` parser
  - `src/parse_units.py`
  - `[Tn]` / `[An]`을 우선 파싱한다.
  - `[An]`만 있는 action-only output은 `parse_mode="a_only"`로 파싱한다.
  - JSON / `Thought:` / `Action:` parser는 fallback 회수용으로만 남아 있다.

- generated unit과 gold hop matching
  - `src/match_gold.py`
  - `action_hint`와 argument hint를 이용해 ParallelAgent/BFCL gold hop에 매칭한다.

- metric 계산
  - `src/metrics.py`
  - `ta_format_rate`, match rate, tool selection recall, missing/hallucinated action rate, confidence summary 등을 계산한다.

- 전체 runner
  - `src/run_discovery.py`
  - output:
    - `raw_generations.jsonl`
    - `think_units.jsonl`
    - `token_confidence.jsonl`
    - `matched_units.jsonl`
    - `metrics.json`
    - `summary.md`

### 현재 active 실험

첫 번째 연구 질문을 가장 깨끗하게 보기 위한 **P0 `[T][A]` mode**만 active mode로 남겼다.

- `[T1]`, `[A1]`, `[T2]`, `[A2]` planning-only prompt mode
  - `goal_tools_ta`
  - `goal_init_tools_ta`
  - `both_ta`
- `[A1]`, `[A2]`, `[A3]` action-only baseline mode
  - `goal_tools_a`
  - `goal_init_tools_a`
  - `both_a`
- `[Tn]` / `[An]` parser
  - `parse_mode="ta"`로 기록된다.
- `[T]` span과 `[A]` span의 denoising feature extraction
  - 기존 `mean_confidence`, `commit_step_mean`은 `[T]` 기준
  - `action_mean_confidence`, `action_commit_step_mean` 등은 `[A]` 기준
- label prediction이 아니라 post-hoc label stratification에 가까운 main metric
  - `ta_format_rate`
  - `a_only_format_rate`
  - `tool_selection_recall`
  - `missing_action_rate`
  - `hallucinated_action_rate`

제거한 것:

- JSON `think_units` baseline mode
- taxonomy/few-shot JSON mode
- dependency label prediction을 main 실험으로 보는 세팅

이전 JSON parser 코드는 모델 output 회수용 fallback으로만 남긴다.

아직 없는 기능:

- turn-prefix planning setting
- tool-name token / argument-entity token만 따로 분리한 feature
- masking intervention

---

## 2. 지금 해야 할 것

지금 할 일은 범위를 좁힌 **P0: zero-shot `[T][A]` planning-only 실험**이다.

### 목표

LLaDA가 BFCL tool-call format을 못 맞추더라도, 다음을 할 수 있는지 확인한다.

- 필요한 tool-use step을 자연어로 분해한다.
- 각 step의 intended action을 `[A]`로 표현한다.
- strict JSON이나 exact BFCL function-call syntax 없이도 gold tool/hop과 매칭 가능한 output을 낸다.
- 생성된 `[T]`, `[A]` span에서 denoising confidence/commit timing을 뽑을 수 있다.

### 지금은 하지 않을 것

아래는 이번 1차 실험에서 하지 않는다.

- 모델에게 `Strong / Weak-D / Weak-A / Independent` label을 출력하게 하기
- taxonomy 설명을 prompt에 넣기
- few-shot 넣기
- full online BFCL execution 붙이기
- official BFCL score와 직접 비교하기
- 복잡한 intervention이나 masking 실험

이것들을 지금 넣으면, “DLM이 기본적으로 think/action rationale을 만들 수 있는가?”라는 질문이 흐려진다.

---

## 3. 지금 추가할 구현

현재 코드 위에 최소 변경으로 새 mode를 추가했다.

### 새 mode

```text
goal_tools_ta
goal_init_tools_ta
both_ta
goal_tools_a
goal_init_tools_a
both_a
```

의미:

- `goal_tools_ta`: full user goal + BFCL tool schema로 `[T][A]` planning-only output 생성
- `goal_init_tools_ta`: 위 입력에 compact `initial_config` 추가
- `both_ta`: 두 mode 모두 실행
- `goal_tools_a`: full user goal + BFCL tool schema로 `[A]` action-only output 생성
- `goal_init_tools_a`: 위 입력에 compact `initial_config` 추가
- `both_a`: 두 A-only mode 모두 실행

### Prompt

1차 prompt는 zero-shot이다. taxonomy label이나 few-shot은 넣지 않는다.

```text
You are an expert in planning tool use.

You are given a user request and a set of available functions.
Your task is not to call the functions.
Your task is to write a concise planning-only rationale for function use.

Rules:
- Use the exact labels [T1], [A1], [T2], [A2], ...
- A user turn may require multiple tool actions.
- Each [T] must be one short sentence about what needs to be known, decided, or done.
- Each [A] must be one short sentence describing exactly one intended function/tool action.
- If multiple tools are needed, split them into separate [Tn]/[An] pairs.
- Keep the numbering global across the whole request; do not reset at each turn.
- [A] may be natural language or a pseudo-call, but it does not need to match the exact BFCL function-call format.
- Use only the available functions.
- Do not output JSON.
- Do not add a final summary step such as 'the user request is fully planned'.
- Do not include extra text before or after the labeled steps.
- Stop when the user request is fully planned.

User request:
{user_request}

Output:
```

주의: 실제 구현에서는 `{bfcl_function_schemas}`를 user message에 직접 넣지 않는다. BFCL v3의 `system_prompt_pre_processing_chat_model()`이 function schema를 system message에 주입한다.

### A-only baseline prompt

A-only mode는 “think 생성 품질”을 직접 주장하기 위한 실험이 아니다. TA mode에서 `[T]`가 user goal rephrasing이 되는 문제를 분리하고, LLaDA가 exact tool-call format 없이 action plan/tool intent를 회수할 수 있는지 보는 baseline이다.

```text
You are an expert in planning tool use.

You are given a user request and a set of available functions.
Your task is not to call the functions.
Your task is to write a concise action-only plan for tool use.

Rules:
- Use the exact labels [A1], [A2], [A3], ...
- Do not write thoughts, explanations, observations, or final summaries.
- A user turn may require multiple tool actions.
- Each [A] must describe exactly one intended function/tool action.
- If multiple tools are needed, split them into separate [An] lines.
- Keep the numbering global across the whole request; do not reset at each turn.
- When an [A] uses an available function, start the sentence with that exact function name or with 'Use <function_name>'.
- [A] may be natural language or a pseudo-call, but it does not need to match the exact BFCL function-call format.
- Use only the available functions.
- Include only actions needed to satisfy the user request.
- Do not add verification, inspection, or cleanup actions unless the user explicitly asks for them.
- Do not output JSON.
- Do not include extra text before or after the labeled actions.

User request:
{user_request}

Output:
```

비교 해석:

```text
A-only 좋음 + TA의 T가 copy:
  action planning은 가능하지만 generated thought는 약하거나 rephrasing-prone.

A-only도 나쁨:
  think 문제가 아니라 basic action planning부터 약함.

A-only 좋고 TA도 좋음:
  generated think/action rationale 분석으로 넘어갈 수 있음.
```

### 왜 `[A]`가 필요한가

`[T]`만 있으면 gold hop matching이 어렵다.

```text
[T1] I need to check the booking.
```

이 문장은 그럴듯하지만 어떤 BFCL tool에 대응되는지 모호하다.

반면 `[A]`가 있으면 matching anchor가 생긴다.

```text
[T1] I need to find the user's booking.
[A1] Use get_booking with the provided booking id.
```

따라서 `[A]`는 exact tool call이 아니라 **intended action anchor**로 필요하다.

### Parser

`parse_units.py`에 `[T][A]` parser를 추가했다.

입력 예:

```text
[T1] I need to lock all car doors.
[A1] Use lockDoors to lock every car door.
[T2] I need to press the brake before starting the engine.
[A2] Use pressBrakePedal with full pedal position.
```

내부 변환:

```json
{
  "unit_id": "u1",
  "think": "I need to lock all car doors.",
  "action_hint": "Use lockDoors to lock every car door.",
  "arguments_hint": {},
  "parse_mode": "ta",
  "raw_action": "Use lockDoors to lock every car door."
}
```

기존 `match_gold.py`는 `action_hint`를 사용하므로, `[A]`에서 tool name을 최대한 추출한다.

### Metrics

1차 main metric은 label prediction accuracy가 아니다.

우선순위:

1. `ta_format_rate`
   - `[Tn]`, `[An]` 구조를 지켰는가?
2. `tool_selection_recall`
   - 필요한 gold tool을 언급했는가?
3. `action_hint_match_rate`
   - `[A]`가 gold hop에 매칭되는가?
4. `missing_action_rate`
   - 필요한 action을 빠뜨렸는가?
5. `hallucinated_action_rate`
   - 없는 tool/action을 만들었는가?
6. span-level denoising features
   - `[T]` span confidence
   - `[A]` span confidence
   - tool-name token confidence
   - argument entity token confidence
   - commit step mean

ParallelAgent label은 이후 분석에서만 붙인다.

```text
matched generated [T][A] unit
-> gold hop
-> gold edge label from ParallelAgent
-> denoising feature stratification
```

---

## 4. 지금 할 첫 실험

### 실험 이름

```text
P0 Global Planning TA
```

### 입력

```text
Full BFCL multi-turn user goal + BFCL function schemas
```

현재 P0는 **offline global goal** setting이다. BFCL sample의 모든 user turn을 미리 이어 붙여 모델에 준다. 즉 future turn도 포함된다.

형식:

```text
[turn 1] first user request
[turn 2] second user request
...
```

실제 예:

```text
[turn 1] I am alex. Check if the current directory is under my name and list all the visible and hidden contents in the current directory now, please.
[turn 2] Go to workspace directory and move one of the 'log.txt' files into a new directory 'archive'.
[turn 3] Investigate within 'log.txt' for the occurrence of the keyword 'Error'.
[turn 4] Finally, show the last 20 lines the file.
```

prompt 안에서는 아래 위치에 들어간다.

```text
User request:
{full_user_goal}

Output:
```

이 setting은 실제 online multi-turn BFCL execution과 다르다. 목적은 “처음부터 전체 global goal이 주어졌을 때 LLaDA가 meaningful think/action plan을 만들 수 있는가?”를 확인하는 것이다.

기본 schema 제공 방식은 `v3+json`으로 고정한다.

- `BFCL_ROOT`: `unified_envs/gorilla_bfcl_v3/berkeley-function-call-leaderboard`
- `BFCL_FUNCTION_DOC_SERIALIZATION=json`
- 실험 코드는 `DiffuAgent/think_parallel_v0`에서 실행
- 결과는 기본적으로 `DiffuAgent/think_parallel_v0/outputs/<run_name>`에 저장
- BFCL dataset, function schema, prompt utility는 위 `BFCL_ROOT`에서 참조

`v3+json+v4decoder`의 decoder 부분은 현재 planning-only `[T][A]` 출력에서는 사용하지 않는다. 하지만 `v3`와 `v3+json` 차이는 function schema가 system prompt에 보이는 방식이라 main 실험 변수로 중요하다.

### 출력

```text
[T1] ...
[A1] ...
[T2] ...
[A2] ...
```

### 추천 smoke set

```text
multi_turn_base_66
multi_turn_base_187
multi_turn_base_193
multi_turn_base_121
```

### 실행 목표

처음에는 성능 숫자를 크게 믿기보다 다음만 확인한다.

- LLaDA가 `[T][A]` 형식을 대체로 지키는가?
- `[A]`에서 BFCL tool name이 회수되는가?
- gold hop과 어느 정도 매칭되는가?
- `token_confidence.jsonl`에서 `[T]`, `[A]` span별 trace를 뽑을 수 있는가?

이 네 가지가 확인되면 다음 단계로 간다.

---

## 5. 나중에 할 것

아래는 1차 P0 실험이 돌아간 뒤에 한다.

### 5.1 Turn-prefix Planning

연구 질문이 “LLaDA가 멀티턴 환경에서 think 생성이라도 잘하나?”라면, 최종적으로는 이 setting이 더 중요하다.

Global Planning은 future turns를 모두 보여주기 때문에 실제 online multi-turn 환경과 다르다. Turn-prefix Planning은 현재까지의 turn/history만 보여준다.

입력:

```text
turn 1까지의 user/history + BFCL function schemas
turn 2까지의 user/history + BFCL function schemas
...
```

출력:

```text
현재 prefix에서 필요한 [T][A] plan
```

목적:

- 현재까지 주어진 정보만으로 next tool-use rationale을 만들 수 있는지 확인한다.
- Strong/Weak-D처럼 observation이 필요한 dependency가 global setting보다 더 잘 드러날 수 있다.

### 5.2 Few-shot ablation

Main 실험에는 few-shot을 넣지 않는다. 나중에 prompt sensitivity와 upper bound를 보기 위해 추가한다.

| 실험 | Prompt | 목적 |
|---|---|---|
| `P0` | zero-shot `[T][A]` | main sanity check |
| `P1` | BFCL-style few-shot `[T][A]` | tool-use rationale 품질 upper bound |
| `P2` | taxonomy-informed few-shot `[T][A]` | prompt sensitivity |

주의:

- `P2`에서도 label을 출력하게 하지 않는다.
- `Weak-A`라는 단어를 직접 쓰기보다, “plan now, execute after prerequisite” 같은 개념만 예시로 녹인다.

피해야 할 prompt:

```text
Classify each action as Strong, Weak-D, Weak-A, or Independent.
```

### 5.3 Denoising dynamics 분석

P0에서 `[T]`, `[A]` span이 안정적으로 추출되면 다음 feature를 계산한다.

- mean token confidence
- min token confidence
- bottom 10 percent mean confidence
- commit step mean
- first stable step
- span length
- tool-name token confidence
- argument-entity token confidence

그 다음 ParallelAgent label로 post-hoc stratification한다.

질문:

- `Independent` action의 `[A]` span은 더 빠르고 안정적으로 commit되는가?
- `Weak-A` action의 tool/action token은 안정적이지만 sequencing 관련 `[T]` token에서 특징이 나타나는가?
- `Weak-D` action은 tool intent는 안정적이지만 argument token이 늦게 안정되는가?
- `Strong` action은 intent 자체의 confidence가 낮거나 늦게 안정되는가?

### 5.4 Masking intervention

denoising dynamics signal이 보이면 그 다음에 masking intervention을 한다.

예:

- prerequisite `[T]` span masking
- prerequisite `[A]` span masking
- argument entity token masking
- sequencing phrase masking

목적:

- dependency hint가 단순 상관인지, downstream planning quality에 영향을 주는 causal signal인지 확인한다.

---

## 6. 프롬프트 레퍼런스 정리

### BFCL / DiffuAgent에서 가져올 것

- available function schema를 제시하는 방식
- “user request + possible functions를 보고 tool use를 계획한다”는 기본 역할
- function doc preprocessing

### AgentBoard에서 가져올 것

- `Thought -> Action`의 간결한 구조
- 단, `Observation` loop는 가져오지 않는다.
- 원본 AgentBoard prompt를 그대로 쓰지 않는다.

### ParallelAgent에서 가져올 것

- prompt가 아니라 post-hoc analysis 기준
- `Strong / Weak-D / Weak-A / Independent` label
- “order alone is not dependency” 같은 해석 원칙

---

## 7. 한 줄 결론

지금 해야 할 일:

```text
JSON taxonomy prediction 실험을 유지/확장하기보다,
BFCL schema 기반 zero-shot [T][A] planning-only mode만 active로 두고
LLaDA가 meaningful think/action span을 생성하는지 확인한다.
```

나중에 할 일:

```text
생성된 [T][A] span의 denoising dynamics를 ParallelAgent dependency label로 나누어 분석하고,
signal이 보이면 turn-prefix setting과 masking intervention으로 확장한다.
```
