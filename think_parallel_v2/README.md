# think_parallel_v2

BFCL v3 `multi_turn_base`를 대상으로, DLM/LLaDA가 **현재 user turn의 global goal을 보고 LLMCompiler-style parallel/dependency plan을 생성할 수 있는지** 확인하는 실험이다.

이 코드는 official BFCL function-call score를 올리기 위한 runner가 아니다. BFCL 데이터를 사용하지만, 목적은 tool call 정확도 자체보다 다음 질문을 진단하는 것이다.

```text
DLM은 exact BFCL tool-call format을 완벽히 지키지 못하더라도,
LLMCompiler식 plan grammar 안에서 병렬 가능한 subtask와 dependency를 드러낼 수 있는가?

그리고 그 plan 생성 과정의 denoising dynamics는
gold DAG의 parallel/dependency 구조와 상관관계를 가지는가?
```

## 현재 고정 입력

현재 실험에 필요한 BFCL graph/edge JSONL은 생성되어 있다. v2 generation runner가 직접 사용하는 파일은 episode-level `*_graphs.jsonl`이다.

```text
graph:
  /home/ilju/research/ParallelAgent/data/annotations/bfcl_v3_think_parallel_multi_turn_base_graphs.jsonl

edge labels:
  /home/ilju/research/ParallelAgent/data/annotations/bfcl_v3_think_parallel_multi_turn_base_edges.jsonl
```

확인된 graph 상태:

```text
graph_available:
  200 episodes
  745 turns

intra_turn_parallel:
  73 episodes
  240 turns
```

주의: `*_edges.jsonl`은 per-edge judge/label 분석용이고, `--graphs-path`에는 넣지 않는다. `--graphs-path`에는 항상 `*_graphs.jsonl`을 넣는다.

## 현재 실행 구조

v2는 이제 두 단계로 나눈다.

```text
prepare stage:
  BFCL records + possible_answer + function docs + graphs 로드
  episode filtering
  gold observation replay
  turn별 prompt 생성
  prepared prompts JSONL 저장

generation stage:
  prepared prompts JSONL만 읽음
  LLaDA generation
  plan parsing
  token confidence trace 저장
```

반복 실험에서는 prepare stage를 매번 다시 할 필요가 없다. prompt template, function doc serialization, episode filter, graph 파일이 바뀌지 않았다면 prepared prompts를 재사용한다.

## Two-Condition Prompt Split

v2는 prompt condition을 둘로 분리한다.

```text
Condition A: llmcompiler_explicit_dag
  LLMCompiler-style explicit DAG condition.
  Current-plan dependency가 있으면 $id 또는 $id.field로 표현한다.

Condition B: llmcompiler_flat_plan
  Flat numbered action list condition.
  Action argument 안에서 numbered action을 참조하지 않는다.
  Result-dependent argument는 "<short description>" placeholder string으로 둔다.
```

기존 `llmcompiler_plan` mode는 backward-compatible alias이며 내부적으로 `llmcompiler_explicit_dag`와 동일하게 처리된다.

권장 prepared/output 경로:

```text
explicit prepared:
  prepared/multi_turn_base_intra_turn_parallel_explicit_prompts.jsonl

flat prepared:
  prepared/multi_turn_base_intra_turn_parallel_flat_prompts.jsonl

explicit output:
  outputs/llada_multiturn_base_explicit

flat output:
  outputs/llada_multiturn_base_flat
```

실행 예:

```bash
MODE=llmcompiler_explicit_dag \
bash /home/ilju/research/DiffuAgent/think_parallel_v2/scripts/prepare_multiturn_base_prompts.sh

MODE=llmcompiler_flat_plan \
bash /home/ilju/research/DiffuAgent/think_parallel_v2/scripts/prepare_multiturn_base_prompts.sh

MODE=llmcompiler_explicit_dag \
bash /home/ilju/research/DiffuAgent/think_parallel_v2/scripts/run_multiturn_base_llada.sh

MODE=llmcompiler_flat_plan \
bash /home/ilju/research/DiffuAgent/think_parallel_v2/scripts/run_multiturn_base_llada.sh
```

## 실제 run 전 환경 조건

실제 LLaDA run은 다음 환경이 준비되어 있어야 한다.

```text
1. BFCL executor dependency가 설치된 Python environment
2. LLaDA/Fast-dLLM backend import 경로
3. LLaDA model checkpoint
4. GPU/CUDA 메모리
```

v2는 v1의 traceable LLaDA backend를 재사용한다.

```text
think_parallel_v1/src/llada_trace.py
```

주요 환경 변수:

```text
FAST_DLLM_LLADA_PATH
  default: /home/ilju/research/Fast-dLLM/v1/llada

LLADA_MODEL_PATH
  from /home/ilju/research/DiffuAgent/env.sh
  default on this server: /data/ilju/LLaDA-8B-Instruct

LLADA_DTYPE
  default: bfloat16

LLADA_MAX_MEMORY
  optional device memory map

LLADA_STEPS
LLADA_GEN_LENGTH
LLADA_BLOCK_LENGTH
LLADA_CONTEXT_LENGTH
LLADA_ENFORCE_CONTEXT
LLADA_TRUNCATE_INPUT
```

