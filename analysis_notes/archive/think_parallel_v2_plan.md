# think_parallel_v2 계획: LLMCompiler-Style Episodic Turn Planning

날짜: 2026-05-15

## 1. 핵심 목표

v2는 v1의 `[A1] Use ...` action-recovery 실험에 종속되지 않는다.
새 실험은 LLMCompiler의 planner formulation을 더 직접적으로 차용한다.

질문:

```text
DLM은 BFCL task에서 각 user turn의 current goal을 보고,
LLMCompiler-style numeric plan을 생성할 수 있는가?

그리고 plan 생성 중 denoising dynamics는 gold dependency / parallelism 구조와
상관관계를 가지는가?
```

이 실험은 official BFCL score를 직접 올리는 실험이 아니다.
BFCL data를 DLM planning diagnostic으로 재구성하는 연구 실험이다.

### 1.1 Two-condition prompt split

prompt condition은 두 개로 분리한다.

```text
Condition A: llmcompiler_explicit_dag
  LLMCompiler-style numeric planner grammar를 유지한다.
  Current-plan dependency는 $id 또는 $id.field로 명시한다.

Condition B: llmcompiler_flat_plan
  Flat numbered action list만 생성한다.
  Action argument 안에서 numbered action을 참조하지 않는다.
  Result-dependent argument는 "<short description>" placeholder로 둔다.
```

기존 `llmcompiler_plan`은 backward-compatible alias로 두고,
실제로는 `llmcompiler_explicit_dag`와 동일하게 처리한다.

이 분리의 목적은 명시적 DAG syntax를 쓰는 LLMCompiler-style reference condition과,
명시적 dependency syntax 없이 denoising dynamics/action-node recovery를 보는
implicit condition을 구분하는 것이다.

## 2. LLMCompiler에서 가져오는 것

LLMCompiler 원본에서 가져오는 핵심은 executor가 아니라 planner grammar다.

가져오는 요소:

```text
1. "Given a user query, create a plan to solve it with the utmost parallelizability."
2. unique, strictly increasing numeric action IDs
3. Python-style action call: 1. tool_name(arg=value)
4. constants or previous action outputs as arguments
5. $id / $id.field reference convention
6. previous plan + observations를 다음 planning context로 쓰는 replan-style context
7. provided functions만 사용
8. explicit end marker
```

제거하는 요소:

```text
1. actual tool execution of generated plan
2. LLMCompiler join()
3. final answer generation
4. LLMCompiler's LangChain executor
5. official online BFCL scoring claim
```

`join()`은 쓰지 않는다. `join()`은 LLMCompiler에서 final answer를 만들기 위한
단계이지만, v2의 관심사는 final answer가 아니라 plan generation dynamics다.
대신 `<END_PLAN>`을 종료 marker로 둔다.

## 3. Replan 아이디어를 이전 턴 context로 재해석

LLMCompiler의 replan은 같은 question에서 이전 plan 실행 결과를 보고 다음 plan을
만드는 구조다.

원본 replan context는 개념적으로 다음과 같다.

```text
Previous Plan:

1. action(...)
Observation: ...

Thought: ...

Current Plan:
```

v2에서는 이것을 BFCL multi-turn의 이전 턴 정보로 재해석한다.

```text
Previous Turns:

Turn 1 User:
...
Previous Plan:
1. action(...)
Observation: ...

Turn 2 User:
...
Previous Plan:
1. action(...)
Observation: ...

Current Turn User:
...

Current Plan:
```

즉, LLMCompiler의 replan context를 "same-query replanning"이 아니라
"episodic multi-turn planning context"로 사용한다.

중요한 결정:

```text
state summary는 사용하지 않는다.
```

이전 턴에서 생긴 상태를 별도로 요약하지 않는다.
대신 이전 턴의 user text, gold previous actions, raw tool observations만 제공한다.

사용하지 않는 예:

```text
Known State:
- booking_id = "5431449"
- card_id = "card_123"
```

사용하는 예:

```text
Turn 1 User:
Register my card ...

Previous Plan:
1. register_credit_card(...)
Observation: {"card_id": "card_123"}
```

## 4. Multi-turn을 쓰는 방식: turn sampling 금지, full task episode 유지

v2에서 multi-turn을 사용할 경우, task 안의 일부 turn만 샘플링하지 않는다.

대신 하나의 BFCL multi-turn sample을 온전한 episode로 사용한다.

실행 방식:

```text
for each selected BFCL multi-turn task:
    for turn t in task turns:
        build Previous Context from turns < t
        ask DLM to generate Current Plan for turn t only
        store generated plan and denoising trace
    evaluate the full task episode after all turns
```

따라서 generation 단위는 turn이지만, dataset/evaluation 단위는 full task다.

이 방식의 장점:

```text
1. LLMCompiler처럼 current query에 대한 plan을 만든다.
2. BFCL multi-turn의 task coherence를 보존한다.
3. future turn leakage를 피한다.
4. 이전 턴 action/observation context를 replan-style로 활용한다.
5. turn별 denoising signal과 full-task dependency graph를 모두 분석할 수 있다.
```

## 5. 데이터 확인 결과

BFCL v3 local data를 직접 확인했다.

파일 위치:

```text
DiffuAgent/unified_envs/gorilla_bfcl_v3/berkeley-function-call-leaderboard/bfcl_eval/data
```

주요 category:

```text
BFCL_v3_multiple.json
BFCL_v3_parallel.json
BFCL_v3_parallel_multiple.json
BFCL_v3_multi_turn_base.json
BFCL_v3_multi_turn_miss_param.json
BFCL_v3_multi_turn_miss_func.json
BFCL_v3_multi_turn_long_context.json
```

요약:

```text
multiple:
  200 tasks
  avg gold calls = 1.0
  거의 전부 단일 function call
  parallel/dependency dynamics 분석에는 부적합

parallel:
  200 tasks
  avg gold calls = 2.69
  min/max = 2/8
  single-turn independent parallel calls
  format sanity와 independent parallel action 분석에 적합

parallel_multiple:
  200 tasks
  avg gold calls = 3.04
  min/max = 2/5
  여러 function을 single turn에서 독립 호출
  parallel보다 function diversity가 좋아 P0에 적합

multi_turn_base:
  200 raw tasks
  avg turns = 3.73
  avg calls/task = 5.8
  turn>=2 calls가 있는 tasks = 168
  turn>=3 calls가 있는 tasks = 76
  full-task episodic planning에 적합

multi_turn_miss_param / miss_func:
  missing parameter/function behavior가 섞임
  v2 초기 main set에는 confound가 크다

multi_turn_long_context:
  long-context stress가 섞임
  일부 task는 30+ calls
  초기 실험보다는 후속 stress test에 적합
```

ParallelAgent annotation도 확인했다.

```text
ParallelAgent/data/annotations/bfcl_graphs.jsonl
```

`multi_turn_base` graph rows:

```text
n = 108
avg n_hops = 5.61
avg critical_path = 3.36
avg parallel_width = 2.63
tasks with parallel_width >= 2 = 92
tasks with intra-turn antichain pairs > 0 = 38
tasks with turn_bound_max_width >= 2 = 38
```

따라서 v2 main multi-turn set은 raw 200개 전체보다,
graph annotation이 있고 intra-turn parallelism이 있는 `multi_turn_base` subset에서
시작하는 것이 좋다.

좋은 예시:

```text
multi_turn_base_65:
  n_hops = 9
  parallel_width = 4
  intra-turn antichain pairs = 17
  turn 1 안에 liter_to_gallon, check_tire_pressure, lockDoors,
  pressBrakePedal 등이 병렬 가능

multi_turn_base_39:
  n_hops = 10
  parallel_width = 4
  intra-turn antichain pairs = 12
  WebDevProjects 안에서 여러 파일 생성/쓰기 actions가 병렬 구조를 가짐

multi_turn_base_69:
  n_hops = 9
  parallel_width = 5
  intra-turn antichain pairs = 10
  distance estimation branch와 fuel conversion branch가 같은 turn 안에 공존

multi_turn_base_18:
  n_hops = 9
  parallel_width = 5
  intra-turn antichain pairs = 7
  mkdir 이후 여러 cp actions가 병렬 가능

multi_turn_base_63:
  n_hops = 10
  parallel_width = 6
  intra-turn antichain pairs = 7
  vehicle setup actions와 later distance branch를 분석하기 좋음
```

## 6. 추천 데이터 전략

v2는 두 단계로 간다.

### P0: Single-turn format and parallel sanity

데이터:

```text
BFCL_v3_parallel
BFCL_v3_parallel_multiple
```

목적:

```text
1. DLM이 LLMCompiler-style `1. tool(args)` format을 지킬 수 있는지 확인
2. 여러 independent actions를 빠뜨리지 않고 생성하는지 확인
3. independent parallel calls의 denoising timing이 서로 가까운지 확인
```

이 단계에서는 dependency chain이 거의 없으므로 dependent-pair order hypothesis는
강하게 보지 않는다.

