# think_parallel_v2 state-view analysis report

이 보고서는 `think_parallel_v2`의 20-episode smoke 실험을 보고서 형태로 정리한 것이다. 목적은 실행 방법이나 산출물 파일 설명이 아니라, v1에서 v2로 무엇이 바뀌었고, 그 설계가 어떤 결과와 해석으로 이어졌는지를 핵심 위주로 설명하는 것이다.

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

이번 state-view rerun에서 비교한 조건은 두 가지다.

| condition | mode | 역할 |
|---|---|---|
| `smoke_explicit_state_tree` | `llmcompiler_explicit_dag` | deterministic current state view를 보고, current-plan 결과가 필요한 argument를 `$id` 또는 `$id.field`로 표현하는 explicit DAG condition. |
| `smoke_flat_state_tree` | `llmcompiler_flat_plan` | deterministic current state view를 보고, numbered action reference를 argument 안에 쓰지 않는 flat plan condition. result-dependent argument는 angle-bracket placeholder로 둔다. |

두 조건의 비교 의도는 단순하다. 같은 state view 위에서 `$id` reference를 직접 허용할 때와 금지할 때, action recovery와 dependency/denoising signal이 어떻게 달라지는지를 본다.

## 2. 실험 설계

### 2.1 Episode는 유지하고 turn마다 생성한다

BFCL `multi_turn_base` record는 여러 user turn을 포함한다. v2는 turn을 독립 sample로 완전히 떼어내지 않고 full episode를 유지한다. 다만 모델 호출은 current turn마다 한 번씩 수행한다.

```text
selected episode:
  turn 1 -> one model generation
  turn 2 -> one model generation with turn 1 previous context
  turn 3 -> one model generation with turn 1-2 previous context
```

즉 episode 하나를 한 번의 model call로 처리하는 것이 아니라, episode 안의 각 user turn마다 별도의 generation을 수행한다. 현재 기본 smoke set처럼 20 episodes가 70 turns를 포함하면 condition 하나당 70번의 model generation이 발생한다.

이 설계의 목적은 current-turn planning을 보면서도, 이전 turn의 state와 observation은 oracle context로 제공하는 것이다.

### 2.2 Previous context는 oracle context다

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

### 2.3 Current turn gold는 metadata다

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

### 2.4 Smoke episode selection

현재 smoke run의 기본 episode set은 전체 `multi_turn_base` 200개에서 무작위로 고른 set이 아니다. 준비된 prompt는 graph annotation이 있으며 같은 turn 안에 병렬 가능한 gold action pair가 있는 episode만 남긴다.

```text
episode_filter=intra_turn_parallel:
  has graph annotation
  turn_bound_max_width >= 2
  n_intra_turn_antichain_pairs > 0
```

그 위에서 smoke run의 기본 `SMOKE_IDS`는 v1 50-sample run과 v2 intra-turn-parallel 73-episode prepared set이 겹치는 20개 episode로 둔다. 목적은 v1의 full-trajectory `[A]` judge 결과와 v2의 LLMCompiler-style explicit/flat 결과를 같은 episode 위에서 비교할 수 있게 만드는 것이다.

따라서 이 set은 전체 BFCL 대표 표본이라기보다, **v1-v2 비교 가능성과 intra-turn parallel structure를 동시에 만족하는 diagnostic comparison set**이다.

### 2.5 Current environment state view를 제공한다

초기 v2 결과에서 가장 큰 문제는 user query만 보고는 숨겨진 파일 경로나 내부 id를 알 수 없는 case가 있다는 점이었다. 예를 들어 사용자가 다음처럼 말한다고 하자.

```text
Find a file named 'config.py' somewhere deep in the file system
and once you have located it, display the last line of the first occurring file.
```

gold trajectory는 다음과 같을 수 있다.

```text
cd(folder='projects')
cd(folder='deep_folder')
tail(file_name='config.py', lines=1)
```