현재 v2의 새 실행 default는 official BFCL multiturn LLaDA reference와 맞추기 위해 다음으로 고정한다.

```text
LLADA_GEN_LENGTH=128
LLADA_STEPS=128
LLADA_BLOCK_LENGTH=32
LLADA_THRESHOLD=0.9
```

주의: 과거 완료 run인 `outputs/llada_multiturn_base`는 기록상 `LLADA_GEN_LENGTH=256`, `LLADA_STEPS=128`, `LLADA_BLOCK_LENGTH=32`였다. 이 old output은 그대로 reference result로 보되, 지금부터 새로 제출하는 v2 smoke/full jobs는 `128/128/32` 기준으로 비교한다.

BFCL gold observation replay는 실제 BFCL tool implementation을 import하고 실행한다. 따라서 BFCL 추론이 돌아가던 동일한 environment에서 실행하는 것이 좋다.

v2 scripts는 먼저 다음 공통 env 파일을 source한다.

```text
/home/ilju/research/DiffuAgent/env.sh
```

현재 shell이 `(base)`여도 scripts는 기본적으로 `env.sh`의 `LLADA_PYTHON`을 사용한다.

```text
/home/ilju/miniconda3/envs/llada8b/bin/python
```

다른 env를 쓰고 싶으면 `PYTHON_BIN`을 지정한다. 다른 모델 weight를 쓰고 싶으면 `LLADA_MODEL_PATH`를 지정한다.

```bash
PYTHON_BIN=/home/ilju/miniconda3/envs/llada2.1/bin/python \
bash /home/ilju/research/DiffuAgent/think_parallel_v2/scripts/prepare_multiturn_base_prompts.sh
```

예를 들어 BFCL repo의 dependency에는 다음이 포함된다.

```text
mpmath==1.3.0
tree_sitter==0.21.3
tree-sitter-java==0.21.0
tree-sitter-javascript==0.21.4
```

final run에서는 gold observation replay가 실패하면 안 된다. `--allow-gold-replay-errors`는 prompt 모양을 보는 smoke test용이다.

## 실험 목적

v1은 `[A1] Use ...` 형식으로 action unit을 뽑고, 나중에 gold hop과 matching하는 구조였다.

v2 Condition A는 더 직접적으로 LLMCompiler를 reference로 삼는다.

```text
v1:
  [A1] Use tool_name: natural-language action
  explicit DAG grammar 없음

v2 Condition A:
  1. tool_name(arg=value)
  2. another_tool(input=$1.some_field)
  <END_PLAN>
  $id reference로 dependency 표현 가능

v2 Condition B:
  1. tool_name(arg=value)
  2. another_tool(input="<needed value from first action>")
  <END_PLAN>
  explicit dependency reference 없이 flat action nodes만 표현
```

핵심은 DLM에게 “정답 tool call을 내라”보다 약간 완화된 목표를 주는 것이다. 즉, DLM이 exact BFCL answer format에는 약하더라도, **어떤 tool action들이 필요하고, 어떤 것들이 서로 독립이며, 어떤 것들이 이전 결과를 기다려야 하는지**를 plan grammar 안에서 드러내는지 본다.

## LLMCompiler에서 차용한 부분

LLMCompiler 원본의 planner에서 가져온 핵심은 executor가 아니라 **planning interface**다.

차용한 요소:

```text
1. "create a plan ... with the utmost parallelizability"
2. numeric action IDs: 1., 2., 3.
3. unique, strictly increasing IDs
4. Python-style tool syntax: tool_name(arg=value)
5. current-plan dependency reference: $id 또는 ${id}
6. provided tools/functions만 사용
7. previous plan + Observation context
8. explicit end marker
```

Condition A prompt의 기본 출력 형식은 다음과 같다.

```text
Thought: <optional one-line strategy>
1. tool_name(arg=value)
2. tool_name(arg=$1.some_field)
<END_PLAN>
```

`$id`는 optional이다. 독립 action이면 쓰지 않는다. 현재 plan 안의 이전 action 결과가 필요할 때만 쓴다.

예:

```text
1. get_zipcode_based_on_city(city="San Francisco")
2. get_zipcode_based_on_city(city="Rivermist")
3. estimate_distance(cityA=$1.zipcode, cityB=$2.zipcode)
<END_PLAN>
```

여기서 1과 2는 병렬 가능하고, 3은 1과 2에 dependent하다.

Condition B prompt의 기본 출력 형식은 다음과 같다.

```text
Thought: <optional one-line strategy>
1. get_zipcode_based_on_city(city="San Francisco")
2. get_zipcode_based_on_city(city="Rivermist")
3. estimate_distance(cityA="<zipcode for San Francisco>", cityB="<zipcode for Rivermist>")
<END_PLAN>
```

B에서는 runtime prompt에 explicit dependency syntax 예시를 노출하지 않는다. 대신 필요한 action node는 유지하고, 아직 실행 결과가 필요한 argument는 angle-bracket placeholder로 둔다. 이 조건의 목적은 explicit DAG grammar 없이 denoising order와 action-node recovery만으로 parallel/dependency signal을 볼 수 있는지 확인하는 것이다.

## LLMCompiler에서 바꾼 부분