### P1: Full-task episodic multi-turn planning

데이터:

```text
BFCL_v3_multi_turn_base
plus graph annotations from ParallelAgent/data/annotations/bfcl_graphs.jsonl
```

선택 조건:

```text
category == multi_turn_base
n_intra_turn_antichain_pairs > 0
turn_bound_max_width >= 2
graph annotation exists
```

예상 task 수:

```text
38 full tasks
```

중요: 이 38개에서 특정 turn만 잘라 쓰지 않는다.
각 task의 모든 turns를 episode로 실행한다.

### P2: Stress / ablation

후속으로만 사용:

```text
multi_turn_long_context
multi_turn_miss_param
multi_turn_miss_func
```

이들은 context length, missing parameter, missing function이라는 별도 confound가 있어
v2 main claim에는 섞지 않는다.

## 7. Previous Context 생성

BFCL에는 gold multi-turn actions를 실제 environment에 replay해 tool result를 얻는
코드가 이미 있다.

참고:

```text
bfcl_eval/scripts/visualize_multi_turn_ground_truth_conversation.py
bfcl_eval/eval_checker/multi_turn_eval/multi_turn_utils.py::execute_multi_turn_func_call
```

해당 스크립트는 turn별로 다음 로그를 만든다.

```text
assistant: ground_truth action
tool: execution_result
state_info: current object state
```

v2에서는 `state_info`를 사용하지 않는다.

사용:

```text
assistant action
tool observation
```

제외:

```text
state_info
initial_config raw dump
state summary
```

Previous Context 예시:

```text
Previous Turns:

Turn 1 User:
I need you to set up a fresh folder named 'WebDevProjects' wherever you're currently working.

Previous Plan:
1. mkdir(dir_name="WebDevProjects")
Observation: ...

Current Turn User:
Enter the folder and populate the 'WebDevProjects' folder with 3 files...

Current Plan:
```

## 8. Generation Prompt

LLMCompiler prompt를 BFCL v2에 맞게 수정한다.

```text
Given a user query, create a plan to solve it with the utmost parallelizability.
Each plan should comprise actions from the provided BFCL functions.

You are given Previous Context, which contains previous user turns, previous
actions, and observations. Use Previous Context only to resolve references and
required inputs for the Current User Turn.

Create Current Plan only for the Current User Turn.
Do not repeat actions already executed in Previous Context.

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
 - If an input is visible in Previous Context observations, use the concrete value.
 - Ensure the plan maximizes parallelizability.
 - Do not execute the functions.
 - Do not provide observations.
 - Do not provide final answers.
 - Never explain the plan with comments.
 - Never introduce new actions other than the provided functions.
 - Say <END_PLAN> after the final action.

Previous Context:
{previous_context}

Current User Turn:
{current_user_turn}

Current Plan:
```

## 9. 출력 포맷

기본 arm:

```text
1. function_name(arg1=value1, arg2=value2)
2. function_name(arg1=value1)
<END_PLAN>
```

reference arm:

```text
1. get_zipcode_based_on_city(_arg0="San Francisco")
2. get_zipcode_based_on_city(_arg0="Rivermist")
3. estimate_distance(cityA="$1.zipcode", cityB="$2.zipcode")
<END_PLAN>
```

주의:

```text
$id reference는 Current Plan 안에서만 사용한다.
Previous Context의 값은 observation에 보이면 concrete value로 사용한다.
```

## 10. 평가 단위

generation row는 turn 단위로 저장하지만, primary report는 task episode 단위로 묶는다.

저장 row:

```json
{
  "question_id": "multi_turn_base_39",
  "turn_index": 1,
  "prompt": [...],
  "raw_response": "...",
  "units": [...],
  "trace_tokens": [...]
}
```

episode report:

```json
{
  "question_id": "multi_turn_base_39",
  "n_turns": 4,
  "turn_results": [...],
  "task_action_recall": 0.8,
  "task_dependency_order_accuracy": 0.75,
  "task_parallel_gap_delta": -3.2
}
```

## 11. Metrics

Plan quality:

```text
format_parse_rate
exact_function_name_recall
current_turn_action_recall
task_action_recall
argument_compatibility_rate
unmatched_action_rate
compound_action_rate
hallucinated_argument_rate
```

Denoising / dependency:

```text
function_name_commit_step
action_first_commit_step
action_last_commit_step
action_mean_commit_step
parse_available_step
confidence_mean
dependent_pair_order_accuracy
parallel_pair_commit_gap
dependent_pair_commit_gap
parallel_vs_dependent_gap_delta
layer_commit_spearman
false_early_execution_rate
```

