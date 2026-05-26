# BFCL Think Parallel v0

이 디렉터리는 BFCL multi-turn 문제에서 LLaDA가 **정확한 tool-call 포맷**을 맞추지 못하더라도, **tool use를 위한 think/action plan**은 만들 수 있는지 확인하기 위한 실험 코드입니다.

현재 실험은 `v3+json` function schema를 사용한 zero-shot planning-only 실험으로 좁혔습니다. 기본은 `[T][A]` mode이고, `[T]`가 user goal rephrasing이 되는 문제를 분리하기 위한 `[A]`-only action-planning baseline도 제공합니다.

```text
Experiment root: /home/ilju/research/DiffuAgent/think_parallel_v0
Default research root: /home/ilju/research
BFCL data / prompt utility: unified_envs/gorilla_bfcl_v3
Function schema serialization: BFCL_FUNCTION_DOC_SERIALIZATION=json
Default mode: both_ta
Shared env: /home/ilju/research/DiffuAgent/env.sh
```

## 유지 범위

이전 JSON `think_units` baseline과 taxonomy/few-shot mode는 active 실험에서 제거했습니다.

이유:

- 지금의 질문은 “dependency label을 맞히는가?”가 아니라 “LLaDA가 tool-use think/action span을 만들 수 있는가?”입니다.
- JSON baseline은 예전 코드와 비교하는 데는 쓸 수 있지만, 현재 P0 실험의 독립변수를 늘립니다.
- taxonomy prompt는 모델에게 `Strong`, `Weak-D`, `Weak-A`, `Independent`를 직접 알려주는 방향이라 denoising dynamics를 post-hoc으로 보려는 목적과 섞입니다.

단, `parse_units.py`에는 JSON/ReAct fallback parser가 남아 있습니다. 이것은 실험 mode가 아니라, 모델이 `[T][A]` 형식을 어겼을 때 output을 일부 회수하기 위한 보조 코드입니다.

## 구현된 파일

```text
think_parallel_v0/
├── README.md
├── dlm_denoising_think_experiment_plan.md
├── scripts/
│   ├── run_llada_discovery.job
│   └── view_summary.sh
└── src/
    ├── bfcl_data.py        # BFCL record, graph/edge loader, full goal/config summary 생성
    ├── llada_trace.py      # LLaDA generation + token confidence trace 수집
    ├── match_gold.py       # generated action_hint를 gold BFCL hop에 매칭
    ├── metrics.py          # parse/match/confidence metric 계산
    ├── parse_units.py      # [T][A] parser + JSON/ReAct fallback
    ├── prompt_builder.py   # BFCL schema 기반 [T][A] prompt 생성
    ├── reevaluate_outputs.py # 기존 output을 새 matcher/metric으로 재평가
    └── run_discovery.py    # 전체 runner
```

## 구현된 Mode

현재 `run_discovery.py --mode`에서 선택 가능한 mode는 아래 6개입니다.

| Mode | 출력 형식 | 입력 | 용도 |
|---|---|---|---|
| `goal_tools_ta` | `[T][A]` | full user goal + BFCL function schema | 초기 환경 없이 planning-only 생성 |
| `goal_init_tools_ta` | `[T][A]` | full user goal + initial_config summary + BFCL function schema | 초기 환경까지 포함 |
| `both_ta` | `[T][A]` | 위 두 TA mode 모두 실행 | 기본값 |
| `goal_tools_a` | `[A]` | full user goal + BFCL function schema | action-only baseline |
| `goal_init_tools_a` | `[A]` | full user goal + initial_config summary + BFCL function schema | initial_config 포함 action-only baseline |
| `both_a` | `[A]` | 위 두 A-only mode 모두 실행 | action-planning baseline 비교 |

## Full User Goal

full user goal은 [bfcl_data.py](/home/ilju/research/DiffuAgent/think_parallel_v0/src/bfcl_data.py:33)의 `join_user_goal(sample["question"])`에서 만듭니다.

BFCL sample의 `question`은 turn들의 list입니다.