LLMCompiler를 BFCL + DLM diagnostic에 그대로 쓰지는 않는다. 다음 부분은 의도적으로 바꿨다.

```text
1. join() 제거
2. generated plan의 실제 tool execution 제거
3. final-answer joiner LLM 제거
4. LangChain executor/scheduler 제거
5. BFCL official answer wrapper 제거
6. replan을 BFCL previous-turn context로 재해석
7. state_info / initial_config raw dump / state summary를 prompt에서 제외
```

`join()`을 쓰지 않는 이유는 이 실험의 관심사가 final answer aggregation이 아니기 때문이다. 우리는 “join 전의 plan 구조”와 “DLM denoising dynamics”를 보고 있다. 그래서 종료 marker는 `<END_PLAN>`만 사용한다.

현재 prompt는 LLMCompiler-style planner grammar를 참조하되, BFCL official answer wrapper는 사용하지 않는다. 즉 system prompt는 BFCL runner의 `[func(...)]` 출력 지시를 재사용하지 않고, function docs와 compact planning contract만 제공한다.

핵심 objective:

```text
Given the current user turn, create the minimal sufficient tool-use plan to solve it.
Use only necessary actions.
Among those actions, maximize parallelizability by adding dependencies only when an input truly requires a current-plan result.
```

이 순서를 둔 이유는 `utmost parallelizability`만 강조하면 불필요한 helper action을 많이 생성해 generated width가 과대평가될 수 있기 때문이다. v2에서는 **먼저 필요한 최소 action set을 고르고, 그 안에서 parallelizability를 최대화**한다.

Condition A compact output contract:

```text
- Output only Thought, numbered actions, and <END_PLAN>; no observations, answers, comments, JSON, or list-style answer wrappers.
- Each action must be one provided function using exact schema parameter names.
- Do not wrap arguments in arg= unless the function schema contains a parameter named arg.
- IDs start at 1 and strictly increase within the Current Plan.
- Inputs may be constants, concrete values from Previous Turns/Observations, or current-plan references like $1 or $1.field.
- Use $id only for actions in the Current Plan. If using $id.field, field must appear in that tool's response schema.
- Independent actions must not reference each other.
- Do not repeat previous-turn actions unless the current user explicitly asks to perform them again.
- Use functions at their documented granularity; do not add helper actions unless their outputs are needed for the current turn.
- Do not call join().
```

Condition B compact output contract는 위와 대부분 같지만 다음 차이가 있다.

```text
- Inputs may be constants, concrete values from Previous Turns/Observations, or short angle-bracket placeholder strings.
- Do not refer to numbered actions inside arguments.
- If an argument requires a value produced by another Current Plan action, use a short angle-bracket placeholder string instead.
- Keep all necessary action nodes visible even when using placeholders.
```

LLMCompiler의 replan context는 원래 같은 query에서 이전 plan 실행 결과를 보고 다음 plan을 만드는 구조다.

v2에서는 이것을 BFCL multi-turn에 맞게 다음처럼 바꾼다.

```text
LLMCompiler:
  Previous Plan + Observation
  Current Plan

think_parallel_v2:
  Completed Previous Turns:
    Turn 1 User
    Previous Plan: gold calls from turn 1
    Observation: gold tool observations from turn 1

    Turn 2 User
    Previous Plan: gold calls from turn 2
    Observation: gold tool observations from turn 2

  Current Turn User
  Current Plan
```

Previous-turn Observations는 read-only context다. 현재 plan output에서 `Observation:` line을 새로 생성하면 안 된다.

## BFCL + DLM 적용을 위한 v2 개선점

LLMCompiler의 아이디어를 BFCL/DLM 실험에 맞게 쓰기 위해 v2에서 추가한 구현상 개선점은 다음과 같다.

```text
1. BFCL multi-turn을 turn sampling하지 않고 full episode로 유지
2. 이전 turn 전체를 oracle previous context로 제공
3. 이전 turn context를 gold call + gold observation으로 구성
4. current turn의 gold answer는 prompt에서 제외
5. generated plan은 실행하지 않고 symbolic plan으로만 저장
6. Condition A의 $id reference를 parser에서 dependency로 구조화
7. action/function span을 저장해서 token confidence trace와 연결 가능하게 함
8. gold DAG graph_stats를 각 turn output에 붙여 post-hoc 분석 가능하게 함
9. DLM token commit trace를 `token_confidence.jsonl`로 저장
10. graph-based episode filter를 제공
```

이 변경 덕분에 BFCL official scoring이 아니라 다음 연구 질문에 맞는 데이터가 나온다.

```text
generated plan node
generated $id dependency
gold DAG turn layer
gold intra-turn antichain pair
DLM token commit step
```

이 다섯 가지를 같은 `question_id`, `turn_index`, response span 기준으로 연결할 수 있다.

## 입력 데이터

### 1. BFCL user turns

경로:

```text
/home/ilju/research/DiffuAgent/unified_envs/gorilla_bfcl_v3/berkeley-function-call-leaderboard/bfcl_eval/data/BFCL_v3_multi_turn_base.json
```

형태:

