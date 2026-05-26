# think_parallel_v2 experiment documentation

이 문서는 `think_parallel_v2` 실험을 보고서로 작성하기 위한 설계 문서다. 사용법 안내가 아니라, 현재 진행 중인 실험들이 무엇을 비교하고, 어떤 프롬프트를 사용하며, 어떤 지표와 예시로 분석할지를 정리한다.

현재 기본 smoke set은 v1-v2 overlap 20 episodes로 갱신되어 있으며, prompt 기본값은 `state_view=tree`다. 이 set의 최종 결과 숫자는 아직 채우지 않는다. 다만 아래에는 이전 9-episode smoke artifact에서 얻은 preliminary 결과 메모를 별도 섹션으로 남긴다.

## 1. 실험 목적

`think_parallel_v2`는 BFCL v3 `multi_turn_base`에서 DLM/LLaDA가 **현재 user turn에 필요한 tool-use plan을 LLMCompiler-style grammar로 생성하면서, 병렬 가능한 action과 이전 action 결과가 필요한 action을 구분할 수 있는지**를 보기 위한 실험이다.

핵심 질문은 두 층으로 나뉜다.

```text
Q1. LLaDA가 exact BFCL answer wrapper 없이도
    current turn에 필요한 tool action node를 복구할 수 있는가?

Q2. 생성된 numbered plan과 denoising trace 안에서
    gold DAG의 병렬/순차 구조와 연결될 수 있는 signal이 보이는가?
```

v1은 `[A1] Use ...` 형태의 natural-language action unit을 만들고 post-hoc judge로 gold hop과 맞췄다. v2는 한 단계 더 직접적으로 LLMCompiler-style plan grammar를 사용한다.

```text
v1:
  [A1] Use tool_name: natural-language action. Inputs: ...

v2:
  Thought: <optional one-line strategy>
  1. tool_name(param=value)
  2. tool_name(param=$1.field)
  <END_PLAN>
```


## 2. 현재 비교 조건

현재 README에서 다루는 기본 조건은 `state_view=tree`를 포함한 두 가지다. 핵심 비교축은 explicit dependency syntax와 flat placeholder syntax의 차이다. `state_view=none`은 기존 state-blind ablation 또는 legacy artifact를 재현할 때만 사용한다.

| condition | mode | 역할 |
|---|---|---|
| `smoke_explicit_state_tree` | `llmcompiler_explicit_dag` | deterministic current state view를 보고, current-plan 결과가 필요한 argument를 `$id` 또는 `$id.field`로 표현하는 explicit DAG condition. |
| `smoke_flat_state_tree` | `llmcompiler_flat_plan` | deterministic current state view를 보고, numbered action reference를 argument 안에 쓰지 않는 flat plan condition. result-dependent argument는 angle-bracket placeholder로 둔다. |

두 조건의 비교 의도는 다음과 같다.

| 비교 | 보려는 것 |
|---|---|
| `smoke_explicit_state_tree` vs `smoke_flat_state_tree` | 같은 deterministic state view 위에서 `$id` reference를 직접 허용할 때와 금지할 때 action recovery 및 denoising signal이 어떻게 달라지는지 |
| explicit `$id` vs flat placeholder | 의존 구조를 output syntax에 드러내는 조건과, action node만 보존하는 조건의 차이 |


## 3. 데이터와 turn 단위 설계

### 3.1 Episode는 유지하고, generation은 turn 단위로 수행

BFCL `multi_turn_base` record는 여러 user turn을 포함한다. v2는 turn을 독립 sample로 떼어내지 않고 full episode를 유지한다. 다만 모델 호출은 current turn마다 한 번씩 수행한다.

```text
selected episode:
  turn 1 -> one model generation
  turn 2 -> one model generation with turn 1 previous context
  turn 3 -> one model generation with turn 1-2 previous context
```

즉 episode 하나를 한 번의 model call로 처리하는 것이 아니라, episode 안의 각 user turn마다 별도의 generation을 수행한다. 이 설계의 목적은 current turn planning을 보면서도 이전 turn의 state와 observation을 oracle context로 제공하는 것이다.

이 방식은 분석 grain을 turn 단위로 깨끗하게 만들지만, inference cost는 turn 수에 비례한다. 현재 기본 smoke set처럼 20 episodes가 70 turns를 포함하면 condition 하나당 70번의 model generation이 발생한다.

### 3.2 Previous context는 oracle context

현재 turn 이전의 user request, gold call, gold observation은 prompt에 들어간다. 현재 turn의 gold call은 prompt에 들어가지 않는다.

```text
Completed Previous Turns (read-only context):
Their Observations may be used as concrete input values.
Do not output Observation lines in the Current Plan.

Turn 1 User:
...
Previous Plan:
1. previous_gold_call(...)
Observation: ...
<END_PLAN>

Current Environment State:
...

Current Turn User:
...

Current Plan:
```

이전 turn context는 model-generated previous plan이 아니라 gold previous plan이다. 이 설정은 previous-turn error accumulation을 제거하고, current-turn plan 생성 능력을 분리해서 보기 위한 것이다.

### 3.3 Current turn gold는 metadata

각 prompt row에는 current turn의 `gold_calls`와 `graph_stats`가 함께 저장된다. 그러나 이것은 평가와 분석용 metadata이며 model input이 아니다.

예를 들어 `multi_turn_base_3` turn 2는 다음 current-turn gold를 가진다.

```text
cd(folder='projects')
cd(folder='photography')
cp(source='test_image1.jpg', destination='backup_tests')
cp(source='test_document.txt', destination='backup_tests')
```

해당 turn의 graph stats는 다음 구조를 가진다.

```text
gold_hop_ids: h2, h3, h4, h5
turn_layers: [h2] -> [h3] -> [h4, h5]
intra_turn_antichain_pairs: [h4, h5]
turn_width: 2
```

즉 `cp` 두 개는 같은 turn 안에서 병렬 가능한 gold action pair로 볼 수 있다.

### 3.4 Smoke episode selection

현재 smoke run의 기본 episode set은 전체 `multi_turn_base` 200개에서 무작위로 고른 set이 아니다. 준비된 prompt는 graph annotation이 있으며 같은 turn 안에 병렬 가능한 gold action pair가 있는 episode만 남긴다.

```text
episode_filter=intra_turn_parallel:
  has graph annotation
  turn_bound_max_width >= 2
  n_intra_turn_antichain_pairs > 0
```

그 위에서 smoke run의 기본 `SMOKE_IDS`는 v1 50-sample run과 v2 intra-turn-parallel 73-episode prepared set이 겹치는 20개 episode로 둔다. 목적은 v1의 full-trajectory `[A]` judge 결과와 v2의 LLMCompiler-style explicit/flat 결과를 같은 episode 위에서 비교할 수 있게 만드는 것이다. 따라서 이 set은 전체 BFCL 대표 표본이라기보다, **v1-v2 비교 가능성과 intra-turn parallel structure를 동시에 만족하는 diagnostic comparison set**이다.

| episode | turns | gold calls | critical path | parallel width | turn-bound max width | intra-turn antichain pairs |
|---|---:|---:|---:|---:|---:|---:|
| `multi_turn_base_35` | 3 | 7 | 5 | 2 | 2 | 1 |
| `multi_turn_base_39` | 4 | 10 | 5 | 4 | 3 | 12 |
| `multi_turn_base_50` | 1 | 2 | 1 | 2 | 2 | 1 |
| `multi_turn_base_55` | 5 | 9 | 4 | 4 | 3 | 8 |
| `multi_turn_base_56` | 3 | 8 | 2 | 5 | 2 | 2 |
| `multi_turn_base_57` | 2 | 4 | 3 | 2 | 2 | 1 |
| `multi_turn_base_59` | 5 | 10 | 3 | 5 | 2 | 3 |
| `multi_turn_base_62` | 4 | 8 | 4 | 3 | 2 | 1 |
| `multi_turn_base_67` | 4 | 8 | 4 | 4 | 2 | 3 |
| `multi_turn_base_70` | 2 | 9 | 3 | 5 | 4 | 11 |
| `multi_turn_base_71` | 5 | 9 | 3 | 5 | 2 | 2 |
| `multi_turn_base_86` | 3 | 8 | 5 | 3 | 3 | 5 |
| `multi_turn_base_87` | 4 | 8 | 2 | 6 | 3 | 5 |
| `multi_turn_base_88` | 3 | 7 | 3 | 5 | 3 | 5 |
| `multi_turn_base_91` | 2 | 3 | 2 | 2 | 2 | 1 |
| `multi_turn_base_97` | 6 | 10 | 3 | 6 | 2 | 3 |
| `multi_turn_base_143` | 4 | 6 | 4 | 3 | 2 | 1 |
| `multi_turn_base_151` | 3 | 6 | 4 | 2 | 2 | 1 |
| `multi_turn_base_173` | 4 | 5 | 3 | 2 | 2 | 1 |
| `multi_turn_base_185` | 3 | 5 | 2 | 3 | 2 | 2 |