```python
question = [
    [{"role": "user", "content": "..."}],
    [{"role": "user", "content": "..."}],
]
```

현재 구현은 각 turn에서 `role == "user"`인 message의 `content`만 모읍니다. assistant/tool message는 full goal 생성에 쓰지 않습니다.

결과 문자열:

```text
[turn 1] first user request
[turn 2] second user request
...
```

실제 `multi_turn_base_1` 예:

```text
[turn 1] I am alex. Check if the current directory is under my name and list all the visible and hidden contents in the current directory now, please.
[turn 2] Go to workspace directory and move one of the 'log.txt' files into a new directory 'archive'.
[turn 3] Investigate within 'log.txt' for the occurrence of the keyword 'Error'.
[turn 4] Finally, show the last 20 lines the file.
```

이 문자열은 user message의 아래 위치에 그대로 들어갑니다.

```text
User request:
{full_user_goal}

Output:
```

한 turn 안에 user message가 여러 개 있으면 같은 turn 아래에서 newline으로 합칩니다. 즉 현재 실험은 “현재까지의 prefix”가 아니라 BFCL record 안의 모든 user turn, future turn 포함, 을 한 번에 이어 붙인 **offline global goal**을 봅니다.

중요한 해석:

- 모델은 전체 multi-turn request를 처음부터 모두 본 상태에서 planning합니다.
- 따라서 이 setting은 실제 online BFCL execution처럼 turn-by-turn으로 새 user request를 받는 환경이 아닙니다.
- 이 setting은 “global goal이 주어졌을 때 LLaDA가 coarse/subtask-level think/action plan을 만들 수 있는가?”를 보는 P0 sanity check입니다.

## Initial Config

`initial_config`는 BFCL sample 안에 들어있는 초기 환경 상태입니다. multi-turn 문제에서 파일, 예약 상태, 메시지 상태, DB-like state, 앱 내부 state 같은 실행 환경의 시작 상태를 담을 수 있습니다.

현재 구현에서는 `sample.get("initial_config", {})`로 읽습니다. 값이 없으면 빈 dict `{}`로 처리합니다.

`initial_config`는 `goal_init_tools_ta`에만 들어갑니다. `both_ta`는 `goal_tools_ta`와 `goal_init_tools_ta`를 둘 다 실행하므로 initial_config 포함/미포함을 같은 샘플에서 비교할 수 있습니다.

요약 문자열은 [bfcl_data.py](/home/ilju/research/DiffuAgent/think_parallel_v0/src/bfcl_data.py:57)의 `summarize_initial_config()`에서 만듭니다.

처리 방식:

- dict/list를 재귀적으로 순회합니다.
- `{"type": "file", "content": ...}` 형태의 file node는 `content`를 최대 300자로 자릅니다.
- 전체 config를 `json.dumps(..., ensure_ascii=False, sort_keys=True)`로 문자열화합니다.
- 전체 문자열이 5000자를 넘으면 5000자에서 자르고 `...<truncated>`를 붙입니다.

prompt에는 아래 heading으로 들어갑니다.

```text
Initial environment configuration summary:
{compact_json}
```

## Function Schema

function schema는 `sample["function"]`에서 가져옵니다.

[prompt_builder.py](/home/ilju/research/DiffuAgent/think_parallel_v0/src/prompt_builder.py:56)에서 BFCL 전처리를 적용합니다.

```python
functions = func_doc_language_specific_pre_processing(
    copy.deepcopy(sample["function"]), category
)
```

그 다음 BFCL의 `system_prompt_pre_processing_chat_model()`을 호출해 system prompt 맨 앞에 function 목록을 붙입니다.

```python
messages = system_prompt_pre_processing_chat_model(messages, functions, category)
```

현재 job 기본값은 [run_llada_discovery.job](/home/ilju/research/DiffuAgent/think_parallel_v0/scripts/run_llada_discovery.job:17) 기준:

```text
BFCL_ROOT=${RESEARCH_ROOT}/DiffuAgent/unified_envs/gorilla_bfcl_v3/berkeley-function-call-leaderboard
BFCL_FUNCTION_DOC_SERIALIZATION=json
IDS_FILE=${BFCL_ROOT}/test_case_ids_to_generate_v3.json
CATEGORY=multi_turn_base
OUTPUT_DIR=${EXPERIMENT_ROOT}/outputs/${RUN_NAME}
```

따라서 기본 실행은 `v3+json`입니다. BFCL v3 prompt utility를 쓰고, function docs는 pretty JSON 문자열로 system prompt에 들어갑니다.

sample id는 기본적으로 BFCL v3의 `test_case_ids_to_generate_v3.json`에서 `multi_turn_base` 목록을 읽습니다. 현재 이 목록은 50개 sample입니다. `IDS=...`를 명시하면 `IDS_FILE`보다 우선하므로 smoke test나 일부 sample 재실행이 가능합니다.

`v3+json+v4decoder`에서 decoder 부분은 현재 `[T][A]` planning-only 출력에서는 사용하지 않습니다. 하지만 `v3`와 `v3+json` 차이는 모델이 보는 function schema 형식이 달라지는 것이므로 현재 실험에도 중요합니다.

## 최종 Prompt 구조

모델에는 chat message 2개가 들어갑니다.

### 1. system message

BFCL v3의 기본 system prompt가 먼저 들어갑니다. 요지는 다음과 같습니다.

```text
You are an expert in composing functions. You are given a question and a set of possible functions...
You should only return the function calls in your response.
...
Here is a list of functions in JSON format that you can invoke.
{pretty_json_function_schema}
```

그 뒤에 이 실험의 override가 같은 system message 끝에 붙습니다.

```text
Diagnostic override: this run is not BFCL action execution.
Ignore any earlier instruction that says to return only executable function calls.
Use the function documentation only as the available action schema.
Return only labeled planning lines in the form [T1], [A1], [T2], [A2], ...
Do not return JSON and do not return executable BFCL function calls.
```

BFCL 기본 prompt에는 “function call만 출력하라”는 문장이 있기 때문에, 이 override가 필요합니다. override가 뒤에 붙으므로 현재 실험에서는 `[T][A]` planning-only 지시가 최종 지시입니다. function schema는 user message에 직접 넣지 않고, BFCL v3의 system prompt preprocessing을 통해 system message에 주입됩니다.

### 2. user message: `goal_tools_ta`

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
- When an [A] uses an available function, start the sentence with that exact function name or with 'Use <function_name>'.
- [A] may be natural language or a pseudo-call, but it does not need to match the exact BFCL function-call format.
- Use only the available functions.
- Do not output JSON.
- Do not add a final summary step such as 'the user request is fully planned'.
- Do not include extra text before or after the labeled steps.
- Stop when the user request is fully planned.

User request:
{full_user_goal}

Output:
```

### 3. user message: `goal_init_tools_ta`

`goal_tools_ta`와 같고, `User request` 뒤에 initial_config 요약이 추가됩니다.

```text
User request:
{full_user_goal}

Initial environment configuration summary:
{compact_initial_config_json}

Output:
```

### 4. user message: `goal_tools_a`

A-only mode는 `[T]` 생성 품질을 직접 주장하기 위한 실험이 아닙니다. TA mode에서 `[T]`가 user goal rephrasing이 되는 문제를 분리하고, exact BFCL tool-call format 없이 action intent를 회수할 수 있는지 보는 baseline입니다.

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
{full_user_goal}

Output:
```

System override도 TA와 다릅니다.

```text
Return only labeled action-plan lines in the form [A1], [A2], [A3], ...
Do not return thoughts, JSON, or executable BFCL function calls.
```

### 5. user message: `goal_init_tools_a`

`goal_tools_a`와 같고, `User request` 뒤에 initial_config 요약이 추가됩니다.

```text
User request:
{full_user_goal}

Initial environment configuration summary:
{compact_initial_config_json}

Output:
```

## `[T][A]` Prompt 판단