```json
{
  "id": "multi_turn_base_0",
  "question": [
    [{"role": "user", "content": "turn 1 user request"}],
    [{"role": "user", "content": "turn 2 user request"}]
  ],
  "initial_config": {},
  "path": ["GorillaFileSystem.cd", "..."],
  "involved_classes": ["GorillaFileSystem"]
}
```

`question`이 multi-turn user query다. v2는 이 안의 turn을 따로 샘플링하지 않는다. 하나의 BFCL task를 full episode로 유지한다.

### 2. BFCL gold calls

경로:

```text
/home/ilju/research/DiffuAgent/unified_envs/gorilla_bfcl_v3/berkeley-function-call-leaderboard/bfcl_eval/data/possible_answer/BFCL_v3_multi_turn_base.json
```

형태:

```json
{
  "id": "multi_turn_base_0",
  "ground_truth": [
    ["cd(folder='document')", "mkdir(dir_name='temp')"],
    ["grep(file_name='final_report.pdf', pattern='budget analysis')"]
  ]
}
```

`ground_truth[t]`는 `question[t]`에 대응하는 gold tool calls다.

중요한 점:

```text
현재 turn의 gold call은 prompt에 넣지 않는다.
현재 turn의 gold call은 output metadata와 post-hoc 평가에만 사용한다.
```

### 3. BFCL function docs

경로:

```text
/home/ilju/research/DiffuAgent/unified_envs/gorilla_bfcl_v3/berkeley-function-call-leaderboard/bfcl_eval/data/multi_turn_func_doc/*.json
```

`involved_classes`를 보고 필요한 function docs를 붙인다.

예:

```text
GorillaFileSystem -> gorilla_file_system.json
MathAPI           -> math_api.json
TwitterAPI        -> posting_api.json
VehicleControlAPI -> vehicle_control.json
```

이 function docs는 system prompt에 들어간다. 모델은 이 목록에 있는 function만 plan에 사용할 수 있다.

### 4. Graph JSONL

예상 경로:

```text
/home/ilju/research/ParallelAgent/data/annotations/bfcl_v3_think_parallel_multi_turn_base_graphs.jsonl
```

각 row는 하나의 BFCL episode에 대한 graph record다.

v2가 기대하는 주요 field:

```text
question_id
pattern
n_hops
critical_path
parallel_width
turn_bound_max_width
n_intra_turn_antichain_pairs
hops
```

`hops` 안에는 최소한 다음 정보가 있어야 한다.

```json
{
  "id": "h1",
  "question_raw": "tool_name({...})",
  "depends_on": [],
  "turn": 0
}
```

graph는 prompt에 넣지 않는다. graph는 다음 용도로만 쓴다.

```text
1. episode filtering
2. turn별 gold hop 통계 저장
3. post-hoc plan/DLM-denoising 분석
```

## Prompt에 들어가지 않는 것

다음 세 가지는 의도적으로 prompt에서 제외한다.

```text
1. state_info
2. initial_config raw dump
3. state summary
```

`state_info`는 BFCL visualization script에서 gold tool 실행 후 내부 API instance state를 덤프할 때 쓰는 디버깅 role이다.

`initial_config raw dump`는 BFCL 원본의 초기 환경 전체다. 파일 시스템 tree, Twitter state, vehicle state 같은 것이 들어 있다.

`state summary`는 우리가 설계 중에 고려했던 파생 아이디어다. 예를 들어 “현재 directory는 temp다” 같은 요약을 따로 만들어 prompt에 넣을 수 있지만, v2에서는 쓰지 않는다.

v2에서 이전 상태는 오직 다음 경로로만 전달된다.

```text
previous user text
previous gold calls
previous gold observations
```

이렇게 한 이유는 LLMCompiler의 `Previous Plan + Observation` 구조에 최대한 가깝게 맞추기 위해서다.

## 작동 과정

prepare entrypoint:

```text
src/prepare_prompts.py
```

prepare stage에서 한 번 수행하는 흐름:

```text
1. BFCL user records 로드
2. possible_answer gold calls를 id 기준으로 merge
3. involved_classes에 맞는 BFCL function docs 로드
4. graph JSONL 로드
5. episode 단위로 filtering
6. 각 episode를 full multi-turn episode로 유지
7. gold calls를 실제 BFCL executor로 replay하여 gold observations 생성
8. 각 turn에 대해 prompt 생성
9. prepared prompts JSONL로 저장
```

generation entrypoint:

```text
src/run_discovery.py
```

generation stage에서 반복 수행하는 흐름:

```text
1. prepared prompts JSONL 로드
2. DLM/LLaDA로 Current Plan 생성
3. generated plan을 parser로 구조화
4. raw generation, parsed units, token confidence trace 저장
```

### Episode filtering

지원하는 filter:

```text
all
graph_available
intra_turn_parallel
multi_hop
```

권장 final setting:

```text
--episode-filter intra_turn_parallel
```

이 filter는 다음 조건을 만족하는 full episode만 고른다.

```text
turn_bound_max_width >= 2
n_intra_turn_antichain_pairs > 0
```

즉, episode 안의 적어도 한 turn에서 실제로 병렬 가능한 gold hop pair가 있어야 한다.

주의:

```text
filtering은 episode 단위다.
generation은 선택된 episode의 모든 turn에 대해 수행한다.
metric에서 병렬성 분석에 들어갈 turn만 따로 마스킹한다.
```