이 20개 episode는 총 70 turns를 만든다. v2는 turn마다 별도 generation을 수행하므로, `smoke_explicit_state_tree` 또는 `smoke_flat_state_tree` condition 하나를 돌리면 70번의 LLaDA generation이 발생한다.

### 3.5 State View Sanity

현재 20-episode smoke set에서 `state_view=tree` dry-run을 확인한 결과는 다음과 같다.

```text
episodes: 20
turn prompts: 70
state_view_mode: tree for all 70
empty state_view: 0
state_view missing from prompt: 0
state replay errors: 0
truncation/max_depth/max_entries hit: 0
```

class coverage는 `GorillaFileSystem`, `VehicleControlAPI`, `MessageAPI`, `TravelAPI`, `TwitterAPI`, `TicketAPI`, `TradingBot`, `MathAPI`를 포함한다. `GorillaFileSystem`은 `cwd + tree`로 렌더링하고, 다른 API는 public state를 deterministic JSON-like text로 렌더링한다.

주의: non-filesystem API의 generic renderer는 BFCL synthetic public state를 그대로 보여주므로 token/password/access_token처럼 보이는 key가 prompt state view에 들어갈 수 있다. 이것은 LLM summary가 아니라 hidden execution state를 static planning input으로 노출하는 진단 설정이다. 보안/정보량을 엄격히 맞추는 별도 실험이 필요하면 class-specific redacted renderer를 추가하거나 `state_view=none` ablation과 분리해서 비교한다.

## 4. 프롬프트 설계

### 4.1 System prompt의 공통 목적

v2 system prompt는 BFCL official answer wrapper를 요구하지 않는다. 대신 function docs와 compact planning contract를 제공한다.

공통 objective는 다음이다.

```text
Given the current user turn, create the minimal sufficient tool-use plan to solve it.
Use only necessary actions.
Among those actions, maximize parallelizability.
```

순서가 중요하다. 먼저 current turn을 해결하는 데 필요한 최소 action set을 고르고, 그 action set 안에서만 병렬성을 최대화한다. `maximize parallelizability`만 강조하면 불필요한 helper action을 많이 생성할 수 있기 때문이다.

공통 contract는 다음이다.

```text
- Output only Thought, numbered actions, and <END_PLAN>.
- Each action must be one provided function using exact schema parameter names.
- Do not wrap arguments in arg= unless the function schema contains a parameter named arg.
- IDs start at 1 and strictly increase within the Current Plan.
- Do not repeat previous-turn actions unless the current user explicitly asks to perform them again.
- Use functions at their documented granularity.
- Do not add helper actions unless their outputs are needed for the current turn.
- Do not call join().
```

### 4.2 `smoke_explicit_state_tree`

`smoke_explicit_state_tree`는 `state_view=tree`와 `llmcompiler_explicit_dag`를 함께 쓰는 condition이다. current plan 안에서 이전 action 결과가 필요하면 `$id` 또는 `$id.field`를 쓴다.

출력 contract:

```text
Thought: <optional one-line strategy>
1. tool_name(param=value)
2. tool_name(param=$1.field)
<END_PLAN>
```

`$id`는 current plan 내부에서만 유효하다. previous turn의 plan id를 `$1`로 참조하지 않는다. previous turn에서 필요한 값은 Observation text에서 concrete value로 가져오거나 자연어 plan에 반영해야 한다.

예:

```text
1. get_zipcode_based_on_city(city="San Francisco")
2. get_zipcode_based_on_city(city="Rivermist")
3. estimate_distance(cityA=$1.zipcode, cityB=$2.zipcode)
<END_PLAN>
```

여기서 1과 2는 서로 독립이므로 병렬 가능하다. 3은 1과 2의 결과가 있어야 하므로 `$1`, `$2`를 참조한다.

### 4.3 `smoke_flat_state_tree`

`smoke_flat_state_tree`는 `state_view=tree`와 `llmcompiler_flat_plan`을 함께 쓰는 condition이다. 이 조건에서는 argument 안에 numbered action reference를 쓰지 않는다.

출력 contract:

```text
Thought: <optional one-line strategy>
1. tool_name(param=value)
2. tool_name(param="<needed value from another current-plan action>")
<END_PLAN>
```

explicit reference 대신 short angle-bracket placeholder를 사용한다.

```text
1. get_zipcode_based_on_city(city="San Francisco")
2. get_zipcode_based_on_city(city="Rivermist")
3. estimate_distance(cityA="<zipcode for San Francisco>", cityB="<zipcode for Rivermist>")
<END_PLAN>
```

이 조건의 목적은 `$id` grammar 없이도 필요한 action node가 보존되는지, 그리고 token confidence / commit order만으로 병렬 또는 순차 구조 signal을 볼 수 있는지 확인하는 것이다.

flat condition에서 `$1`, `$2.field` 같은 reference가 생성되면 contract 위반이다. 이 경우 `flat_reference_violation_count`에 잡힌다.

### 4.4 State View

기본 prompt는 current turn 시작 직전의 deterministic state view를 포함한다. 이 view는 LLM summary가 아니라 BFCL `initial_config`에서 시작해 이전 turn의 gold calls만 replay한 뒤 rule-based renderer로 만든다. 따라서 current turn gold call은 state view 생성에 사용하지 않는다.

기본 mode는 `--state-view tree`이며, 기존 state-blind ablation은 `--state-view none`으로 유지한다.

중요한 해석 경계는 다음이다.

```text
state_view=tree:
  hidden BFCL state를 deterministic text로 제공하는 static planning diagnostic.
  official BFCL interactive inference와 같지는 않다.

state_view=none:
  user query + previous oracle context만 보는 state-blind ablation.
  hidden path/id/value가 user query에 없으면 resolved gold action을 맞히기 어렵다.
```

예시:

```text
Current Environment State:
GorillaFileSystem:
cwd: /alex
tree:
- alex/
  - projects/
    - deep_folder/
      - config.py
      - real_config.py
```

## 5. Prompt에 넣지 않는 정보

v2 기본 state-tree 조건은 다음 정보를 prompt에 넣지 않는다.

```text
current-turn gold calls
gold DAG graph
initial_config raw dump
BFCL official answer wrapper
generated previous-turn plans
```

gold DAG는 episode filtering과 post-hoc analysis에만 사용한다. 따라서 generated plan이 gold graph를 보고 맞춘 것이 아니다.

이전 상태는 다음 경로로 전달된다.

```text
previous user text
previous gold calls
previous gold observations
deterministic current environment state view
```

### 5.1 기본 실행 명령

새 기본 조건은 prepared prompt 파일명에 `state_tree`를 포함한다. 기존 state-blind 산출물은 같은 이름으로 재사용하지 않는다.

```bash
cd /home/ilju/research

ROOT=/home/ilju/research/DiffuAgent/think_parallel_v2
RUN_STAMP=$(date +%y%m%d_%H%M%S)

# explicit state-tree prepared prompts
MODE=llmcompiler_explicit_dag \
STATE_VIEW=tree \
bash $ROOT/scripts/prepare_multiturn_base_prompts.sh

# flat state-tree prepared prompts
MODE=llmcompiler_flat_plan \
STATE_VIEW=tree \
bash $ROOT/scripts/prepare_multiturn_base_prompts.sh

# 20-case explicit smoke run
CONDITION=explicit \
STATE_VIEW=tree \
RUN_STAMP=$RUN_STAMP \
OUT=$ROOT/outputs/smoke_explicit_state_tree_$RUN_STAMP \
bash $ROOT/scripts/run_smoke_condition.sh

# 20-case flat smoke run
CONDITION=flat \
STATE_VIEW=tree \
RUN_STAMP=$RUN_STAMP \
OUT=$ROOT/outputs/smoke_flat_state_tree_$RUN_STAMP \
bash $ROOT/scripts/run_smoke_condition.sh
```

matching은 두 단계다. 먼저 `run_v2_matching.sh`로 P0 deterministic matcher를 실행한다. 이 단계는 LLM-as-judge를 호출하지 않고, `v2_match_*` 산출물만 만든다.

```bash
PYTHON_BIN=/home/ilju/miniconda3/envs/llada8b/bin/python \
OUTPUT_DIR=$ROOT/outputs/smoke_explicit_state_tree_$RUN_STAMP \
bash $ROOT/scripts/run_v2_matching.sh

PYTHON_BIN=/home/ilju/miniconda3/envs/llada8b/bin/python \
OUTPUT_DIR=$ROOT/outputs/smoke_flat_state_tree_$RUN_STAMP \
bash $ROOT/scripts/run_v2_matching.sh
```