하지만 user query에는 `projects/deep_folder`가 직접 나오지 않는다. 이 상태에서 모델이 `find_file` 같은 제공되지 않은 helper tool을 상상하는 것은 단순한 planning 실패라기보다, 입력 정보 부족과 섞여 있다.

그래서 v2 state-tree 실험에서는 current turn 직전의 environment state를 deterministic text로 prompt에 넣는다.

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

이 state view는 LLM summary가 아니다. BFCL `initial_config`에서 시작해 이전 turn의 gold calls만 replay한 뒤 rule-based renderer로 만든다. current turn gold call은 state view 생성에 사용하지 않는다.

### 2.6 State view는 진단용 설정이다

`state_view=tree`는 official BFCL interactive inference와 같지 않다. 실제 BFCL runner라면 모델이 tool을 호출하고 observation을 받아 다음 step을 이어간다. 반면 여기서는 실행 전에 현재 상태를 text로 보여주고, 그 상태를 바탕으로 plan을 한 번에 만들게 한다.

특히 filesystem이 아닌 API에서는 generic renderer가 public state를 JSON-like text로 보여준다. 따라서 synthetic `access_token`, `password`, `card_number`처럼 보이는 key가 prompt에 들어갈 수 있다. 이것은 보안적으로 정제된 prompt가 아니라, hidden execution state를 일부러 드러내는 진단 설정이다.

이 점 때문에 state-tree 결과는 "모델이 실제 BFCL 환경에서 이렇게 행동한다"가 아니라, "현재 상태가 보이는 조건에서도 plan recovery가 되는가"로 해석해야 한다.

## 3. 프롬프트 설계

### 3.1 System prompt의 공통 목적

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

### 3.2 `smoke_explicit_state_tree`

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

### 3.3 `smoke_flat_state_tree`

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

## 4. Confidence trace

v2는 v1의 traceable LLaDA backend를 재사용한다. 생성 output 영역을 mask token으로 채운 뒤 block 단위로 denoising하고, token이 commit될 때 trace row를 남긴다.

`token_confidence`의 핵심 field는 다음이다.

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

이 값은 "최종 action이 맞을 확률"이 아니다. LLaDA denoising 중 해당 token을 commit하는 순간의 selected-token probability다.

이번 20-overlap state-tree run은 `gen_length=128`, `steps=128`, `block_length=128`로 실행했다. 즉 output 128 token 전체를 하나의 block 안에서 denoising했다.

```text
block_length=128:
  output positions 0-127 -> block 0
```

이 설정을 사용한 이유는 plan coherence와 dependency reference를 볼 때 block boundary가 별도 간섭 요인이 되지 않게 하기 위해서다. `block_length=32`처럼 output을 4개 block으로 나누면, 앞 block의 action 번호, function name, argument가 먼저 확정되고 뒤 block이 그 결과에 맞춰지는 형태가 될 수 있다. 그러면 `$id` reference나 뒤쪽 action의 commit pattern이 모델의 dependency planning 때문인지, block-wise generation artifact 때문인지 해석이 어려워진다.

따라서 이번 run에서는 output 전체를 하나의 block에서 denoise하게 두고, `$id` reference와 뒤쪽 action이 앞쪽 action과 더 동시에 조정될 수 있는 조건으로 맞췄다. 이 선택은 성능 개선용 trick이라기보다, dependency/commit-step 분석에서 block boundary confound를 줄이기 위한 control이다.

현재 trace는 committed token row만 저장한다. 따라서 다음은 직접 관측하지 않는다.

```text
same output position의 per-step confidence history
commit 전 top-k 후보 변화
uncommitted masked position의 confidence
confidence slope 또는 delta
```

### 4.1 Action confidence

action confidence는 parsed action span과 token span을 겹쳐서 계산한다. 여기서 action span은 parser가 인식한 **단일 numbered action line 전체**다.

예를 들어 raw response에 다음 줄이 있으면:

```text
1. get_zipcode_based_on_city(city="Rivermist")
```