현재 prompt는 P0 sanity check용으로 적절합니다.

좋은 점:

- taxonomy label을 주지 않아서 post-hoc denoising 분석을 오염시키지 않습니다.
- strict BFCL function-call format을 요구하지 않아서 tool-call formatting 문제와 planning 문제를 분리합니다.
- `[A]`가 있어서 gold BFCL hop과 matching할 anchor가 생깁니다.
- 한 user turn 안에 여러 tool action이 필요한 경우에도 여러 `[Tn]/[An]` unit으로 쪼개도록 하므로, turn 단위가 아니라 subtask/function-hop 단위 분석에 맞습니다.
- `Use only the available functions`와 function-name 시작 규칙이 있어 hallucination과 matching 실패를 줄입니다.

주의할 점:

- BFCL system prompt와 `[T][A]` override가 충돌하므로, raw prompt 확인은 항상 필요합니다.
- `[A]`는 exact tool call이 아니므로 argument accuracy는 아직 약한 지표입니다.
- `[A]`가 여러 tool을 한 문장에 합치는 compound action이면, 이것은 hop-level 분해 실패로 해석해야 합니다.
- 현재는 offline global goal이므로 실제 online multi-turn 능력을 직접 측정하지는 않습니다.

## `[A]`-only Prompt 판단

A-only mode의 해석은 TA와 다릅니다.

```text
A-only 좋음 + TA의 T가 copy:
  action planning은 가능하지만 generated thought는 약하거나 rephrasing-prone.

A-only도 나쁨:
  think 문제가 아니라 basic action planning부터 약함.

A-only 좋고 TA도 좋음:
  generated think/action rationale 분석으로 넘어갈 수 있음.
```

A-only에서 주로 볼 지표:

- `a_only_format_rate`
- `tool_selection_recall`
- `compound_action_rate`
- `missing_action_rate`
- `hallucinated_action_rate`
- `labels.*.action_mean_confidence`

## 실행

기본 BFCL v3 `multi_turn_base` subset 실행:

```bash
cd /home/ilju/research/DiffuAgent

MODE=both_ta \
bash think_parallel_v0/scripts/run_llada_discovery.job
```

Smoke test처럼 한 sample만 실행:

```bash
cd /home/ilju/research/DiffuAgent

IDS=multi_turn_base_66 \
MODE=both_ta \
bash think_parallel_v0/scripts/run_llada_discovery.job
```

여러 샘플:

```bash
IDS=multi_turn_base_66,multi_turn_base_187,multi_turn_base_193,multi_turn_base_121 \
MODE=both_ta \
bash think_parallel_v0/scripts/run_llada_discovery.job
```

A-only smoke test:

```bash
IDS=multi_turn_base_1 \
MODE=both_a \
bash think_parallel_v0/scripts/run_llada_discovery.job
```

주요 환경변수:

| 변수 | 기본값 | 의미 |
|---|---|---|
| `RESEARCH_ROOT` | `/home/ilju/research` | `DiffuAgent`, `ParallelAgent`, `Fast-dLLM`, `model`의 parent |
| `BFCL_ROOT` | `${RESEARCH_ROOT}/DiffuAgent/unified_envs/gorilla_bfcl_v3/berkeley-function-call-leaderboard` | BFCL checkout |
| `BFCL_FUNCTION_DOC_SERIALIZATION` | `json` | v3 function schema 직렬화 방식 |
| `LLADA_THRESHOLD` | `0.9` | 공용 `DiffuAgent/env.sh`에서 설정되는 LLaDA threshold |
| `IDS` | unset | 직접 실행할 BFCL sample id. 설정하면 `IDS_FILE`보다 우선 |
| `IDS_FILE` | `${BFCL_ROOT}/test_case_ids_to_generate_v3.json` | `IDS`가 없을 때 category별 sample id 목록을 읽는 파일 |
| `CATEGORY` | `multi_turn_base` | BFCL category |
| `MODE` | `both_ta` | 실행 mode |
| `GRAPHS` | `${RESEARCH_ROOT}/ParallelAgent/data/annotations/bfcl_graphs.jsonl` | ParallelAgent graph annotation |
| `EDGES` | `${RESEARCH_ROOT}/ParallelAgent/data/annotations/bfcl_edges.jsonl` | ParallelAgent edge annotation |
| `OUTPUT_DIR` | `${EXPERIMENT_ROOT}/outputs/${RUN_NAME}` | 결과 저장 위치 |