LLM-as-judge 보정까지 포함한 P1 hybrid 결과가 필요하면 P0 이후 같은 output directory에 대해 `run_v2_hybrid_matching.sh`를 추가로 실행한다. 이 단계가 `v2_judge_*`, `v2_hybrid_*` 산출물을 만든다.

```bash
PYTHON_BIN=/home/ilju/miniconda3/envs/llada8b/bin/python \
OUTPUT_DIR=$ROOT/outputs/smoke_explicit_state_tree_$RUN_STAMP \
bash $ROOT/scripts/run_v2_hybrid_matching.sh

PYTHON_BIN=/home/ilju/miniconda3/envs/llada8b/bin/python \
OUTPUT_DIR=$ROOT/outputs/smoke_flat_state_tree_$RUN_STAMP \
bash $ROOT/scripts/run_v2_hybrid_matching.sh
```

prepared prompt 기본 파일:

| mode | default prepared prompt |
|---|---|
| `llmcompiler_explicit_dag` | `prepared/multi_turn_base_intra_turn_parallel_explicit_state_tree_prompts.jsonl` |
| `llmcompiler_flat_plan` | `prepared/multi_turn_base_intra_turn_parallel_flat_state_tree_prompts.jsonl` |

state-blind ablation은 같은 명령에서 `STATE_VIEW=none` 또는 `--state-view none`으로 실행한다.

## 6. 파싱과 산출물 schema

### 6.1 Plan parser

`parse_plan.py`는 다음 형식의 line만 action unit으로 구조화한다.

```text
<integer>. <tool_name>(<args_text>)
```

`<END_PLAN>` 또는 `<END_OF_PLAN>`을 만나면 plan 종료로 본다.

parser가 생성하는 주요 unit field:

| field | 의미 |
|---|---|
| `unit_id` | parsed unit id |
| `node_id` | numbered action id |
| `tool_name` | function name |
| `args_text` | parenthesis 안 argument string |
| `dependencies` | `$id` reference에서 추출한 current-plan reference ids |
| `thought` | 직전 `Thought:` line 내용 |
| `raw_action` | 원문 action line |
| `is_valid_tool` | `tool_name`이 provided function list에 있는지 |
| `response_spans.action` | raw action line의 response character span |
| `response_spans.function_name` | function name의 response character span |

예:

```text
3. estimate_distance(cityA=$1.zipcode, cityB=${2}.zipcode)
```

parsed dependency:

```json
{
  "node_id": 3,
  "tool_name": "estimate_distance",
  "dependencies": [1, 2]
}
```

### 6.2 Generation records

보고서 분석에 주로 쓰는 파일은 다음이다.

| file | 분석 용도 |
|---|---|
| `prompts.jsonl` | 실제 model input과 current-turn gold metadata 확인 |
| `raw_generations.jsonl` | 모델 raw response 확인 |
| `plan_units.jsonl` | parsed plan node, parse error, quality diagnostics 확인 |
| `token_confidence.jsonl` | token commit trace 확인 |
| `episode_manifest.jsonl` | 어떤 episode가 포함됐는지 확인 |
| `generation_metrics.json` | run-level parse/quality aggregate 확인 |

`prompts.jsonl`의 `prompt` field만 model input이다. 같은 row에 들어 있는 current-turn `gold_calls`는 분석 metadata다.

state-tree 기본 조건에서는 각 prompt row에 다음 metadata도 저장된다.

| field | 의미 |
|---|---|
| `state_view_mode` | `tree`, `none`, `raw` 중 사용된 state view mode |
| `state_view` | prompt에 삽입된 deterministic current environment state text |
| `state_view_config` | depth/entry/char limit과 file-content 포함 여부 |
| `state_view_replay_turn_index` | 이 state view가 어떤 current turn 시작 직전 상태인지 |
| `state_view_replay_uses_gold_previous_turns` | 이전 turn gold replay로 current state를 만든다는 표시 |

`generation_metrics.json`의 `run.state_view_modes`로 해당 run이 어떤 state view mode를 포함했는지 확인한다. 정상적인 기본 smoke run은 `["tree"]`만 가져야 한다.

## 7. Confidence trace

v2는 v1의 traceable LLaDA backend를 재사용한다. 생성 output 영역을 mask token으로 채운 뒤 block 단위로 denoising하고, token이 commit될 때 trace row를 남긴다.

`token_confidence.jsonl`의 핵심 field:

| field | 의미 |
|---|---|
| `block` | generated output을 `block_length` 단위로 나눈 block index |
| `commit_step` | 전체 denoising loop 기준 token이 확정된 step |
| `step_in_block` | 해당 block 내부 step |
| `position` | generated output token position |
| `token_text` | decoded token text |
| `confidence` | commit 순간 selected-token probability |
| `char_start`, `char_end` | decoded response 안 character span |

저장되는 confidence는 다음 값이다.

```text
confidence = softmax(logits)[selected_token]
```

이 값은 “최종 action이 맞을 확률”이 아니다. LLaDA denoising 중 해당 token을 commit하는 순간의 selected-token probability다.

기본 smoke 스크립트는 `gen_length=128`, `steps=128`, `block_length=32`를 사용한다. 따라서 output 128 token은 32 token짜리 4개 block으로 나뉘고, 각 block은 32 denoising step을 쓴다. 실제 run 해석에서는 `generation_metrics.json`의 `generation_config`도 함께 확인한다.

```text
block_length=32:
  output positions 0-31    -> block 0
  output positions 32-63   -> block 1
  output positions 64-95   -> block 2
  output positions 96-127  -> block 3
```

이 설정은 trace를 block 단위로 보기 좋게 만들지만, plan 문장이 block boundary를 넘을 때 앞 block의 action 번호, function name, argument가 먼저 확정되고 뒤 block이 그 결과에 맞춰지는 형태가 된다. 따라서 dependency reference나 multi-action plan coherence를 볼 때 block boundary 자체가 간섭 요인이 될 수 있다.

다음 우선순위의 ablation은 같은 prompt와 같은 `gen_length=128`, `steps=128`을 유지하되 `block_length=128`로 바꾸는 것이다. 이 경우 output 전체가 하나의 block 안에서 denoising되므로, `$id` reference와 뒤쪽 action이 앞쪽 action과 더 동시에 조정될 수 있는지 확인할 수 있다. 이 실험은 “성능 개선용 새 조건”이라기보다, 현재 `block_length=32` 결과가 block-wise generation artifact였는지 확인하는 control에 가깝다.

현재 trace는 committed token row만 저장한다. 따라서 다음은 직접 관측하지 않는다.

```text
same output position의 per-step confidence history
commit 전 top-k 후보 변화
uncommitted masked position의 confidence
confidence slope 또는 delta
```

### 7.1 Action confidence

action confidence는 `plan_units.jsonl`의 action span과 `token_confidence.jsonl`의 token span을 겹쳐서 계산한다. 여기서 action span은 parser가 인식한 **단일 numbered action line 전체**다.

예를 들어 raw response에 다음 줄이 있으면:

```text
1. get_zipcode_based_on_city(city="Rivermist")
```

parser는 이 줄을 다음처럼 나눈다.

| field | 값 | span 의미 |
|---|---|---|
| `raw_action` | `1. get_zipcode_based_on_city(city="Rivermist")` | parser가 인식한 action line 전체 |
| `tool_name` | `get_zipcode_based_on_city` | function name |
| `args_text` | `city="Rivermist"` | 괄호 안 argument string |
| `response_spans.action` | action line 전체 character span | `1.`부터 닫는 괄호까지 |
| `response_spans.function_name` | function name character span | `get_zipcode_based_on_city` 부분만 |

따라서 `Thought:`, `Observation:`, `<END_PLAN>`은 action span에 포함되지 않는다. 현재 parser는 한 줄짜리 `N. tool(args)` 형식을 action으로 잡으므로, multiline call은 action unit으로 잡히지 않을 수 있다.

예:

```text
1. find({
  "path": ".",
  "name": "test"
})
```

이런 multiline JSON-style call은 raw output에 action intent가 있어도 `response_spans.action`이 생성되지 않을 수 있다. 이 경우 token confidence는 존재하지만 action/function span confidence 집계에서는 빠진다.

action span confidence는 다음처럼 계산한다.

```text
action_confidence(unit)
  = mean(token.confidence
         for token in token_confidence
         if token span overlaps unit.response_spans.action)
```

function-name confidence도 같은 방식으로 계산하지만, overlap 대상은 function name span만이다.

```text
function_name_confidence(unit)
  = mean(token.confidence
         for token in token_confidence
         if token span overlaps unit.response_spans.function_name)
```

이 aggregation으로 다음을 비교할 수 있다.

```text
valid tool-name action vs invalid tool-name action
schema-valid action vs schema-invalid action
root action vs $id-referencing action
gold parallel layer action vs gold serial layer action
flat placeholder action vs explicit $id action
```

### 7.2 Commit-step 분석