parser는 이 줄을 function name, arguments, action span으로 나눈다. `Thought:`, `Observation:`, `<END_PLAN>`은 action span에 포함되지 않는다.

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

이 aggregation으로 valid tool-name action과 invalid tool-name action, schema-valid action과 schema-invalid action, root action과 `$id`-referencing action을 비교할 수 있다.

### 4.2 Commit-step 분석

`commit_step`은 token이 확정된 step이다. action span의 token commit_step을 평균 또는 분포로 모으면 다음 질문을 볼 수 있다.

```text
gold에서 parallel-safe인 action들이 비슷한 commit_step에 확정되는가?
gold에서 dependent한 action은 prerequisite action보다 늦게 확정되는가?
$id reference token은 action function name보다 늦게 확정되는가?
flat placeholder token은 explicit $id token과 다른 commit pattern을 보이는가?
```

다만 이 분석은 correctness metric이 아니다. denoising trace가 병렬/순차 구조와 연결될 수 있는 후보 신호인지를 보는 보조 분석이다.

## 5. Matcher와 평가 방식

### 5.1 v1 matcher에서 v2 matcher로

v1은 generated `[A]`가 자연어 action에 가까웠기 때문에 rule-based matching만으로 hop correspondence를 안정적으로 알기 어려웠다. 그래서 모든 gold hop을 candidate로 유지하고 pairwise LLM judge를 돌리는 방식이 필요했다.

v2는 출력이 더 구조화되어 있다. `tool_name`, `args_text`, `$id dependencies`, schema diagnostics, response span이 이미 파싱되어 있으므로, 이 구조 정보를 먼저 활용하는 것이 더 타당하다.

| v2 구조 정보 | matcher에서의 역할 |
|---|---|
| `tool_name` | exact tool match와 invalid tool detection의 강한 anchor |
| `args_text` | parameter/value overlap, unresolved `$id`, placeholder 확인 |
| `dependencies` | generated DAG edge를 gold DAG로 lift하는 데 필요 |
| `schema_errors` | executable format error와 intent error를 분리 |
| `response_spans` | token confidence / commit step을 action span에 연결 |

따라서 v2는 v1처럼 모든 matching을 LLM-as-judge에 맡기지 않는다. P0 rule-based matcher를 primary matcher로 두고, LLM-as-judge는 경계 케이스를 보정하는 hybrid pipeline으로 구성한다.

### 5.2 P0 deterministic matcher

P0는 v2 generation output을 수정하지 않고, generated numbered action unit을 current-turn gold hop에 연결한다. 목적은 generated action이 어떤 gold hop에 붙는지 확인하고, generated `$id` edge가 gold DAG edge 또는 gold antichain 구조와 어떻게 맞는지 보는 것이다.

P0의 책임은 다음이다.

```text
1. generated unit별 best/primary gold hop 후보 생성
2. exact tool / argument overlap / schema 기반 deterministic score 계산
3. duplicate primary match 표시
4. generated $id edge를 matched gold hop edge로 lift
5. gold dependency / antichain alignment의 1차 metric 생성
6. LLM judge가 필요한 ambiguous case 추출
```

P0 matching rule은 보수적이다.

```text
1. current-turn graph_stats.gold_hop_ids만 candidate로 사용한다.
2. exact normalized tool name match를 강한 anchor로 둔다.
3. argument token / parameter overlap은 tie-breaker와 보조 score로 쓴다.
4. $1.result, $1.matches[0], <placeholder>는 unresolved input으로 기록하고
   literal mismatch만으로 즉시 실패시키지 않는다.
5. score threshold 미만 unit은 unmatched로 남긴다.
```

하지만 P0는 final correctness judge가 아니다. schema는 틀렸지만 의미가 맞는 action, 같은 tool이지만 boolean 값이 반대인 action, semantic synonym, decomposition mismatch, duplicate action 같은 경우는 deterministic rule만으로 안정적으로 판정하기 어렵다.