### Gold observation replay

파일:

```text
src/bfcl_data.py
```

함수:

```text
replay_gold_observations(...)
```

이 함수는 BFCL의 executor를 사용한다.

```text
bfcl_eval/eval_checker/multi_turn_eval/multi_turn_utils.py
execute_multi_turn_func_call(...)
```

각 turn의 gold calls를 실제로 실행해서 observation string을 얻는다.

예:

```text
gold call:
  cd(folder='document')

observation:
  {"current_working_directory": "document"}
```

이 observation은 현재 turn prompt가 아니라, 이후 turn의 previous context에 들어간다.

### Multi-turn previous context

이전 turn이 여러 개면 전부 들어간다.

예를 들어 turn 4를 생성할 때 prompt에는 turn 1, turn 2, turn 3의 user/gold call/observation이 모두 들어간다.

형태:

```text
Previous Turns:

Turn 1 User:
...
Previous Plan:
1. previous_gold_call(...)
Observation: ...
<END_PLAN>

Turn 2 User:
...
Previous Plan:
1. previous_gold_call(...)
2. previous_gold_call(...)
Observation: ...
<END_PLAN>

Current Turn User:
...

Current Plan:
```

현재 turn의 gold answer는 prompt에 없다.

### Current Plan generation

모델은 현재 turn에 대해서만 plan을 생성한다.

예:

```text
Thought: locate the files, then copy the independent matched files.
1. cd(folder="projects")
2. cd(folder="photography")
3. cp(source="test_image1.jpg", destination="backup_tests")
4. cp(source="test_document.txt", destination="backup_tests")
<END_PLAN>
```

만약 현재 plan 안에서 이전 action 결과가 필요하면 `$id`를 쓴다.

```text
1. find(path=".", name="test")
2. cp(source=$1.matches[0], destination="backup_tests")
3. cp(source=$1.matches[1], destination="backup_tests")
<END_PLAN>
```

`$id`는 current plan 내부에만 적용된다. previous turn의 action id를 `$1`로 참조하지 않는다. Current Plan numbering은 매 turn마다 `1.`부터 다시 시작한다.

### Parsing

파일:

```text
src/parse_plan.py
```

parser가 뽑는 주요 정보:

```text
node_id
tool_name
args_text
dependencies
thought
raw_action
is_valid_tool
response_spans
```

`dependencies`는 `$id` reference에서 나온다.

예:

```text
3. estimate_distance(cityA=$1.zipcode, cityB=${2}.zipcode)
```

parsed result:

```json
{
  "node_id": 3,
  "tool_name": "estimate_distance",
  "dependencies": [1, 2]
}
```

## 실행 방법

### 1. Prepare prompts 한 번 생성

BFCL merge, graph attach, episode filtering, gold observation replay, prompt 생성을 한 번 수행한다.

```bash
bash /home/ilju/research/DiffuAgent/think_parallel_v2/scripts/prepare_multiturn_base_prompts.sh
```

기본 출력:

```text
/home/ilju/research/DiffuAgent/think_parallel_v2/prepared/multi_turn_base_intra_turn_parallel_prompts.jsonl
/home/ilju/research/DiffuAgent/think_parallel_v2/prepared/multi_turn_base_intra_turn_parallel_prompts_manifest.jsonl
/home/ilju/research/DiffuAgent/think_parallel_v2/prepared/multi_turn_base_intra_turn_parallel_prompts_metrics.json
```

이 파일은 prompt template, graph, filtering 기준이 바뀌지 않는 한 여러 generation run에서 재사용한다.

### 2. Prepared prompts dry-run

모델을 로드하지 않고 prepared prompts를 runner가 읽을 수 있는지 확인한다.

```bash
python /home/ilju/research/DiffuAgent/think_parallel_v2/src/run_discovery.py \
  --category multi_turn_base \
  --prepared-prompts-path /home/ilju/research/DiffuAgent/think_parallel_v2/prepared/multi_turn_base_intra_turn_parallel_prompts.jsonl \
  --output-dir /home/ilju/research/DiffuAgent/think_parallel_v2/outputs/dry_run_prepared \
  --dry-run
```

prepared prompt를 읽을 때도 `--ids` 또는 `--ids-file`로 episode subset을 고를 수 있다. 이 경우 full prepared cache는 그대로 두고, 선택된 `question_id`의 turn rows만 실행한다.

```bash
python /home/ilju/research/DiffuAgent/think_parallel_v2/src/run_discovery.py \
  --category multi_turn_base \
  --prepared-prompts-path /home/ilju/research/DiffuAgent/think_parallel_v2/prepared/multi_turn_base_intra_turn_parallel_explicit_prompts.jsonl \
  --ids multi_turn_base_97,multi_turn_base_128 \
  --output-dir /home/ilju/research/DiffuAgent/think_parallel_v2/outputs/dry_run_subset \
  --dry-run
```

### 3. LLaDA generation run

```bash
python /home/ilju/research/DiffuAgent/think_parallel_v2/src/run_discovery.py \
  --category multi_turn_base \
  --prepared-prompts-path /home/ilju/research/DiffuAgent/think_parallel_v2/prepared/multi_turn_base_intra_turn_parallel_prompts.jsonl \
  --output-dir /home/ilju/research/DiffuAgent/think_parallel_v2/outputs/llada_multiturn_base
```