`commit_step`은 token이 확정된 step이다. action span의 token commit_step을 평균 또는 분포로 모으면 다음 질문을 볼 수 있다.

```text
gold에서 parallel-safe인 action들이 비슷한 commit_step에 확정되는가?
gold에서 dependent한 action은 prerequisite action보다 늦게 확정되는가?
$id reference token은 action function name보다 늦게 확정되는가?
flat placeholder token은 explicit $id token과 다른 commit pattern을 보이는가?
```

이 분석은 아직 final result가 아니라, 보고서에서 채울 denoising signal 후보로 둔다.

## 8. 지표 정의

### 8.1 Format sanity

| metric | denominator | 의미 |
|---|---:|---|
| `format_parse_rate` | turn generations | parser가 numbered LLMCompiler-style plan을 구조화한 generation 비율 |
| `parse_error` 없음 | turn generations | id order, duplicate id, non-preceding reference, missing `<END_PLAN>`, invalid tool name 등이 없는지 |
| `n_units` | generation | parsed action node 수 |

`format_parse_rate`는 plan quality metric이 아니다. 모델이 형식적으로 plan grammar를 따랐는지를 먼저 확인하는 sanity metric이다.

### 8.2 Tool/action coverage

| metric | denominator | 의미 |
|---|---:|---|
| `valid_tool_name_units` | parsed units | generated `tool_name`이 provided function list에 존재하는 unit 수 |
| `invalid_tool_name_units` | parsed units | 제공되지 않은 tool name을 사용한 unit 수 |
| `generated_gold_call_delta` | generation | generated unit 수 minus current-turn gold call 수 |
| `duplicate_action_count` | generation | 같은 raw action이 반복된 횟수 |

`valid_tool_name_units`는 gold correctness가 아니다. 예를 들어 `multi_turn_base_3` turn 2에서 generated tool이 모두 provided function list에 있어도, gold가 `cd`, `cd`, `cp`, `cp`인데 generated가 `mv`, `mv`, `mkdir`, `mv`라면 tool-choice correctness는 낮다.

### 8.3 Schema validity

| metric | denominator | 의미 |
|---|---:|---|
| `schema_valid_units` | schema-checked units | required parameter가 있고 unknown parameter가 없는 unit 수 |
| `schema_invalid_units` | schema-checked units | required missing, unknown parameter, parse error 등이 있는 unit 수 |
| `schema_errors` | invalid units | unit별 schema error reason |

예를 들어 gold가 다음일 때:

```text
touch(file_name='DataSet1.csv')
```

generated가 다음이면:

```text
1. touch(arg="DataSet1.csv")
```

`touch`는 valid tool name이지만 schema-valid action은 아니다. `touch` schema는 `file_name`을 required parameter로 요구하고, `arg` parameter는 없다. 따라서 `schema_errors`에는 `missing_required: file_name; unknown_parameters: arg`가 들어간다.

### 8.4 의존/reference behavior

| metric | denominator | 의미 |
|---|---:|---|
| `dependency_edge_count` | generation 또는 run | parsed `$id` reference 수 |
| `flat_reference_violation_count` | flat condition generations | flat condition에서 `$id` reference가 생성된 횟수 |
| `has_flat_reference_violation` | flat condition generation | flat contract 위반 여부 |

explicit condition에서 `$id` reference는 의도된 signal이다. flat condition에서 `$id` reference는 contract violation이다.

예:

```text
1. find(path=".", name="test")
2. cat(file_name=$1.matches[0])
```

이 plan은 `dependency_edge_count=1`이다. explicit condition에서는 current-plan result use로 해석한다. flat condition에서는 같은 syntax가 나오면 `flat_reference_violation_count`에 잡힌다.

### 8.5 Gold DAG alignment 후보 지표

현재 runner가 generation 중에 최종 gold matching score를 내지는 않는다. gold alignment는 generation 이후 post-hoc 단계에서 계산한다.

현재 `generation_metrics.json`와 `plan_units.jsonl`에서 자동 계산되는 것은 다음 수준이다.

| 현재 계산됨 | 의미 | 한계 |
|---|---|---|
| `gold_tool_names` | current turn gold call에서 tool name만 추출 | gold hop별 argument, dependency, layer와 연결되지 않음 |
| `generated_tool_names` | generated unit의 `tool_name` 목록 | 순서/중복/tool-choice mismatch를 정밀 평가하지 않음 |
| `generated_gold_call_delta` | generated unit 수 minus current-turn gold call 수 | action 수 sanity일 뿐 correctness가 아님 |
| `dependency_edge_count` | generated `$id` reference 수 | gold dependency와 align되는지 판단하지 않음 |

즉 generation 산출물만으로는 generated unit이 어떤 `gold_hop_id`와 매칭되는지 판단할 수 없다. 따라서 generated `$id` edge가 gold dependency edge와 맞는지, gold antichain pair를 불필요하게 serialize했는지는 post-hoc matcher 또는 judge가 필요하다.

gold dependency alignment를 보려면 post-hoc matching 단계가 필요하다.

```text
1. generated unit을 current-turn gold hop 후보와 매칭한다.
2. 매칭된 unit에 gold_hop_id, gold layer, predecessor/successor 정보를 붙인다.
3. generated edge u_i -> u_j가 있을 때,
   matched gold hop h_i -> h_j가 gold graph의 dependency edge인지 확인한다.
4. gold antichain pair h_a, h_b에 대응하는 generated units 사이에
   불필요한 $id reference가 생겼는지 확인한다.
```

| candidate metric | 의미 |
|---|---|
| tool set recall | current-turn gold tool set 중 generated tool set이 덮은 비율 |
| tool multiset match | repeated tool까지 포함한 multiset 일치 |
| gold antichain preservation | gold parallel pair가 generated plan에서도 서로 `$id` 없이 분리되는지 |
| unnecessary reference rate | gold independent pair 사이에 generated `$id` reference가 생긴 비율 |
| missing reference rate | gold dependent pair가 generated plan에서 reference 없이 놓인 비율 |
| compactness | generated unit 수가 gold call 수 대비 얼마나 과하거나 부족한지 |

### 8.6 Post-hoc v2 matcher

`src/match_v2_outputs.py`는 v2 generation output을 수정하지 않고, 별도 matcher artifact만 생성하는 post-hoc 분석 스크립트다. 목적은 generated numbered action unit을 current-turn gold hop에 연결한 뒤, generated `$id` edge가 gold DAG edge 또는 gold antichain 구조와 어떻게 맞는지 보는 것이다.

입력은 run output directory의 `plan_units.jsonl`, `prompts.jsonl`과 BFCL gold DAG annotation이다. 출력은 같은 directory 안에 다음 파일로 저장된다.

| file | 의미 |
|---|---|
| `v2_match_candidates.jsonl` | generated unit별 current-turn gold hop 후보와 deterministic score |
| `v2_matches.jsonl` | generated unit별 resolved `primary_hop_id`, match strength, duplicate 여부 |
| `v2_dependency_alignment.jsonl` | generated edge와 gold dependency/antichain alignment 판정 |
| `v2_match_metrics.json` | action matching과 dependency alignment의 run-level summary |

이 matcher는 v2의 P0 deterministic matcher다. v2 output은 이미 `tool_name`, `args_text`, `dependencies`, `response_spans`가 구조화되어 있으므로 exact tool name, argument token overlap, schema diagnostics만으로 빠른 1차 matching을 수행한다.

현재 MVP의 matching rule은 다음처럼 보수적이다.

```text
1. current-turn graph_stats.gold_hop_ids만 candidate로 사용한다.
2. exact normalized tool name match를 강한 anchor로 둔다.
3. argument token / parameter overlap은 tie-breaker와 보조 score로 쓴다.
4. $1.result, $1.matches[0], <placeholder>는 unresolved input으로 기록하고
   literal mismatch만으로 즉시 실패시키지 않는다.
5. score threshold 미만 unit은 unmatched로 남긴다.
```

P0 matcher만으로도 다음을 빠르게 볼 수 있다.

```text
generated action이 어떤 gold_hop_id에 붙었는지
generated $id edge의 양끝이 gold hop에 매칭됐는지
generated edge가 gold direct dependency인지, ancestor relation인지
gold antichain pair를 불필요하게 serialize했는지
gold current-turn dependency가 generated plan에서 누락됐는지
```

하지만 P0 matcher는 final correctness judge가 아니다. 다음 케이스는 deterministic rule만으로 안정적으로 판정하기 어렵다.