### 5.3 P1 selective LLM-as-judge

P1은 모든 pair를 judge하지 않는다. P0가 안정적으로 판단하기 어려운 high-impact pair만 LLM-as-judge에 보낸다.

P1 대상은 다음과 같다.

```text
1. P0 match_strength=wrong 이지만 best_candidate_score가 높은 pair
2. P0 partial이지만 schema-invalid인 pair
3. P0 exact/partial이지만 boolean, mode, numeric argument conflict가 의심되는 pair
4. invalid/synonym tool이지만 semantic candidate가 있는 pair
5. generated dependency edge endpoint가 unmatched인데 semantic match 가능성이 있는 pair
6. current turn의 Q2 dependency 분석에 직접 영향을 주는 pair
```

P1 judge prompt는 v1 judge schema를 최대한 재사용하되, v2의 구조 정보를 함께 제공한다.

```text
GENERATED ACTION:
- unit_id: u3
- numbered_action: 3. estimate_distance(cityA=$1.zipcode, cityB=$2.zipcode)
- tool_name: estimate_distance
- args_text: cityA=$1.zipcode, cityB=$2.zipcode
- current_plan_dependencies: [1, 2]
- unresolved_inputs: $1.zipcode, $2.zipcode
- schema_valid: true/false
```

flat condition의 angle-bracket placeholder와 explicit condition의 `$id` reference는 unresolved input으로 취급한다. judge는 executable syntax 자체를 요구하지 않는다. 다만 generated action이 concrete value를 임의로 invent했는지, 또는 gold argument와 반대 값을 넣었는지는 엄격히 본다.

### 5.4 Hybrid resolver

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

같은 gold hop에 여러 generated unit이 붙으면 가장 좋은 unit만 recall numerator에 세고, 나머지는 duplicate로 표시한다. duplicate row는 버리지 않는다. over-generation과 repeated action failure를 분석하는 데 필요하기 때문이다.

v2의 기본 보고 metric은 P1 hybrid 결과를 사용한다. 다만 Q2 dependency/denoising 분석에서는 더 보수적인 subset도 함께 본다. `$id`가 많이 나왔다는 사실만으로 dependency structure를 맞췄다고 말하지 않기 위해서다.

### 5.5 평가 지표 해석

평가는 크게 네 층으로 본다.

| 층 | 보는 것 |
|---|---|
| format | numbered plan으로 parse되는가 |
| tool/schema | 제공된 tool을 쓰고, parameter schema를 지키는가 |
| action matching | generated action이 current-turn gold hop과 맞는가 |
| dependency | generated dependency edge가 gold DAG dependency와 맞는가 |

여기서 세 가지를 분리해야 한다.

```text
valid tool name은 정답 action이라는 뜻이 아니다.
schema-valid action도 gold와 맞는다는 뜻은 아니다.
confidence는 정답 확률이 아니다.
```

report의 기본 action recovery 숫자는 P1 hybrid 결과를 기준으로 한다. 핵심 metric의 denominator는 다음처럼 다르다.

| metric | denominator | 의미 |
|---|---:|---|
| `hybrid_matched_gold_hop_recall` | current-turn gold hops | duplicate를 제거한 뒤 exact/semantic/partial로 cover된 gold hop 비율 |
| `hybrid_strict_single_action_recall` | current-turn gold hops | exact behavior, compatible 또는 unresolved-ok input, single-hop match를 모두 만족한 gold hop 비율 |
| `hybrid_matched_unit_rate` | generated units | generated unit 중 어떤 gold hop에 exact/semantic/partial로 붙은 비율 |

따라서 `hybrid_matched_gold_hop_recall`과 `hybrid_strict_single_action_recall`은 gold 기준 recall이고, `hybrid_matched_unit_rate`는 generated action 기준 precision-like 지표에 가깝다. 두 종류의 denominator를 섞어 해석하면 안 된다.

## 6. 실험 결과