wrapper script:

```bash
bash /home/ilju/research/DiffuAgent/think_parallel_v2/scripts/run_multiturn_base_llada.sh
```

이 script는 기본 prepared prompt path를 다음으로 둔다.

```text
/home/ilju/research/DiffuAgent/think_parallel_v2/prepared/multi_turn_base_intra_turn_parallel_prompts.jsonl
```

다른 prepared prompt 파일을 쓰고 싶으면 `PREPARED_PROMPTS`로 바꿔서 실행한다.

```bash
PREPARED_PROMPTS=/path/to/other_prepared_prompts.jsonl \
bash /home/ilju/research/DiffuAgent/think_parallel_v2/scripts/run_multiturn_base_llada.sh
```

### 4. Smoke comparison jobs

수정 전 single-prompt v2 cache, new explicit DAG, new flat plan을 같은 9개 episode subset에서 비교하는 SLURM job이다.

```bash
cd /home/ilju/research/DiffuAgent

sbatch think_parallel_v2/scripts/run_smoke_pre_split.job
sbatch think_parallel_v2/scripts/run_smoke_explicit.job
sbatch think_parallel_v2/scripts/run_smoke_flat.job
```

공통 실행 스크립트는 `think_parallel_v2/scripts/run_smoke_condition.sh`다. 필요하면 다음 환경 변수로 override한다.

```text
SMOKE_IDS
OUT 또는 OUTPUT_DIR
PREPARED_PROMPTS
GPUS
LLADA_GEN_LENGTH
LLADA_STEPS
LLADA_BLOCK_LENGTH
DRY_RUN=1
```

## Output

prepare stage와 generation stage의 output이 나뉜다.

### Prepare output

기본 위치:

```text
/home/ilju/research/DiffuAgent/think_parallel_v2/prepared/
```

주요 파일:

```text
multi_turn_base_intra_turn_parallel_prompts.jsonl
  generation stage가 읽는 prepared turn prompts

multi_turn_base_intra_turn_parallel_prompts_manifest.jsonl
  선택된 full episode 목록과 graph summary

multi_turn_base_intra_turn_parallel_prompts_metrics.json
  prepared prompt row 수, episode 수, replay error 여부
```

`prepared_prompts.jsonl`의 각 row는 한 turn에 대응한다.

주요 field:

```text
question_id
turn_index
mode
current_goal
prompt
n_functions
function_names
gold_calls
gold_observations
graph_stats
```

`prompt`가 실제 model input이다. `gold_calls`는 현재 turn 정답 metadata이고 prompt 안에는 들어가지 않는다.

### Generation output

generation output directory에는 다음 파일들이 생긴다.

### `episode_manifest.jsonl`

선택된 full episode 목록과 graph summary.

주요 field:

```text
question_id
category
n_turns
n_gold_calls
has_graph
graph_summary
```

이 파일로 실제로 어떤 episode가 선택됐는지 먼저 확인한다.

### `prompts.jsonl`

각 turn별 prompt와 debug/eval metadata.

주요 field:

```text
question_id
turn_index
current_goal
prompt
n_functions
gold_calls
gold_observations
graph_stats
```

주의:

```text
prompt field:
  실제 model input이다.
  여기에는 previous turns의 gold call/observation만 들어간다.

gold_calls field:
  현재 turn의 gold answer다.
  이것은 평가/debug metadata이며 model input이 아니다.

gold_observations field:
  현재 turn gold call을 replay한 결과다.
  이것도 현재 turn prompt에는 들어가지 않고,
  다음 turn의 previous context를 만들 때 사용된다.
```

### `raw_generations.jsonl`

모델이 생성한 raw response.

주요 field:

```text
question_id
turn_index
raw_response
latency
input_tokens
output_tokens
generation_config
```

형식 실패, `<END_PLAN>` 누락, 이상한 tool name 등은 여기에서 먼저 확인한다.

### `plan_units.jsonl`

parser가 raw response를 LLMCompiler-style plan node로 구조화한 결과.

주요 field:

```text
parse_mode
parse_error
n_units
units
graph_stats
```

`units` 안에는 다음이 있다.

```text
node_id
tool_name
args_text
dependencies
thought
raw_action
is_valid_tool
response_spans
```

`is_valid_tool`은 tool name이 제공된 function list 안에 있는지만 나타낸다. argument schema가 맞는지, gold call과 맞는지, 불필요한 중복 action이 있는지는 이 값으로 판단하지 않는다.

각 row에는 post-hoc diagnostic용 `quality_metrics`도 포함된다.

```text
valid_tool_name_units
invalid_tool_names
schema_checked
schema_valid_units
schema_invalid_units
schema_errors
duplicate_action_count
has_duplicate_actions
generated_gold_call_delta
is_over_generated_vs_gold
gold_tool_names
generated_tool_names
dependency_edge_count
flat_reference_violation_count
has_flat_reference_violation
```

여기서 `schema_checked=false`이면 해당 prompt row에 function schema metadata가 없어서 schema metric을 계산하지 못했다는 뜻이다. 새로 prepare한 prompt에는 `function_schemas`가 들어가므로 generation stage에서 schema metric을 계산할 수 있다.