## 결과 파일

기본 결과는 아래에 저장됩니다.

```text
${EXPERIMENT_ROOT}/outputs/${RUN_NAME}/
```

| 파일 | 내용 |
|---|---|
| `raw_generations.jsonl` | prompt, raw response, generation config, `bfcl_function_doc_serialization` |
| `think_units.jsonl` | parser가 회수한 units, `parse_mode`, `parse_error` |
| `token_confidence.jsonl` | token별 confidence, commit step, char span |
| `matched_units.jsonl` | generated unit과 gold BFCL hop 매칭 결과 |
| `metrics.json` | 전체 metric과 run metadata |
| `summary.md` | 사람이 빠르게 볼 요약 |

## 해석

main metric:

| Metric | 의미 |
|---|---|
| `ta_format_rate` | `[T][A]` 형식으로 파싱된 generation 비율 |
| `a_only_format_rate` | `[A]`-only 형식으로 파싱된 generation 비율 |
| `match_rate` / `action_hint_match_rate` | generated unit이 gold hop에 매칭된 비율 |
| `tool_selection_recall` | gold hop 중 생성 plan이 커버한 비율 |
| `missing_action_rate` | gold hop 중 빠진 비율 |
| `hallucinated_action_rate` | generated unit 중 gold hop에 매칭되지 않은 비율 |
| `compound_action_rate` | 하나의 `[A]` 안에 여러 tool/action이 들어간 비율 |
| `labels.*.mean_confidence` | gold dependency label별 `[T]` span confidence |
| `labels.*.action_mean_confidence` | gold dependency label별 `[A]` span confidence |

## 주의

- 현재 실험은 global goal을 한 번에 주는 offline setting입니다.
- 실제 online multi-turn turn-prefix setting은 아직 구현되어 있지 않습니다.
- `bfcl_graphs.jsonl`, `bfcl_edges.jsonl`는 prompt에 들어가지 않고 post-hoc evaluation에만 쓰입니다.
- `LLADA_THINK_DIAGNOSTIC`는 BFCL handler의 online `<think>` diagnostic이고, 이 디렉터리의 offline 실험과는 별도입니다.
- `think_parallel_v0`는 production BFCL handler나 AgentBoard 원본 prompt를 수정하지 않는 독립 실험 디렉터리입니다.

## 현재 Smoke Result 해석

아래 run을 기준으로 현재 상태를 점검했습니다.

```text
think_parallel_v0/outputs/llada_think_parallel_20260514_085531
sample: multi_turn_base_1
mode: both_ta
```

명령어:

```bash
cd /home/ilju/research/DiffuAgent

python think_parallel_v0/src/reevaluate_outputs.py \
  --output-dir think_parallel_v0/outputs/llada_think_parallel_20260514_085531

bash think_parallel_v0/scripts/view_summary.sh \
  think_parallel_v0/outputs/llada_think_parallel_20260514_085531
```

### 관찰

format 측면:

```text
ta_format_rate = 1.0
format_parse_rate = 1.0
```

즉 LLaDA는 `[T1]`, `[A1]`, `[T2]`, `[A2]` 형식 자체는 안정적으로 따릅니다.

관대한 coverage matcher로 재평가하면 match metric은 다음처럼 바뀝니다.

```text
goal_tools_ta:
  matched = 4 / 4 units
  tool_selection_recall = 0.833
  missing_action_rate = 0.167
  compound_action_rate = 0.250

goal_init_tools_ta:
  matched = 5 / 5 units
  tool_selection_recall = 1.000
  missing_action_rate = 0.000
  compound_action_rate = 0.400
```