| ambiguous case | 예 | P0 한계 |
|---|---|---|
| schema-invalid but semantically right | `lockDoors(arg={"unlock": true, ...})` vs `lockDoors({"unlock": true, ...})` | `arg`/`param` wrapper 때문에 schema-invalid지만 action intent는 맞을 수 있음 |
| same tool but wrong value | `lockDoors(unlock=True)` vs gold `unlock=False` | same tool anchor가 강해서 과대평가될 수 있음 |
| semantic tool synonym | `calculate_distance(...)` vs `estimate_distance(...)` | tool name mismatch 때문에 과소평가될 수 있음 |
| decomposition mismatch | `find_file -> read_file` vs `cd -> cd -> tail` | generated plan intent는 유사하지만 hop boundary가 다름 |
| duplicate action | 같은 generated action이 반복됨 | one-to-one resolver 때문에 하나는 matched, 나머지는 wrong으로 남을 수 있음 |
| hallucinated concrete value | prior result가 필요한 id를 임의 숫자로 채움 | argument token overlap만으로는 위험을 충분히 판단하지 못함 |

따라서 P0 deterministic 결과를 **단독 final correctness metric**으로 해석하는 것은 피하고, 다음 용도로 먼저 사용한다.

```text
1. 빠른 smoke sanity와 per-turn inspection
2. LLM-as-judge prompt에 넣을 candidate ordering / candidate_reason 제공
3. judge를 먼저 돌릴 boundary case triage
4. judge 이후 dependency alignment의 초기 implementation check
```

따라서 v2의 권장 방향은 v1처럼 모든 matching을 LLM-as-judge에 맡기는 것이 아니라, **P0 rule-based matcher를 primary matcher로 두고 LLM-as-judge는 경계 케이스를 보정하는 hybrid pipeline**이다. v1-style all-pairs judge는 공정 비교용 compatibility mode로 남기되, v2의 주 분석 metric으로는 쓰지 않는다.

### 8.7 Recommended hybrid matching pipeline

v2는 v1보다 출력이 구조화되어 있다. `tool_name`, `args_text`, `$id dependencies`, schema diagnostics, response span이 이미 파싱되어 있으므로, 이 구조 정보를 최대한 활용하는 것이 더 타당하다. LLM-as-judge는 semantic ambiguity와 rule-based false positive/false negative를 줄이는 보조 판정기로 둔다.

핵심 원칙은 다음이다.

```text
P0 deterministic matcher:
  broad coverage, dependency alignment, denoising 연결의 기본 anchor

P1 selective LLM-as-judge:
  P0가 헷갈리는 generated unit / gold hop pair만 semantic correction
```

#### 8.7.1 왜 hybrid가 기본인가

v1은 generated `[A]`가 자연어 action에 가까웠기 때문에 rule-based matching만으로 hop correspondence를 안정적으로 알기 어려웠다. 그래서 모든 gold hop을 candidate로 유지하고 pairwise LLM judge를 돌리는 방식이 필요했다.

v2는 상황이 다르다.

| v2 구조 정보 | hybrid에서의 역할 |
|---|---|
| `tool_name` | exact tool match와 invalid tool detection의 강한 anchor |
| `args_text` | parameter/value overlap, unresolved `$id`, placeholder 확인 |
| `dependencies` | generated DAG edge를 gold DAG로 lift하는 데 필요 |
| `schema_errors` | executable format error와 intent error를 분리 |
| `response_spans` | token confidence / commit step을 action span에 연결 |

이 정보를 버리고 all-pairs LLM judge만 주 분석으로 삼으면 비용이 늘고, judge variance가 dependency alignment에 섞인다. 특히 Q2는 generated `$id` edge와 denoising trace를 gold DAG에 붙이는 분석이므로, 지나치게 넓은 semantic match는 오히려 구조 해석을 흐릴 수 있다.

#### 8.7.2 P0 deterministic matcher

P0는 현재 `src/match_v2_outputs.py`가 담당한다.

P0의 책임:

```text
1. generated unit별 best/primary gold hop 후보 생성
2. exact tool / argument overlap / schema 기반 deterministic score 계산
3. duplicate primary match 표시
4. generated $id edge를 matched gold hop edge로 lift
5. gold dependency / antichain alignment의 1차 metric 생성
6. LLM judge가 필요한 ambiguous case 추출
```

P0 결과는 smoke/debug뿐 아니라 v2의 기본 matcher 결과로 사용한다. 단, 아래 P1 judge가 판정한 pair는 P1 결과로 override 또는 annotate한다.

#### 8.7.3 P1 selective LLM-as-judge

P1은 모든 pair를 judge하지 않는다. P0가 안정적으로 판단하기 어려운 high-impact pair만 LLM-as-judge에 보낸다.

P1 대상:

```text
1. P0 match_strength=wrong 이지만 best_candidate_score가 높은 pair
2. P0 partial이지만 schema-invalid인 pair
3. P0 exact/partial이지만 boolean, mode, numeric argument conflict가 의심되는 pair
4. invalid/synonym tool이지만 semantic candidate가 있는 pair
5. generated dependency edge endpoint가 unmatched인데 semantic match 가능성이 있는 pair
6. current turn의 Q2 dependency 분석에 직접 영향을 주는 pair
```

현재 smoke 결과에서 이런 후보는 `llm_judge_candidate_cases.*` 같은 audit artifact로 저장할 수 있다. 예시는 다음과 같다.

| category | 예 | judge가 필요한 이유 |
|---|---|---|
| schema-invalid partial | `lockDoors(arg={"unlock": true, ...})` vs `lockDoors({"unlock": true, ...})` | schema는 틀렸지만 action/input intent는 맞을 수 있음 |
| argument conflict | `lockDoors(unlock=True)` vs gold `unlock=False` | same tool이어도 의미가 반대라 wrong일 수 있음 |
| semantic synonym | `calculate_distance(...)` vs `estimate_distance(...)` | tool name mismatch 때문에 P0가 과소평가할 수 있음 |
| decomposition mismatch | `find_file -> read_file` vs `cd -> cd -> tail` | semantic plan intent와 hop boundary가 다름 |
| duplicate high-score unmatched | 같은 action 반복 중 하나만 primary로 선택됨 | over-generation인지 duplicate coverage인지 구분 필요 |

#### 8.7.4 Judge prompt unit rendering

P1 judge prompt는 v1 judge schema를 최대한 재사용하되, v2의 구조 정보를 함께 제공한다.

```text
GENERATED ACTION:
- unit_id: u3
- numbered_action: 3. estimate_distance(cityA=$1.zipcode, cityB=$2.zipcode)
- tool_name: estimate_distance
- args_text: cityA=$1.zipcode, cityB=$2.zipcode
- thought: Need zipcodes for both cities before estimating distance.
- current_plan_dependencies: [1, 2]
- unresolved_inputs: $1.zipcode, $2.zipcode
- schema_valid: true/false
- schema_error: ...
```

flat condition의 angle-bracket placeholder와 explicit condition의 `$id` reference는 unresolved input으로 취급한다.

```text
$1.zipcode                         -> unresolved input from current-plan action 1
<zipcode for Rivermist>             -> unresolved input placeholder
<distance from Rivermist to ...>     -> unresolved input placeholder
```

judge는 executable syntax 자체를 요구하지 않는다. 다만 generated action이 concrete value를 임의로 invent했는지, 또는 gold argument와 반대 값을 넣었는지는 엄격히 본다.

#### 8.7.5 Judge schema

P1 judge schema는 v1 schema와 호환되는 core fields를 유지한다.

| field | 값 | 의미 |
|---|---|---|
| `q1_action_relation` | exact / semantic / partial / no / unclear | generated action behavior와 candidate gold hop의 primary intent 관계 |
| `q2_input_relation` | compatible / partially_compatible / incompatible / unresolved_ok / not_applicable | generated input과 gold argument 관계 |
| `q3_extra_distinct_action` | yes / no / unclear | generated unit 하나가 candidate 외 다른 tool action까지 포함하는지 |
| `q4_hallucinated_argument` | yes / no / unclear | prior result가 필요한 값을 concrete value로 지어냈는지 |
| `candidate_action_covered` | bool | candidate hop이 이 generated unit에 의해 cover되는지 |
| `single_hop_match` | bool | 이 generated unit이 candidate hop 하나에 대응하는지 |
| `match_strength` | exact / semantic / partial / wrong / not_enough_information | 최종 pairwise match strength |
| `confidence` | 0.0-1.0 | judge confidence |
| `better_hop_hint` | string/null | 다른 hop이 더 맞아 보이면 hint만 제공 |
| `reason` | string | 짧은 근거 |

v2 전용 field는 auxiliary로만 추가한다. 예를 들어 `schema_surface_error_only`, `dependency_reference_ok`, `argument_conflict_type`을 추가할 수 있지만, v1 호환 metric에는 직접 사용하지 않는다.

#### 8.7.6 Hybrid resolver

Hybrid resolver는 P0 결과를 기본값으로 두고, P1 judge 결과가 있는 pair만 보정한다.