`flat_reference_violation_count`는 `llmcompiler_flat_plan` condition에서만 의미가 있다. parser는 기존처럼 generated `$` reference를 dependency로 파싱하므로, flat mode에서 dependency edge가 생기면 flat contract를 위반한 것으로 기록한다.

이 파일이 post-hoc matching/analysis의 기본 입력이다.

### `token_confidence.jsonl`

DLM/LLaDA denoising trace.

주요 field:

```text
question_id
turn_index
block
commit_step
step_in_block
position
token_id
token_text
confidence
char_start
char_end
```

`response_spans`와 연결하면 특정 action line, function name, `$id` dependency token이 언제 commit됐는지 볼 수 있다.

### `generation_metrics.json`

generation/parse summary.

대표 metric:

```text
format_parse_rate
total_units
mean_units_per_generation
valid_tool_name_units
schema_valid_units
duplicate_action_generations
over_generated_vs_gold_generations
dependency_edge_count
flat_reference_violation_generations
flat_reference_violation_count
```

`parse` section은 plan quality metric이 아니라 format sanity metric이다. `quality` section은 tool-name validity, schema validity, duplicate/over-generation 같은 post-hoc diagnostics를 분리해서 보여준다. gold correctness는 이 값들을 DAG/gold matching과 함께 해석해야 한다.

### `summary.md`

run과 parse 결과를 사람이 빠르게 확인하기 위한 요약 파일이다.

주요 내용:

```text
category
mode
n_episodes
n_turn_generations
episode_filter
dry_run 여부
format_parse_rate
total_units
mean_units_per_generation
```

## 결과 해석 방법

현재 README 기준으로 post-hoc matching/denoising 분석 script는 아직 자동화되어 있지 않다. 이 runner는 그 분석을 위한 원자료를 만든다.

즉, 자동화된 것은 여기까지다.

```text
BFCL episode load
gold observation replay
LLMCompiler-style prompt generation
DLM generation
plan parsing
token confidence trace 저장
graph_stats 부착
```

아래 해석 단계는 `plan_units.jsonl`, `token_confidence.jsonl`, `prompts.jsonl`, `episode_manifest.jsonl`을 이용한 후속 분석 기준이다.

### 1. Format sanity

먼저 확인할 것:

```text
parse_mode != failed
parse_error 없음
<END_PLAN> 존재
unique increasing numeric IDs
invalid tool name 없음
```

이 단계는 “DLM이 LLMCompiler-style grammar를 따를 수 있는가”를 본다.

### 2. Action coverage

각 turn에서:

```text
generated units 수
gold_calls 수
tool_name overlap
argument/entity overlap
schema validity
duplicate action count
generated_gold_call_delta
```

를 비교한다.

이 단계는 “필요한 subtask를 plan으로 복원했는가”를 본다.

주의:

```text
valid_tool_name_units 또는 is_valid_tool은 gold correctness가 아니다.
```

gold correctness는 다음 계층으로 본다.

```text
strict tool correctness:
  generated tool multiset == gold tool multiset

relaxed tool correctness:
  generated/gold tool set precision, recall

schema correctness:
  selected tool의 required/exact parameter schema 만족 여부

plan compactness:
  duplicate action, over-generation 여부

DAG correctness:
  generated $id dependency edge/layer와 gold DAG dependency/antichain alignment
```

### 3. Parallel/dependency structure

generated plan에서:

```text
$id가 없는 action들 = current plan 내 독립 후보
$id가 있는 action들 = current plan 내 dependency 후보
```

gold graph에서:

```text
turn_layers
intra_turn_antichain_pairs
depends_on
```

와 비교한다.

좋은 신호:

```text
gold에서 parallel-safe인 pair를 generated plan에서도 서로 $id 없이 분리함
gold에서 dependent인 pair를 generated plan에서 $id로 연결함
```

나쁜 신호:

```text
독립 action인데 불필요한 $id dependency를 만듦
dependent action인데 $id 없이 병렬처럼 둠
필요한 action을 하나의 자연어 line으로 뭉개거나 누락함
```

### 4. Denoising dynamics

`token_confidence.jsonl`과 `plan_units.jsonl`의 spans를 연결해 본다.

#### token confidence의 의미

v2의 LLaDA backend는 v1의 traceable generation을 재사용한다.

```text
think_parallel_v1/src/llada_trace.py
```

생성은 output 영역을 mask token으로 채운 뒤 block 단위로 denoising한다. 각 denoising step에서 아직 mask인 position에 대해 모델 logits를 계산하고, 선택될 token `x0`를 만든다. `remasking=low_confidence`일 때 저장되는 confidence는 다음 값이다.

```text
softmax(logits)[selected_token]
```

즉 `token_confidence.jsonl`의 `confidence`는 **해당 token이 최종 commit된 순간의 selected-token probability**다. 전체 denoising 과정에서 같은 position의 confidence가 step마다 어떻게 변했는지는 현재 저장하지 않는다.

현재 trace에 저장되는 row는 “commit된 token”에 대해서만 생긴다.

