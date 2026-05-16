# Turn-Level LLMCompiler-Style DLM Planning 실험 계획

날짜: 2026-05-15

## 1. 목적

이 실험의 목적은 DLM이 BFCL multi-turn task에서 strict executable tool-call
format을 직접 맞추지 못하더라도, 각 user turn 안에서 필요한 tool-use plan을
LLMCompiler-style planning grammar로 생성할 수 있는지 확인하는 것이다.

더 구체적으로는 다음 질문을 본다.

```text
현재 turn의 user request와 이전 턴의 action/observation context가 주어졌을 때,
DLM은 현재 turn에서 필요한 여러 tool action을 plan으로 생성할 수 있는가?

그리고 그 plan을 생성하는 denoising dynamics는 gold dependency/parallelism과
상관관계를 가지는가?
```

이 실험은 BFCL official multi-turn evaluation이 아니다. BFCL multi-turn data를
turn-level planning problem으로 재구성하여, DLM의 planning 및 denoising behavior를
분석하는 diagnostic experiment이다.

## 2. LLMCompiler에서 차용하는 핵심

LLMCompiler 전체 실행 엔진을 가져오지 않고, planner 쪽 형식과 원칙만 차용한다.

가져오는 것:

```text
1. Given a user query, create a plan with the utmost parallelizability.
2. Each action has a unique, strictly increasing numeric ID.
3. Each action follows Python-style function-call syntax.
4. Inputs can be constants or outputs from previous actions.
5. Previous action outputs may be referenced with $id or $id.field.
6. Use only provided tools/functions.
7. Never introduce new actions/functions.
8. Stop with an explicit end marker.
```

가져오지 않는 것:

```text
1. tool execution
2. Observation generation by executing generated actions
3. join()
4. final answer generation
5. replan loop as implemented in LLMCompiler
6. LangChain Tool executor
```

LLMCompiler 원본에서는 `join()`이 모든 이전 task observation을 모아 final answer를
만드는 trigger 역할을 한다. 이 실험에서는 final answer가 목적이 아니므로 `join()`을
제거하고, 종료 marker로 `<END_PLAN>`만 사용한다.

## 3. 왜 turn-level인가

기존 `think_parallel_v1`은 BFCL multi-turn의 모든 user turns를 concat한 뒤 전체
trajectory action plan을 생성한다.

이 방식은 global trajectory planning 분석에는 좋지만, 다음 문제가 있다.

```text
1. future turn leakage가 있다.
2. 하나의 긴 prompt 안에 여러 turn의 목표가 섞인다.
3. denoising dynamics가 turn 간 순서, coreference, long-context 효과와 섞인다.
4. LLMCompiler의 single-query planner formulation과 거리가 있다.
```

초기 실험에서는 각 turn을 하나의 query로 보고, 그 turn 안에서 필요한 gold hops만
대상으로 plan 생성 능력과 intra-turn parallelism signal을 본다.

이 구조는 LLMCompiler의 기본 형태와 더 가깝다.

```text
one current user query
-> multiple planned actions
-> maximize parallelizability
-> no execution in this diagnostic variant
```

## 4. 이전 턴 정보 처리: Option C, no state summary

turn-level 실험에서 이전 턴 정보는 oracle previous context로 제공한다.

단, state summary는 만들지 않는다. 즉 다음과 같은 요약은 사용하지 않는다.

```text
Known State:
- card_id = "card_123"
- booking_id = "5431449"
```

대신 이전 턴의 user request, gold actions, gold observations를 가능한 한
LLMCompiler replan context와 비슷한 형태로 제공한다.

형식:

```text
Previous Context:

Previous Turn 1:
User: ...
1. previous_action(...)
Observation: ...

Previous Turn 2:
User: ...
2. previous_action(...)
Observation: ...

Current User Turn:
...

Current Plan:
```

이전 context의 목적은 current turn에서 필요한 reference를 해소하는 것이다.
예를 들어 "that booking", "the registered card", "the file just created" 같은 표현을
해결할 수 있어야 한다.

다만 current plan에는 previous actions를 반복하지 않는다.

## 5. 입력 구성

각 BFCL multi-turn sample을 turn 단위 instance로 변환한다.

하나의 training/eval instance는 다음 필드를 가진다.