```text
for each generated unit:
  start from P0 candidate scores and P0 primary match
  apply P1 overrides:
    - semantic rescue: P0 wrong -> judge semantic/partial/exact
    - conflict downgrade: P0 exact/partial -> judge wrong due to input conflict
    - schema rescue: schema-invalid but judge says action/input compatible
    - duplicate clarification: repeated unit vs distinct coverage

  choose primary match by:
    judge match_strength if judged
    otherwise P0 match_strength
    single_hop_match
    judge confidence if available
    P0 deterministic score
```

같은 gold hop에 여러 generated unit이 붙으면 가장 좋은 unit만 recall numerator에 세고, 나머지는 `duplicate_primary_match=true`로 둔다. duplicate row는 버리지 않는다. over-generation과 repeated action failure를 분석하는 데 필요하기 때문이다.

#### 8.7.7 Hybrid output artifacts

Hybrid pipeline은 P0 파일을 덮어쓰지 않고 별도 파일을 만든다.

| file | 의미 |
|---|---|
| `v2_judge_candidate_cases.jsonl` | P1 judge 대상 pair와 추출 이유 |
| `v2_judge_pairwise.jsonl` | selective LLM judge 결과 |
| `v2_hybrid_matches.jsonl` | P0 + P1 override 이후 generated unit별 primary match |
| `v2_hybrid_dependency_alignment.jsonl` | hybrid match 기반 dependency/antichain alignment |
| `v2_hybrid_metrics.json` | v2 main action recovery / dependency metrics |
| `v2_hybrid_audit.md` | 사람이 확인할 high-impact case table |

#### 8.7.8 Main metrics

v2의 기본 보고 metric은 hybrid 결과를 사용한다.

| metric | denominator | 의미 |
|---|---:|---|
| `hybrid_matched_gold_hop_recall` | current-turn gold hops | duplicate 제거 후 exact/semantic/partial로 cover된 gold hop 비율 |
| `hybrid_strict_single_action_recall` | current-turn gold hops | exact behavior + compatible/unresolved_ok input + single-hop match |
| `hybrid_partial_or_better_recall` | current-turn gold hops | exact/semantic/partial까지 허용한 recall |
| `hybrid_matched_unit_rate` | generated units | generated unit 중 gold hop에 붙은 비율 |
| `hybrid_unmatched_action_rate` | generated units | 어떤 gold hop도 cover하지 못한 generated unit 비율 |
| `semantic_rescue_rate` | P1 judged P0-wrong candidates | P0가 놓쳤지만 judge가 살린 비율 |
| `conflict_downgrade_rate` | P1 judged P0-matched candidates | P0가 맞다고 봤지만 judge가 wrong으로 내린 비율 |
| `schema_surface_error_rate` | P1 judged schema-invalid matches | syntax/schema 표면 오류지만 action intent는 맞는 비율 |
| `hybrid_false_serialization_count` | generated dependency edges | gold independent pair 사이에 생긴 generated dependency |
| `hybrid_missing_dependency_count` | gold dependency edges | matched units 사이에 generated dependency path가 없는 gold edge |

Q1 action recovery에는 full hybrid metric을 쓴다. Q2 dependency/denoising 분석에는 더 보수적인 subset도 함께 보고한다.

```text
Q1 subset:
  exact / semantic / partial hybrid matches

Q2 strict subset:
  exact or high-confidence semantic matches
  no argument conflict
  not compound
  dependency endpoint both matched
```

이렇게 나누는 이유는 semantic rescue가 Q1에는 도움이 되지만, Q2 DAG alignment에서는 지나치게 넓은 hop correspondence가 dependency 구조를 흐릴 수 있기 때문이다.

#### 8.7.9 Dependency alignment after hybrid matching

Hybrid match가 생기면 dependency alignment는 다음 순서로 다시 계산한다.

```text
1. generated unit u_i의 hybrid primary_hop_id를 가져온다.
2. generated dependency edge u_i -> u_j를 hybrid hop edge h_i -> h_j로 lift한다.
3. h_i -> h_j가 gold direct edge인지, ancestor edge인지, reverse edge인지,
   false serialization인지 판정한다.
4. gold dependency h_a -> h_b가 있을 때 hybrid matched units 사이에 generated path가 있는지 확인한다.
5. gold antichain pair h_a, h_b가 있을 때 generated $id path가 생겼는지 확인한다.
```

최종 Q2 해석은 hybrid strict subset과 denoising trace를 연결해서 한다. 즉 `$id`가 많이 나왔다는 사실만으로 dependency structure를 맞췄다고 말하지 않는다.

## 9. 분석 방식 예시

이 섹션의 예시는 최종 결과가 아니라, 지표가 어떻게 해석되는지 보여주는 실제 산출물 기반 예시다.

### 9.1 `multi_turn_base_35` turn 0: state view가 필요한 이유

Current user:

```text
Find a file named 'config.py' somewhere deep in the file system and once you have located it, display the last line of the first occuring file.
```

Gold:

```text
cd(folder='projects')
cd(folder='deep_folder')
tail(file_name='config.py', lines=1)
```

state-blind prompt에서는 `projects`와 `deep_folder`가 user query에 보이지 않는다. 따라서 model이 `find(path=".", name="config.py")` 같은 exploratory action을 계획하는 것은 task intent 관점에서 자연스럽지만, static gold-hop matching에서는 `cd -> cd -> tail`과 맞지 않는다.

state-tree 기본 prompt는 current turn 시작 직전 상태를 다음처럼 제공한다.

```text
Current Environment State:
GorillaFileSystem:
cwd: /alex
tree:
- alex/
  - projects/
    - deep_folder/
      - config.py
      - real_config.py
  - temp/
    - <empty>
```

이 조건에서는 `projects/deep_folder/config.py`가 observable하므로 resolved static plan인 `cd -> cd -> tail`을 gold-hop matching 대상으로 삼는 것이 더 공정하다.

주의: 아래 `multi_turn_base_3`, `multi_turn_base_15` 예시는 state-tree 기본 전환 이전의 legacy smoke artifact에서 온 사례다. 새 `state_view=tree` 결과의 대표 사례는 20-overlap run 이후 별도로 갱신한다.

### 9.2 `multi_turn_base_3` turn 1: over-generation과 `$id` reference

Current user:

```text
As part of my latest photography project, I need to gather files that have 'test'
in their name from any folder in my current directory.
```

Gold:

```text
find(path='.', name='test')
```

`smoke_explicit` generated:

```text
1. find(arg={"path": ".", "name": "test"})
2. cat(arg={"file_name": $1.matches[0]})
<END_PLAN>
```

분석:

| 관점 | 해석 |
|---|---|
| action count | generated 2 vs gold 1, `generated_gold_call_delta=1` |
| tool validity | `find`, `cat` 모두 provided tool name |
| schema validity | `arg` wrapper 때문에 both schema-invalid |
| reference | `cat`이 `$1.matches[0]`를 참조하므로 `dependency_edge_count=1` |
| compactness | user는 locate만 요구했는데 `cat`까지 추가되어 over-generation |

이 예시는 explicit condition에서 `$id` reference가 잘 파싱될 수 있음을 보여주지만, 동시에 reference가 있다고 해서 gold-correct plan은 아님을 보여준다.

### 9.3 `multi_turn_base_3` turn 2: gold parallel pair와 tool-choice mismatch

Gold:

```text
cd(folder='projects')
cd(folder='photography')
cp(source='test_image1.jpg', destination='backup_tests')
cp(source='test_document.txt', destination='backup_tests')
```

Gold DAG:

```text
turn_layers:
  [h2] -> [h3] -> [h4, h5]

intra_turn_antichain_pairs:
  [h4, h5]
```

`smoke_explicit` generated:

```text
1. mv(source="./projects/photography/test_image1.jpg",
      destination="./projects/photography/backup_tests/test_image1.jpg")
2. mv(source="./projects/photography/test_document.txt",
      destination="./projects/photography/backup_tests/test_document.txt")
3. mkdir(path="./projects/photography/backup_tests")
4. mv(source="./projects/photography/backup_tests",
      destination="./projects/photography/backup_tests/backup_tests/")
<END_PLAN>
```

분석:

| 관점 | 해석 |
|---|---|
| action count | generated 4 vs gold 4, count만 보면 맞음 |
| tool choice | gold는 `cd`, `cd`, `cp`, `cp`; generated는 `mv`, `mv`, `mkdir`, `mv` |
| schema validity | `mkdir(path=...)`는 schema가 요구하는 `dir_name`이 아니므로 invalid |
| parallel structure | gold의 two `cp`는 antichain pair지만 generated에는 correct `cp` pair가 없음 |
| conclusion | action count sanity만으로는 성공으로 볼 수 없고, tool set/schema/DAG alignment가 필요 |

이 예시는 `generated_gold_call_delta=0`이어도 plan quality가 낮을 수 있음을 보여준다.

### 9.4 `multi_turn_base_15` turn 1: exact tool name but wrong parameter

Gold:

```text
touch(file_name='DataSet1.csv')
```

`smoke_explicit` generated:

```text
1. touch(arg="DataSet1.csv")
<END_PLAN>
```