이 결과는 `Use ls ...`, `Use cd ... Use mv ...` 같은 자연어 action sentence에서 tool name을 추출하고, compound action 안의 여러 gold hop을 coverage match로 인정한 결과입니다.

따라서 현재 해석은 다음처럼 나눕니다.

```text
coverage 관점:
  필요한 tool-use intent는 꽤 많이 언급한다.

granularity 관점:
  하나의 [A]에 여러 tool을 합치는 compound action이 남아 있다.
```

### Granularity 문제

더 중요한 관찰은 `[T]/[A]` unit의 granularity입니다.

현재 LLaDA 출력은 대체로 subtask/function-hop 단위라기보다 user turn instruction 단위에 가깝습니다.

예:

```text
[T2] Go to the workspace directory and move one of the 'log.txt' files into a new directory 'archive'.
[A2] Use cd to navigate to the workspace directory. Use mv to move one of the 'log.txt' files into the 'archive' directory.
```

gold graph에서는 이것이 별도 hop입니다.

```text
h2: cd({"folder": "workspace"})
h3: mv({"source": "log.txt", "destination": "archive"})
```

따라서 현재 모델은 하나의 `[A]` 안에 여러 function action을 합치는 compound action을 만들고 있습니다.

이것은 P0 질문을 두 단계로 나누게 합니다.

```text
Q1. LLaDA가 meaningful tool-use think/action text를 생성하는가?
    현재 관찰: 어느 정도 yes.

Q2. LLaDA가 think/action을 subtask/function-hop 단위로 분해하는가?
    현재 관찰: 아직 weak / suboptimal.
```

### Think Parallel과의 관계

think parallel 분석의 이상적인 단위는 user turn이 아니라 subtask/function-hop입니다.

```text
one [Tn]/[An] pair ~= one executable subtask or one BFCL gold hop
```

이 단위가 맞아야 다음 분석이 가능합니다.

- 각 hop의 `[T]` confidence
- 각 hop의 `[A]` confidence
- tool-name token stability
- argument token stability
- commit step
- ParallelAgent edge label별 post-hoc stratification

반대로 현재처럼 `cd + mv`가 하나의 `[A]`에 합쳐지면, `mv`가 `cd`에 의존하는지, 두 action이 병렬 가능한지, 각각의 denoising confidence가 어떻게 다른지를 분리해서 보기 어렵습니다.

따라서 현재 결과는 다음처럼 해석합니다.

```text
LLaDA can produce coarse tool-use rationale,
but not yet clean hop-level think/action decomposition.
```

즉 완전 실패라기보다, think parallel을 하려면 먼저 **granularity alignment** 문제가 있다는 초기 진단입니다.

### Matcher 해석 기준

현재 matcher는 “think/action intent를 생성했는가?”를 보기 위해 관대하게 동작합니다.

예:

```text
[A2] Use cd to navigate to the workspace directory. Use mv to move log.txt into archive.
```

이 경우:

```text
coverage:
  cd, mv를 모두 gold hop과 match로 인정

granularity:
  compound_action=True
```

즉 compound action은 coverage 실패가 아니라 **granularity warning**입니다.

### 다음 판단

우선순위:

1. matcher 결과 확인
   - `matched_hop_ids`는 coverage를 봅니다.
   - `compound_action=True`는 hop-level decomposition 실패를 봅니다.
   - `compound_action_rate`는 think parallel 분석 단위가 얼마나 깨지는지 보는 지표입니다.

2. prompt sensitivity 확인
   - 현재 prompt는 이미 “one action per `[A]`”를 요구하지만, zero-shot LLaDA가 완전히 따르지는 않았습니다.
   - 더 강한 structural instruction을 넣을지, 또는 P0 결과로 coarse granularity를 기록할지 결정합니다.

3. 해석 기준
   - `ta_format_rate`는 모델이 형식을 지켰는지 보는 지표입니다.
   - match 계열 metric은 action intent coverage로 해석합니다.
   - compound action 비율은 hop-level decomposition 실패 지표로 봅니다.