```json
{
  "question_id": "multi_turn_base_39",
  "turn_index": 1,
  "previous_context": "...",
  "current_user_turn": "...",
  "available_functions": [...],
  "gold_current_hops": [...],
  "gold_current_edges": [...],
  "gold_current_layers": [...]
}
```

`previous_context`에는 turn `< t`의 user text, gold actions, observations가 들어간다.
`current_user_turn`에는 turn `t`의 user text만 들어간다.
`gold_current_hops`는 graph annotation의 `hops[*].turn == t`인 hop만 포함한다.

초기 실험에서는 현재 turn만으로 의미 있는 병렬화 분석이 가능한 turn을 우선 선택한다.

필터:

```text
1. current turn gold hop count >= 2
2. current turn intra-turn antichain pair count >= 1
3. current turn has at least one layer with width >= 2
```

예를 들어 graph annotation의 `turn_bound_layers`에서 같은 turn 안에 병렬 가능한
hop들이 있는 케이스를 우선 사용한다.

## 6. 출력 포맷

출력은 `[A1]` 형식을 쓰지 않고 LLMCompiler-style numeric plan을 사용한다.

기본 포맷:

```text
1. function_name(arg1=value1, arg2=value2)
2. function_name(arg1=value1)
3. function_name(arg_from_previous="$1.field")
<END_PLAN>
```

규칙:

```text
1. Use unique, strictly increasing numeric IDs.
2. Use exact BFCL function names.
3. Use Python-style function-call syntax.
4. Each line must contain exactly one action.
5. Use constants from Current User Turn or Previous Context when available.
6. If an argument must come from a previous action in Current Plan, use $id or $id.field.
7. If an argument must come from Previous Context, use the concrete value from the previous observation when visible.
8. Do not repeat actions already executed in Previous Context.
9. Do not write thoughts, explanations, observations, final answers, JSON, or comments.
10. End with <END_PLAN>.
```

주의: `$id`는 current plan 안의 previous action만 참조한다. Previous Context의 actions는
이미 실행된 것으로 간주하며, 필요한 값이 observation에 보이면 concrete value로 사용한다.

## 7. Prompt Template

LLMCompiler planner prompt를 BFCL turn-level diagnostic에 맞게 수정한다.

```text
Given a user query, create a plan to solve it with the utmost parallelizability.
Each plan should comprise actions from the provided BFCL functions.

You are given Previous Context, which contains previous user turns, previous
actions, and observations. Use Previous Context only to resolve references and
required inputs for the Current User Turn.

Create Current Plan only for the Current User Turn.

Available functions:
{function_descriptions}

Guidelines:
 - Each action described above contains input/output types and description.
 - You must strictly adhere to the input and output types for each action.
 - Each action in the plan should strictly be one of the provided functions.
 - Follow Python-style function-call conventions.
 - Each action MUST have a unique ID, which is strictly increasing.
 - Inputs for actions can either be constants or outputs from preceding actions
   in Current Plan.
 - If an input comes from a preceding action in Current Plan, use $id or $id.field.
 - Ensure the plan maximizes parallelizability.
 - Do not execute the functions.
 - Do not provide observations.
 - Do not provide final answers.
 - Do not repeat actions already executed in Previous Context.
 - Never explain the plan with comments.
 - Never introduce new actions other than the provided functions.
 - Say <END_PLAN> after the final action.

Previous Context:
{previous_context}

Current User Turn:
{current_user_turn}

Current Plan:
```

few-shot examples는 BFCL에서 골라 넣되, generation prompt에는 gold graph label이나
dependency label을 넣지 않는다. gold graph는 post-hoc analysis에만 사용한다.

## 8. 실제 BFCL 예시

BFCL `multi_turn_base_39`에는 다음 흐름이 있다.

```text
[turn 1] create WebDevProjects folder
[turn 2] populate WebDevProjects with styles.css, index.html, script.js
[turn 3] ask for second file name by system order
[turn 4] display content of first file by system order
```

turn 2의 gold hops는 대략 다음과 같다.

```text
cd({"folder": "WebDevProjects"})
touch({"file_name": "styles.css"})
echo({"content": "Hello World!", "file_name": "styles.css"})
touch({"file_name": "index.html"})
echo({"content": "Hi World!", "file_name": "index.html"})
touch({"file_name": "script.js"})
echo({"content": "Halo World!", "file_name": "script.js"})
```

turn 2는 `cd` 이후 여러 file creation/write actions가 병렬 구조를 가진다.