분석:

| 관점 | 해석 |
|---|---|
| tool validity | `touch`는 provided tool name |
| action count | generated 1 vs gold 1 |
| schema validity | `file_name` required missing, `arg` unknown |
| report implication | exact tool-name recovery와 executable schema correctness를 분리해서 봐야 함 |

이 예시는 `valid_tool_name_units`와 `schema_valid_units`를 분리한 이유를 보여준다.

## 10. Smoke condition별 분석 관점

### 10.1 `smoke_explicit_state_tree`

볼 것:

```text
valid_tool_name_units
schema_valid_units
dependency_edge_count
gold dependent pair와 generated $id edge alignment
gold antichain pair에서 불필요한 $id edge가 생기는지
action/function confidence by DAG layer
```

이 조건에서는 `$id` reference가 핵심 signal이다. 하지만 `$id`가 많다고 좋은 것은 아니다. gold에서 독립인 action pair 사이에 reference가 생기면 불필요한 serialization일 수 있다.

### 10.2 `smoke_flat_state_tree`

볼 것:

```text
format_parse_rate
valid_tool_name_units
schema_valid_units
flat_reference_violation_count
placeholder 사용 여부
gold action node coverage
commit_step / confidence signal without explicit $id
```

이 조건에서는 `$id` reference가 나오면 contract violation이다. 대신 result-dependent value는 짧은 angle-bracket placeholder로 남아야 한다.

예상 output style:

```text
1. get_zipcode_based_on_city(city="San Francisco")
2. get_zipcode_based_on_city(city="Rivermist")
3. estimate_distance(cityA="<zipcode for San Francisco>", cityB="<zipcode for Rivermist>")
<END_PLAN>
```


## 11. 20-overlap `state_view=tree` 결과

이 섹션은 v1-v2 overlap 20 episodes에 대해 `state_view=tree`로 다시 실행한 `smoke_explicit_state_tree`와 `smoke_flat_state_tree` 결과를 정리한다. 두 run 모두 같은 20 episodes, 70 current-turn generations, 142 gold hops 위에서 비교한다.


둘 다 P0 deterministic matcher와 P1 selective LLM-as-judge hybrid matcher까지 완료됐다. P1 judge error는 두 condition 모두 0이다.

### 11.1 Run coverage

| condition | state view | episodes | turn generations | parsed generations | total units | notes |
|---|---|---:|---:|---:|---:|---|
| `smoke_explicit_state_tree` | `tree` | 20 | 70 | 70 | 149 | P0 rows 149, P1 judged pairs 61 |
| `smoke_flat_state_tree` | `tree` | 20 | 70 | 70 | 130 | P0 rows 130, P1 judged pairs 52 |

두 condition 모두 `format_parse_rate=1.0`이지만, 이것은 parser가 numbered action surface를 구조화했다는 뜻이지 action correctness를 뜻하지 않는다. explicit은 flat보다 19개 더 많은 action unit을 만들었고, over-generation도 더 많았다.

### 11.1.1 State View Sanity

| condition | state_view_modes | empty state views | missing from prompt | replay notes | truncation notes |
|---|---|---:|---:|---:|---:|
| `smoke_explicit_state_tree` | `["tree"]` | 0 | 0 | 0 | 0 |
| `smoke_flat_state_tree` | `["tree"]` | 0 | 0 | 0 | 0 |

두 run의 prompt row는 모두 `Current Environment State`를 포함한다. `state_view_config`는 `include_file_content=false`, `max_depth=6`, `max_entries=200`, `max_chars=6000`이며, 실제 최대 state view 길이는 2872 characters였다. 따라서 이 비교에서 `multi_turn_base_35` 같은 filesystem path 문제는 state view 누락 때문이 아니라, 모델이 제공 tool/schema를 얼마나 잘 따랐는지의 문제로 해석해야 한다.

### 11.2 Format sanity

| condition | `format_parse_rate` | missing `<END_PLAN>` | parse errors | duplicate actions |
|---|---:|---:|---:|---:|
| `smoke_explicit_state_tree` | 1.000 | 0 | 17 | 10 turns / 13 duplicates |
| `smoke_flat_state_tree` | 1.000 | 0 | 24 | 2 turns / 3 duplicates |

parse error의 대부분은 missing end marker가 아니라 invalid tool name이다. explicit은 invalid tool-name parse error가 16건이고 non-preceding `$1` reference error가 1건이었다. flat은 invalid tool-name parse error가 23건이고, `$10000`를 reference처럼 읽은 non-preceding dependency + invalid tool-name error가 1건 있었다.

zero-unit turn은 explicit 3개, flat 7개다. flat은 output contract를 더 강하게 제한했지만, 일부 turn에서 action line 대신 JSON-like object만 내거나 malformed function surface를 내면서 parsed unit이 더 적어졌다.

### 11.3 Tool/action coverage

| condition | valid tool units | invalid tool units | mean generated-gold delta | over-generated turns |
|---|---:|---:|---:|---:|
| `smoke_explicit_state_tree` | 126 / 149 | 23 / 149 | +0.10 | 27 / 70 |
| `smoke_flat_state_tree` | 99 / 130 | 31 / 130 | -0.17 | 20 / 70 |

explicit은 valid tool-name 비율이 높다.

```text
explicit valid tool rate: 126 / 149 = 0.846
flat valid tool rate:      99 / 130 = 0.762
```

하지만 explicit은 더 많은 unit을 생성하면서 duplicate와 over-generation도 늘었다. flat은 더 compact하지만 under-generation turn이 더 많다.

```text
explicit: over=27, under=21, equal=22
flat:     over=20, under=25, equal=25
```

따라서 flat이 compact하다는 사실과 action recovery가 좋다는 사실은 분리해서 봐야 한다.

### 11.4 Schema validity

| condition | schema valid units | schema invalid units | common schema errors |
|---|---:|---:|---|
| `smoke_explicit_state_tree` | 81 / 149 | 68 / 149 | `param=` wrapper, wrong parameter name, missing required field, missing tool schema |
| `smoke_flat_state_tree` | 67 / 130 | 63 / 130 | `arg=` wrapper, JSON-like malformed call, wrong parameter name, missing tool schema |

Schema-valid rate는 explicit이 조금 높다.

```text
explicit schema-valid rate: 81 / 149 = 0.544
flat schema-valid rate:     67 / 130 = 0.515
```

두 condition 모두 wrapper 문제가 반복된다. 예를 들어 `lockDoors(param={...})`, `setHeadlights(arg={...})`, `get_zipcode_based_on_city(arg={"city": ...})` 같은 surface는 tool name은 맞아도 schema check에서는 invalid다. P1 judge는 이런 schema surface error 중 일부를 partial로 rescue하지만, executable correctness로 간주하면 안 된다.

### 11.5 P0 / P1 Action Matching

P0는 deterministic matcher이고, P1은 P0 candidate 중 ambiguous/high-impact pair만 LLM-as-judge로 보정한 hybrid matcher다.

| condition | P0 matched gold recall | P0 strict single recall | P0 matched unit rate | P0 match counts |
|---|---:|---:|---:|---|
| `smoke_explicit_state_tree` | 0.401 | 0.211 | 0.383 | exact=30, partial=27, wrong=92 |
| `smoke_flat_state_tree` | 0.373 | 0.254 | 0.408 | exact=36, partial=17, wrong=77 |

P0 기준으로는 explicit이 gold-hop recall이 조금 높고, flat은 strict single recall과 matched unit rate가 높다. flat의 exact count도 36으로 explicit의 30보다 많다.

P1 hybrid 이후:

| condition | hybrid matched gold recall | hybrid strict single recall | hybrid matched unit rate | hybrid match counts |
|---|---:|---:|---:|---|
| `smoke_explicit_state_tree` | 0.366 | 0.169 | 0.396 | exact=26, semantic=3, partial=30, wrong=90 |
| `smoke_flat_state_tree` | 0.359 | 0.197 | 0.415 | exact=28, semantic=9, partial=17, wrong=76 |

P1 후 두 condition의 matched gold recall은 거의 비슷하다. explicit이 0.366, flat이 0.359로 차이는 0.007뿐이다. 반면 strict single recall은 flat이 높다.

```text
explicit hybrid strict single recall: 0.169
flat hybrid strict single recall:     0.197
```

P1은 단순히 score를 올리는 단계가 아니다. 두 condition 모두 P0 false positive를 downgrade했다.

| condition | judged pairs | semantic rescue rate | conflict downgrade rate | schema surface error rate |
|---|---:|---:|---:|---:|
| `smoke_explicit_state_tree` | 61 | 0.197 | 0.164 | 0.344 |
| `smoke_flat_state_tree` | 52 | 0.212 | 0.192 | 0.288 |