```text
block:
  generation output을 block_length 단위로 나눈 block index

commit_step:
  전체 denoising loop 기준 몇 번째 model forward / commit step에서 이 token이 확정됐는지

step_in_block:
  해당 block 안에서 몇 번째 denoising step인지

position:
  generated output 안에서의 token position

confidence:
  commit 순간 selected token의 softmax probability
```

따라서 confidence는 “최종 답이 맞을 확률”이 아니라, LLaDA denoising 중 **그 순간 그 token을 얼마나 확신하고 commit했는지**를 나타낸다.

#### block별 confidence aggregation

block별 confidence는 `token_confidence.jsonl`을 `block` field로 groupby해서 `confidence` 평균을 낸 값이다.

```text
block_confidence_mean[b]
  = mean(confidence for rows where row.block == b)
```

이 값은 block 단위로 생성 위치가 뒤로 갈수록 token commit confidence가 어떻게 달라지는지 보는 coarse diagnostic이다. 예를 들어 새 default인 `gen_length=128`, `block_length=32` 설정에서는 block 0이 response 초반 32 token들, block 3이 response 후반 32 token들에 해당한다. 과거 `outputs/llada_multiturn_base` run처럼 `gen_length=256`, `block_length=32`였던 경우에는 block 7이 후반 32 token들이다.

주의:

```text
block별 평균은 같은 token의 trajectory가 아니다.
서로 다른 position/token들이 각자 commit된 순간의 confidence를 block 단위로 평균낸 것이다.
```

#### action span confidence aggregation

`plan_units.jsonl`의 각 unit에는 response character span이 있다.

```text
response_spans.action:
  raw action line 전체의 char_start / char_end

response_spans.function_name:
  function name 부분의 char_start / char_end
```

`token_confidence.jsonl`에도 각 token의 decoded text span이 있다.

```text
char_start
char_end
```

action span confidence는 action line span과 겹치는 token rows를 찾고, 그 token들의 confidence 평균을 낸 값이다.

```text
action_confidence(unit)
  = mean(token.confidence
         for token in token_confidence
         if token span overlaps unit.response_spans.action)
```

function-name confidence도 같은 방식으로 function_name span과 겹치는 token만 평균낸다.

이 aggregation으로 다음을 비교할 수 있다.

```text
valid tool-name action vs invalid tool-name action
root action vs $id dependency action
gold parallel turn의 action line commit confidence
gold serial/dependent turn의 action line commit confidence
```

다만 이것도 action line에 속한 token들의 **commit 순간 confidence 평균**이다. action line을 구성하는 token들이 denoising 과정에서 어떻게 변했는지, 즉 confidence delta나 trajectory slope는 현재 기록되지 않는다.

#### 현재 저장하지 않는 것

현재 trace는 다음을 저장하지 않는다.

```text
같은 output position의 per-step confidence history
commit 전 후보 token 변화
top-k distribution 변화
confidence delta / slope
uncommitted masked position의 confidence
```

따라서 “denoising trajectory에 대응하는 토큰의 confidence 변화량”을 직접 측정하려면 trace 확장이 필요하다. 예를 들어 action/function/$id span에 해당하는 output positions에 대해 매 denoising step의 top-1 token, top-1 confidence, committed 여부를 저장해야 한다.

관심 질문:

```text
parallel-safe actions의 function name/action line이 비슷한 commit_step에 확정되는가?
dependent action은 prerequisite action보다 늦게 확정되는가?
$id reference token은 어느 시점에 commit되는가?
action line의 commit pattern이 gold turn_layers와 상관되는가?
commit 전 confidence trajectory나 confidence delta가 dependency/parallel structure와 상관되는가?  # trace 확장 필요
```

이게 v2 실험의 핵심 연구 신호다.

## 주의할 점

### Gold observation replay는 final run에서 strict

final run에서는 gold observation replay가 실패하면 안 된다.

현재 runner는 기본 strict다. BFCL executor dependency가 빠져 있으면 실행이 실패한다. 예를 들어 `MathAPI`는 BFCL repo의 dependency인 `mpmath==1.3.0`이 필요할 수 있다.

prompt shape만 확인하는 dry-run에서는 다음 옵션을 쓸 수 있다.

```text
--allow-gold-replay-errors
```

하지만 이 옵션은 final experiment에서는 쓰지 않는다.

### Graph는 generation input이 아니다

gold DAG는 model prompt에 들어가지 않는다. graph는 filtering과 post-hoc 분석에만 쓰인다.

따라서 generated plan이 gold graph를 “보고 맞춘 것”이 아니다.

### Previous context는 oracle context다

이전 turn context는 model-generated previous plan이 아니라 gold previous calls + gold observations다.

이 설정의 목적은 current turn planning 능력을 분리해서 보기 위함이다. 후속 ablation에서는 model-generated previous context로 바꿀 수 있지만, v2 초기 실험은 oracle previous context가 기본이다.

### Current turn 단위 generation, episode 단위 dataset

모델 호출 단위는 turn이다.

하지만 sampling/filtering/evaluation의 기본 단위는 full episode다.

```text
selected episode:
  turn 1 -> generation
  turn 2 -> generation with turn 1 previous context
  turn 3 -> generation with turn 1-2 previous context
```

turn만 떼어 단독 sample로 쓰지 않는다.