모델이 생성해야 할 Current Plan 예시는 다음과 같다.

```text
1. cd(folder="WebDevProjects")
2. touch(file_name="styles.css")
3. touch(file_name="index.html")
4. touch(file_name="script.js")
5. echo(content="Hello World!", file_name="styles.css")
6. echo(content="Hi World!", file_name="index.html")
7. echo(content="Halo World!", file_name="script.js")
<END_PLAN>
```

여기서 post-hoc gold graph는 `2,3,4`가 같은 layer에 가까운지, `5`가 `2` 이후에
나오는지, denoising commit timing이 그런 구조를 반영하는지 분석하는 데만 사용한다.

## 9. Denoising 분석

generation 단계에서는 DLM trace를 action span과 연결한다.

각 action line에 대해 다음 feature를 계산한다.

```text
action_first_commit_step
action_last_commit_step
action_mean_commit_step
action_median_commit_step
function_name_first_commit_step
function_name_last_commit_step
argument_span_mean_commit_step
reference_token_commit_step
confidence_mean
confidence_min
confidence_std
parse_available_step
```

핵심 분석 질문:

```text
1. current-turn gold layer 0에 해당하는 actions가 layer 1 actions보다 먼저 안정화되는가?
2. 같은 gold layer에 속한 actions는 commit step이 가까운가?
3. dependent pair에서 predecessor action이 successor action보다 먼저 안정화되는가?
4. parallel pair는 dependent pair보다 commit interval overlap이 큰가?
5. hallucinated argument가 있는 generated action은 confidence가 낮거나 late commit이 많은가?
6. generated $id reference가 있는 경우, reference를 포함한 successor action은 predecessor보다 늦게 안정화되는가?
```

## 10. Matching 및 평가

생성된 numeric action line을 gold current-turn hop에 matching한다.

기존 `think_parallel_v1`의 judge matching 구조를 재사용하되, 입력 단위를 `[A]`가 아니라
`1. function(args)` line으로 바꾼다.

평가 지표:

```text
format_parse_rate
current_turn_action_recall
exact_function_name_recall
argument_compatibility_rate
single_action_match_rate
compound_action_rate
hallucinated_argument_rate
unmatched_action_rate
```

parallelism/denoising 지표:

```text
layer_commit_spearman
dependent_pair_order_accuracy
parallel_pair_commit_gap
dependent_pair_commit_gap
parallel_vs_dependent_gap_delta
early_safe_execution_rate
false_early_execution_rate
```

여기서 `early_safe_execution_rate`는 실제 tool execution을 하지 않고 계산한다.
생성 중 특정 action이 parse 가능해진 시점에, gold dependency 기준으로 그 action을
실행해도 되었을지를 counterfactual하게 판단한다.

## 11. 실험 Arm

초기 실험은 최소 세 arm으로 비교한다.

### Arm 1: 기존 A-only plan

기존 `think_parallel_v1` 방식.

```text
[A1] Use tool: ...
```

목적:

```text
DLM이 natural-language action plan을 생성할 수 있는지 확인
```

### Arm 2: LLMCompiler-style numeric plan

새 main setting.

```text
1. tool(args)
2. tool(args)
<END_PLAN>
```

목적:

```text
LLMCompiler-style plan grammar가 DLM planning 분석에 더 적합한지 확인
```

### Arm 3: LLMCompiler-style reference plan

`$id` reference를 명시적으로 허용하거나 요구한다.

```text
1. get_zipcode_based_on_city(_arg0="San Francisco")
2. get_zipcode_based_on_city(_arg0="Silverpine")
3. estimate_distance(cityA="$1.zipcode", cityB="$2.zipcode")
<END_PLAN>
```

목적:

```text
DLM이 dependency를 명시적으로 생성할 수 있는지와,
explicit reference가 denoising dynamics 분석을 강화하는지 확인
```

주의: Arm 3은 dependency를 모델에게 직접 쓰게 하므로, "dependency가 denoising
dynamics에 암묵적으로 드러나는가"라는 질문에는 Arm 2보다 덜 순수하다.

## 12. 구현 단계

### Step 1: turn-level instance builder

BFCL multi-turn sample과 graph annotation을 join한다.

출력:

```text
turn_instances.jsonl
```

각 row:

```json
{
  "question_id": "...",
  "turn_index": 1,
  "previous_context": "...",
  "current_user_turn": "...",
  "gold_hops": [...],
  "gold_layers": [...]
}
```

### Step 2: prompt builder

`prompt_builder.py`에 LLMCompiler-style turn-level mode를 추가한다.

예상 mode:

```text
lc_numeric_turn
lc_ref_turn
```

### Step 3: parser

`parse_units.py`에 numeric action parser를 추가한다.

파싱 대상:

```text
1. function_name(...)
2. function_name(...)
<END_PLAN>
```

출력 필드:

```json
{
  "unit_id": "u1",
  "source_step": 1,
  "raw_action": "function_name(...)",
  "tool_name": "function_name",
  "args_text": "...",
  "references": ["$1"],
  "char_span": [0, 42]
}
```

### Step 4: trace-to-unit feature extraction

`llada_trace.py`의 token commit trace를 parser의 char span과 연결한다.

필요하면 generation 중 intermediate partial text snapshot을 저장한다.
최종 token commit trace만으로 action span feature를 계산할 수 있는지 먼저 확인하고,
부족하면 block/step별 partial decode를 추가한다.

### Step 5: judge matching

`judge_match_outputs.py`를 numeric action format에 맞게 확장한다.

기존 pairwise judge schema는 대부분 유지하되, generated action label만 다음처럼 바꾼다.

```text
GENERATED ACTION:
- unit_id: u1
- text: 1. function_name(...)
```

### Step 6: denoising correlation analysis

별도 script를 추가한다.

예상 파일:

```text
src/analyze_turn_dynamics.py
```

입력:

```text
raw_generations.jsonl
think_units.jsonl
token_confidence.jsonl
judge_matches.jsonl
turn_instances.jsonl
```

출력:

```text
turn_dynamics_metrics.json
turn_dynamics_summary.md
```

## 13. 성공 기준

초기 성공 기준은 official BFCL accuracy가 아니다.

P0 성공 기준:

```text
1. format_parse_rate >= 0.8
2. current_turn_action_recall이 기존 A-only plan과 비슷하거나 더 높음
3. dependent_pair_order_accuracy가 random baseline보다 높음
4. parallel pairs의 commit gap이 dependent pairs보다 작음
5. high-confidence early action 중 dependency violation이 낮음
```

P1 성공 기준:

```text
1. Arm 2 또는 Arm 3가 A-only보다 lower hallucinated_argument_rate를 보임
2. Arm 3에서 generated $id references가 gold dependencies와 유의미하게 일치
3. denoising-implied schedule로 theoretical safe speedup의 일부를 설명 가능
```

## 14. 주요 리스크

### Format burden

`1. tool(args)`는 `[A1] Use ...`보다 엄격하다. DLM이 다시 format을 못 지킬 수 있다.

완화:

```text
1. few-shot을 짧고 강하게 넣는다.
2. `<END_PLAN>`을 명확히 요구한다.
3. parser는 minor syntax variation을 허용한다.
```

### Previous context length

state summary를 쓰지 않으므로 previous actions/observations가 길어질 수 있다.

완화:

```text
1. 초기 실험은 short-context multi_turn_base subset만 사용한다.
2. previous context는 raw initial_config를 넣지 않는다.
3. previous observations는 BFCL execution result만 넣고, verbose object dump는 피한다.
```

### Oracle context

이전 턴 gold actions/observations를 쓰므로 official online BFCL setting과 다르다.

해석:

```text
이 실험은 current-turn planning dynamics를 보기 위한 oracle-context diagnostic이다.
official BFCL score claim과 분리한다.
```

### Dependency leakage

Arm 3의 `$id` reference는 dependency를 explicit하게 생성하게 한다.

해석:

```text
Arm 2는 implicit denoising signal 분석용.
Arm 3은 explicit dependency generation 능력 분석용.
```

## 15. 한 줄 요약

이 실험은 BFCL multi-turn을 turn-level planning problem으로 재구성하고, 이전 턴의
gold action/observation context를 제공하되 state summary는 만들지 않는다. 모델은
LLMCompiler-style `1. tool(args)` plan만 생성하며, tool execution과 join은 제거한다.
생성된 plan과 denoising trace를 current-turn gold graph에 post-hoc matching하여,
DLM의 plan generation dynamics가 intra-turn dependency/parallelism을 반영하는지
측정한다.