즉 P1 결과를 기준으로 보면, `$id`를 허용한 explicit이 action recovery에서 flat을 뚜렷하게 이겼다고 말하기 어렵다. 오히려 flat은 더 적은 unit으로 비슷한 hybrid recall을 냈고, exact/semantic strict 쪽은 약간 더 안정적이다.

### 11.6 의존/reference behavior

| condition | generated dependency edges | hybrid false serialization | hybrid missing dependency | missing dependency with unmatched endpoint | flat reference violations |
|---|---:|---:|---:|---:|---:|
| `smoke_explicit_state_tree` | 8 | 0 | 1 | 58 | N/A |
| `smoke_flat_state_tree` | 1 | 0 | 6 | 53 | 1 |

explicit은 `$id` reference를 허용했지만 generated dependency edge가 8개뿐이다. 그중 gold dependency로 안정적으로 align된 edge는 없다. hybrid dependency alignment의 generated-edge side는 다음처럼 남았다.

```text
explicit generated edge alignment:
  unmatched_both_endpoints=3
  unmatched_source=1
  unmatched_target=3
  same_gold_hop=1

flat generated edge alignment:
  unmatched_source=1
```

gold dependency check 59개 중 대부분은 generated endpoint가 gold hop에 매칭되지 않아 구조 비교 자체가 불가능했다. 따라서 현재 결과만으로는 LLaDA가 gold DAG dependency를 복구한다고 말할 수 없다.

flat은 원칙적으로 `$id` reference를 쓰면 안 되는 condition인데, 1개 flat reference violation이 발생했다. 전체적으로는 flat contract가 거의 지켜졌지만, dependency signal은 거의 사라졌다.

### 11.7 Denoising confidence

| condition | action confidence pattern | function-name confidence pattern | commit_step pattern | notable span-level cases |
|---|---|---|---|---|
| `smoke_explicit_state_tree` | valid tool 0.889 vs invalid 0.808; schema-valid 0.896 vs invalid 0.854 | valid tool 0.907 vs invalid 0.721; schema-valid 0.915 vs invalid 0.835 | dependency actions later: 45.5 vs root 29.8 | `$id` actions lower confidence, later commit |
| `smoke_flat_state_tree` | valid tool 0.906 vs invalid 0.832; schema-valid 0.918 vs invalid 0.858 | valid tool 0.916 vs invalid 0.771; schema-valid 0.921 vs invalid 0.839 | only 1 dependency action; not enough for dependency timing | exact actions highest confidence; semantic rescues lower |

Confidence는 surface-quality signal로는 유용하다. 두 condition 모두 valid tool name과 schema-valid action의 action/function-name confidence가 invalid surface보다 높다.

```text
explicit:
  valid tool action conf     0.889
  invalid tool action conf   0.808
  schema-valid action conf   0.896
  schema-invalid action conf 0.854

flat:
  valid tool action conf     0.906
  invalid tool action conf   0.832
  schema-valid action conf   0.918
  schema-invalid action conf 0.858
```

하지만 confidence는 직접적인 correctness predictor로는 약하다. covered action과 wrong action의 confidence 차이는 작다.

```text
explicit covered/wrong action conf: 0.883 / 0.873
flat covered/wrong action conf:     0.889 / 0.888
```

explicit에서는 generated dependency action이 root action과 구분되는 패턴을 보인다. confidence가 낮고 더 늦게 commit된다.

```text
explicit root actions:       action_conf=0.884, mean_commit_step=29.8
explicit dependency actions: action_conf=0.756, mean_commit_step=45.5
```

이것은 유용한 denoising diagnostic이지만, 해당 dependency edge가 gold dependency와 clean하게 align되지 않으므로 아직 gold DAG recovery의 증거는 아니다.

### 11.8 Notable cases

| case | condition | observation | interpretation |
|---|---|---|---|
| `multi_turn_base_35` turn 0 | explicit | State view shows `projects/deep_folder/config.py`, but generated `find_file/read_file`, which are not provided tools. | State view is present; failure is tool/schema grounding, not hidden path absence. |
| `multi_turn_base_35` turn 0 | flat | Generated JSON-like objects such as `{"path": "deep_folder", "file_name": "config.py"}` instead of valid tool calls. | Flat condition suppressed `$id`, but did not guarantee executable action syntax. |
| `multi_turn_base_39` turn 1 | explicit | Generated only three `echo(WebDevProjects/...)` actions; matched echo hops but missed `cd` and `touch`. | Model can recover content-writing intent while collapsing setup actions. |
| `multi_turn_base_39` turn 1 | flat | Recovered more of the file-creation trajectory than explicit and reached 7/10 episode-level gold recall. | Flat can be competitive when the action set is simple and no current-plan dependency is needed. |
| `multi_turn_base_50` turn 0 | flat | `lockDoors(arg={...})`, `setHeadlights(arg={...})`; P1 recovers intent but schema remains invalid. | Common wrapper failure: semantic intent is present, executable schema is not. |
| `multi_turn_base_62` turn 0 | both | Generated navigation/formatting helper tools instead of zipcode + distance + send-message chain. | The planner often invents plausible helper APIs when the required multi-hop API composition is harder. |
| `multi_turn_base_151` | both | Best episode family: 4/6 gold hops recovered by both conditions. | Travel/Twitter tasks with explicit values in prompt/previous observations are easier than hidden composition tasks. |
| `multi_turn_base_70` | both | Worst or near-worst: explicit 1/9, flat 0/9 hybrid episode recall. | Vehicle multi-step conditional control remains difficult; action count is too low and dependencies are missed. |

### 11.9 Bottom line

state-tree rerun은 input observability 문제를 해결했지만, 그 자체로 action recovery나 dependency recovery를 해결하지는 못했다.

```text
1. Both conditions produce parseable plans for all 70 turns.
2. Explicit produces more actions, more valid tool names, and more $id edges.
3. Flat produces fewer actions, fewer duplicates, and slightly better strict single-hop hybrid recall.
4. Hybrid matched gold-hop recall is nearly tied: explicit 0.366 vs flat 0.359.
5. Neither condition recovers gold dependency structure reliably.
6. Token confidence separates valid/schema-valid surfaces from invalid surfaces, but not correctness strongly enough.
```

보고서에 쓸 수 있는 가장 안전한 문장은 다음이다.

> `state_view=tree` makes hidden state observable and gives a fairer static planning input. Under that setting, explicit `$id` syntax does not yet yield a clear action-recovery advantage over flat planning. It creates more dependency-looking structure, but the generated edges mostly fail to align to gold DAG edges because many endpoint actions are unmatched or schema-invalid. The strongest positive signal is format/trace reliability and confidence separation for valid/schema-valid surface forms, not correct dependency recovery.

### 11.10 Subagent verification

별도 subagent가 두 output directory의 `generation_metrics.json`, `v2_match_metrics.json`, `v2_hybrid_metrics.json`을 원천 JSONL 파일과 대조해 재계산했다. 확인 대상은 `prompts.jsonl`, `plan_units.jsonl`, `v2_hybrid_matches.jsonl`, `v2_hybrid_dependency_alignment.jsonl`, `token_confidence.jsonl`이다.

검증 결과 저장된 metric과 재계산 값 사이의 불일치는 없었다.

추가 확인 사항:

```text
prompts/raw/plan_units coverage:
  explicit 70/70/70
  flat     70/70/70

state_view:
  explicit tree 70/70, nonempty 70/70
  flat     tree 70/70, nonempty 70/70
  paired explicit-flat state_view equality 70/70

literal "tree:" state views:
  explicit 7/70
  flat     7/70
```

`tree:` literal이 7개인 것은 filesystem class에서만 tree renderer가 쓰이고, 나머지 API class는 deterministic JSON-like public state renderer를 쓰기 때문이다. 따라서 state view sanity issue는 아니다.

## 12. 해석 경계

주의할 점:

```text
format_parse_rate는 plan quality가 아니다.
valid_tool_name_units는 gold correctness가 아니다.
schema_valid_units는 gold correctness가 아니다.
generated_gold_call_delta가 0이어도 tool choice가 틀릴 수 있다.
$id reference는 explicit condition에서는 signal이지만 flat condition에서는 violation이다.
confidence는 commit 순간 selected-token probability이지 정답 확률이 아니다.
gold DAG는 model input이 아니라 post-hoc analysis metadata다.
previous context는 oracle gold context다.
state-tree view는 current-turn gold를 쓰지 않지만 previous-turn gold replay는 사용한다.
state-tree run과 state-blind run은 input information이 다르므로 직접 성능 비교가 아니라 ablation으로 해석한다.
state-tree run은 official BFCL interactive execution이 아니라 hidden state를 deterministic text로 노출한 static planning diagnostic이다.
```

v2 README의 역할은 최종 결론을 미리 쓰는 것이 아니라, 보고서에서 어떤 질문과 지표로 `smoke_explicit_state_tree`, `smoke_flat_state_tree`을 비교할지 고정하는 것이다.