Confidence trace 해석:

```text
token_confidence.jsonl의 confidence는 token이 최종 commit된 순간의
selected-token softmax probability다.

현재 저장되는 것은 commit된 token row뿐이다.
같은 output position의 per-step confidence history,
confidence delta / slope,
commit 전 top-k 변화는 저장하지 않는다.
```

Aggregation 기준:

```text
block_confidence_mean:
  token_confidence rows를 block으로 groupby한 confidence 평균.
  서로 다른 token들이 각자 commit된 순간의 confidence 평균이며,
  같은 token의 trajectory 평균이 아니다.

action_span_confidence:
  plan_units.response_spans.action과 token char_start/char_end가 겹치는
  token rows의 confidence 평균.

function_name_span_confidence:
  plan_units.response_spans.function_name과 겹치는 token rows의 confidence 평균.
```

추가 trace가 필요하면 action/function/$id span에 해당하는 output positions에 대해
매 denoising step의 top-1 token, top-1 confidence, committed 여부를 저장한다.

Full-task coherence:

```text
episode_completion_rate
turns_with_valid_plan_rate
no_repeat_previous_action_rate
cross_turn_reference_resolution_rate
```

## 12. 분석 가설

P0 single-turn:

```text
1. parallel/parallel_multiple에서 DLM은 multiple independent actions를 numeric plan으로 생성할 수 있다.
2. 같은 independent set의 actions는 denoising commit timing이 서로 가깝다.
```

P1 multi-turn full task:

```text
1. current turn의 gold layer 0 actions가 later layer actions보다 먼저 안정화된다.
2. dependent pair에서는 predecessor action이 successor action보다 먼저 안정화된다.
3. parallel pair는 dependent pair보다 commit gap이 작다.
4. 이전 context observation에 등장한 concrete value는 hallucination보다 더 안정적으로 생성된다.
5. 이전 턴 actions를 반복하지 않는 능력은 Previous Context formatting에 민감하다.
```

## 13. 구현 항목

새 디렉터리:

```text
DiffuAgent/think_parallel_v2/
```

예상 파일:

```text
src/build_v2_instances.py
src/prompt_builder_v2.py
src/parse_lc_plan.py
src/run_v2_generation.py
src/match_v2_outputs.py
src/analyze_v2_dynamics.py
scripts/run_v2_llada.job
scripts/run_v2_analysis.sh
```

구현 순서:

```text
1. BFCL category별 data profiler 고정
2. P0 parallel/parallel_multiple instance builder
3. LLMCompiler-style numeric prompt builder
4. numeric plan parser
5. LLaDA generation + token trace 저장
6. P0 metrics
7. multi_turn_base full-task episode builder
8. gold previous action replay로 Previous Context 생성
9. state_info 제거
10. full-task episodic generation
11. gold graph matching
12. denoising dynamics 분석
```

## 14. 성공 기준

P0:

```text
format_parse_rate >= 0.8
exact_function_name_recall >= v1 A-only baseline 근처
parallel/parallel_multiple에서 평균 generated actions가 gold calls에 근접
```

P1:

```text
multi_turn_base selected full tasks에서 episode_completion_rate >= 0.7
dependent_pair_order_accuracy > random baseline
parallel_pair_commit_gap < dependent_pair_commit_gap
no_repeat_previous_action_rate 높음
```

## 15. 현재 판단

데이터 선택 결론:

```text
1. multiple은 v2 핵심 실험 데이터로 쓰지 않는다.
   단일 call이 대부분이라 plan/parallel dynamics에 약하다.

2. parallel + parallel_multiple을 P0 format sanity로 쓴다.
   single-turn independent actions라 가장 단순하다.

3. multi_turn_base를 P1 main set으로 쓴다.
   단, turn sampling이 아니라 full-task episode를 유지한다.

4. multi_turn_miss_param, multi_turn_miss_func, long_context는 P2로 미룬다.
   각각 missing information과 long context confound가 있다.
```

한 줄 요약:

```text
think_parallel_v2는 LLMCompiler의 replan-style previous plan/observation context를
BFCL multi-turn 이전 턴 context로 재해석하고, full-task episode 안에서 매 turn마다
LLMCompiler-style numeric Current Plan을 생성하게 한다. 초기 sanity는
parallel/parallel_multiple로 보고, main diagnostic은 intra-turn parallelism이 있는
multi_turn_base full tasks에서 수행한다.
```