이 섹션은 v1-v2 overlap 20 episodes에 대해 `state_view=tree`로 다시 실행한 `smoke_explicit_state_tree`와 `smoke_flat_state_tree` 결과를 정리한다. 두 run 모두 같은 20 episodes, 70 current-turn generations, 142 gold hops 위에서 비교한다.

둘 다 P0 deterministic matcher와 P1 selective LLM-as-judge hybrid matcher까지 완료됐다. P1 judge error는 두 condition 모두 0이다.

### 6.1 Run coverage

| condition | state view | episodes | turn generations | parsed generations | total units | notes |
|---|---|---:|---:|---:|---:|---|
| `smoke_explicit_state_tree` | `tree` | 20 | 70 | 70 | 149 | P0 rows 149, P1 judged pairs 61 |
| `smoke_flat_state_tree` | `tree` | 20 | 70 | 70 | 130 | P0 rows 130, P1 judged pairs 52 |

두 condition 모두 `format_parse_rate=1.0`이지만, 이것은 parser가 numbered action surface를 구조화했다는 뜻이지 action correctness를 뜻하지 않는다. explicit은 flat보다 19개 더 많은 action unit을 만들었고, over-generation도 더 많았다.

### 6.2 State view sanity

| condition | state_view_modes | empty state views | missing from prompt | replay notes | truncation notes |
|---|---|---:|---:|---:|---:|
| `smoke_explicit_state_tree` | `["tree"]` | 0 | 0 | 0 | 0 |
| `smoke_flat_state_tree` | `["tree"]` | 0 | 0 | 0 | 0 |

두 run의 prompt row는 모두 `Current Environment State`를 포함한다. `state_view_config`는 `include_file_content=false`, `max_depth=6`, `max_entries=200`, `max_chars=6000`이며, 실제 최대 state view 길이는 2872 characters였다.

따라서 이 비교에서 `multi_turn_base_35` 같은 filesystem path 문제는 state view 누락 때문이 아니라, 모델이 제공 tool/schema를 얼마나 잘 따랐는지의 문제로 해석해야 한다.

### 6.3 Format sanity

| condition | `format_parse_rate` | missing `<END_PLAN>` | parse errors | duplicate actions |
|---|---:|---:|---:|---:|
| `smoke_explicit_state_tree` | 1.000 | 0 | 17 | 10 turns / 13 duplicates |
| `smoke_flat_state_tree` | 1.000 | 0 | 24 | 2 turns / 3 duplicates |

parse error의 대부분은 missing end marker가 아니라 invalid tool name이다. explicit은 invalid tool-name parse error가 16건이고 non-preceding `$1` reference error가 1건이었다. flat은 invalid tool-name parse error가 23건이고, `$10000`를 reference처럼 읽은 non-preceding dependency + invalid tool-name error가 1건 있었다.

zero-unit turn은 explicit 3개, flat 7개다. flat은 output contract를 더 강하게 제한했지만, 일부 turn에서 action line 대신 JSON-like object만 내거나 malformed function surface를 내면서 parsed unit이 더 적어졌다.

### 6.4 Tool/action coverage

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

### 6.5 Schema validity

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

### 6.6 P0 / P1 action matching

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

### 6.7 Dependency/reference behavior

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

### 6.8 Denoising confidence

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

### 6.9 Notable cases

| case | condition | observation | interpretation |
|---|---|---|---|
| `multi_turn_base_35` turn 0 | explicit | state view에 `projects/deep_folder/config.py`가 보이지만, 제공되지 않은 `find_file/read_file`을 생성했다. | state view는 들어갔다. 실패 원인은 hidden path 부재가 아니라 tool/schema grounding이다. |
| `multi_turn_base_35` turn 0 | flat | valid tool call 대신 `{"path": "deep_folder", "file_name": "config.py"}` 같은 JSON-like object를 생성했다. | flat 조건이 `$id`를 억제하더라도 executable action syntax를 보장하지는 않는다. |
| `multi_turn_base_39` turn 1 | explicit | `echo(WebDevProjects/...)` action 일부는 맞췄지만, 필요한 `cd`와 `touch`를 놓쳤다. | content-writing intent는 회복하지만 setup action을 collapse하는 패턴이다. |
| `multi_turn_base_39` turn 1 | flat | explicit보다 file-creation trajectory를 더 많이 회복했고 episode-level gold recall 7/10에 도달했다. | current-plan dependency가 거의 필요 없는 단순 action set에서는 flat도 경쟁력이 있다. |
| `multi_turn_base_50` turn 0 | flat | `lockDoors(arg={...})`, `setHeadlights(arg={...})`처럼 intent는 보이지만 schema-invalid인 call을 만들었다. | P1은 intent를 일부 rescue할 수 있지만, executable schema는 여전히 틀렸다. |
| `multi_turn_base_62` turn 0 | both | zipcode + distance + send-message chain 대신 navigation/formatting helper tool을 생성했다. | 필요한 multi-hop API composition이 어려울 때 그럴듯한 helper API를 invent하는 경향이 있다. |
| `multi_turn_base_151` | both | 두 조건 모두 6개 gold hop 중 4개를 회복한 가장 좋은 episode family였다. | prompt나 previous observation에 값이 명시된 Travel/Twitter task는 hidden composition task보다 쉽다. |
| `multi_turn_base_70` | both | explicit은 1/9, flat은 0/9 hybrid episode recall로 최하위권이었다. | Vehicle multi-step conditional control은 여전히 어렵고, action 수가 부족하며 dependency도 놓친다. |

### 6.10 Bottom line

state-tree rerun은 input observability 문제를 해결했지만, 그 자체로 action recovery나 dependency recovery를 해결하지는 못했다.

```text
1. 두 조건 모두 70개 turn 전체에서 parse 가능한 plan을 만들었다.
2. explicit은 더 많은 action, 더 많은 valid tool name, 더 많은 $id edge를 만들었다.
3. flat은 action 수와 duplicate가 더 적고, strict single-hop hybrid recall은 약간 더 높았다.
4. hybrid matched gold-hop recall은 거의 같다: explicit 0.366 vs flat 0.359.
5. 두 조건 모두 gold dependency structure를 안정적으로 복구하지 못했다.
6. token confidence는 valid/schema-valid surface와 invalid surface는 어느 정도 가르지만, correctness를 강하게 가르지는 못했다.
```


## 7. 결론

state-view rerun은 중요한 혼동을 줄였다. 이제 `multi_turn_base_35`처럼 user query만으로는 hidden path를 알기 어려운 case에서도, current state가 prompt에 들어간 상태로 모델을 평가할 수 있다.

그럼에도 action recovery는 제한적이었다. explicit `$id` 문법은 더 많은 dependency-looking structure를 만들었지만, gold DAG dependency와 안정적으로 맞지는 않았다. flat은 더 단순한 형식으로도 비슷한 action recall을 냈고, strict single-hop recall은 조금 더 높았다.

따라서 현재 v2 결과의 핵심은 다음이다.

```text
state를 보여주는 것만으로 planning 문제가 해결되지는 않는다.
dependency 문법을 주는 것만으로 dependency recovery가 생기지는 않는다.
v2의 가치는 성공률 향상보다 실패 원인을 분해해서 보는 데 있다.
```

## Appendix A. 분석 방식 예시

이 섹션의 예시는 최종 결과가 아니라, 지표가 어떻게 해석되는지 보여주는 실제 산출물 기반 예시다.

### A.1 `multi_turn_base_35` turn 0: state view가 필요한 이유

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

### A.2 `multi_turn_base_3` turn 1: over-generation과 `$id` reference

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

### A.3 `multi_turn_base_3` turn 2: gold parallel pair와 tool-choice mismatch

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

### A.4 `multi_turn_base_15` turn 1: exact tool name but wrong parameter

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
