# think_parallel_v1 analysis report

작성 대상 run:
`/home/ilju/research/DiffuAgent/think_parallel_v1/outputs/llada_think_parallel_20260515_180208`


## 1. 결론 요약

이번 `think_parallel_v1` run은 BFCL multi-turn task에서 LLaDA가 strict executable tool-call syntax를 맞추지 못하더라도, **gold trajectory의 hop 단위 action intent를 BFCL function name 중심 prompt로 회수할 수 있는지**를 보는 진단 실험이다. 이 run은 dependency/parallelism label을 직접 예측하는 실험이 아니다. 그 전 단계인 DLM이 agent task를 위한 think/action planning이 충분히 되는지 확인하기 위한 선행 실험이다.

핵심 질문은 다음 하나로 좁혔다.

> LLaDA가 BFCL function schema를 보고, full multi-turn user goal을 executable hop에 가까운 `[A]` action plan으로 얼마나 복구하는가?

핵심 결과는 다음과 같다. 표에는 보고서 해석에 직접 필요한 지표만 남겼다.

| 지표 | 값 | 한글 설명 |
|---|---:|---|
| 평가 sample 수 | 50 | 이번 run에서 생성과 judge 평가를 완료한 BFCL multi-turn sample 수 |
| gold hop 수 | 293 | 모델이 회수해야 하는 reference trajectory의 전체 tool-use hop 수 |
| 생성 action 수 | 172 | 모델이 실제로 만든 `[A]` action 수. gold hop 대비 58.7% 수준이라 under-generation을 바로 보여준다 |
| 형식 파싱 성공률 | 100.0% | 출력이 의도한 `[A#] Use ... Inputs: ...` 계열 형식으로 파싱된 비율 |
| strict single-action recall | 21.8% | exact behavior와 compatible input을 가진 단일 action이 gold hop과 일치하는 비율 |
| partial-or-better recall | 33.4% | exact/semantic/partial match까지 허용했을 때 gold hop을 회수한 비율 |
| function-name validity | 86.6% | 생성된 172개의 function name이 해당 sample의 schema에 실제 존재한 비율 |
| hallucinated argument rate | 19.8% | prior result가 필요한 값을 모델이 임의의 concrete value로 채운 generated action 비율 |

해석하면, v1 prompt/parser stack은 **형식 안정화에는 성공**했다. 50개 generation이 모두 파싱됐고, 모델 출력은 대부분 의도한 `[A#] Use <function_name>: ... Inputs: ...` 형식을 따랐다.

하지만 full trajectory recovery는 아직 낮다. LLaDA는 평균 gold hop 5.86개짜리 task에서 평균 3.44개 action만 생성했다. 50개 sample 중 44개에서 generated action 수가 gold hop 수보다 적었다. 따라서 낮은 recall의 주요 원인은 judge candidate retrieval 실패라기보다, 모델이 필요한 hop을 충분하게 생성하지 못한 데 있다.

## 2. 실험 설계

### 2.1 입력 데이터

입력은 BFCL v3의 `multi_turn_base` 50개 sample이다. 본 샘플은, Bitter Lesson 논문의 DiffuAgent 프레임워크의 whiltlist 목록이다.

각 sample의 `question`은 multi-turn 대화 구조다. 각 turn에서 user message만 뽑아서 다음처럼 붙여 `Gold Goal`을 만든다.

```text
[turn 1] first user request
[turn 2] second user request
...
```

즉 이번 run은 **offline full-trajectory planning** setting이다. 모델은 현재 turn prefix만 보는 것이 아니라, 해당 BFCL sample의 모든 user turn을 처음부터 한 번에 본다. gold goal을 보고 필요한 hop단위 action planning을 수행하고, 그 결과와  gold graph를 비교하여 평가한다.

### 2.2 Mode

이번 run의 generation mode는 `exact_name_a` 하나다.

```text
[A1] Use <exact_function_name>: <intended action>. Inputs: <entities, arguments, or result-dependent inputs>.
[A2] Use <exact_function_name>: <intended action>. Inputs: <entities, arguments, or result-dependent inputs>.
```

이 mode의 목적은 dependency 분석보다 앞선다. 먼저 모델이 exact BFCL function name을 anchor로 action intent를 얼마나 복구하는지 확인한다. 그래서 `[T]` thought line, dependency/precomputability claim, initial_config ablation은 이번 v1 run에서 제외했다.

## 3. v0와 v1의 차이

### 3.1 v0가 보던 것

`think_parallel_v0`역시 마찬가지로 BFCL multi-turn sample의 모든 user turn을 concat한 offline full-trajectory planning setting였다. v0의 중심 질문은 “LLaDA가 exact BFCL call을 만들지 못해도 tool-use think/action span을 만들 수 있는가?”였다.

대표 mode는 다음과 같다.

| v0 mode | 출력 | 입력 특징 | 목적 |
|---|---|---|---|
| `goal_tools_ta` | `[T]` + `[A]` | user goal + function schema | think/action plan 생성 |
| `goal_init_tools_ta` | `[T]` + `[A]` | user goal + initial_config + schema | 초기 상태 포함 효과 확인 |
| `goal_tools_a` | `[A]` only | user goal + schema | action-only baseline |
| `goal_init_tools_a` | `[A]` only | user goal + initial_config + schema | initial_config 포함 action baseline |

v0의 중요한 특징은 `[T]` span과 `[A]` span을 분리해 볼 수 있다는 점이었다. v0 metrics에는 gold dependency label별 `think_mean_confidence`, `action_mean_confidence`를 집계하는 코드가 있었다. 이 설계는 LLaDA denoising confidence와 dependency label 사이의 post-hoc 관계를 보기 위한 초안이었다.

다만 v0 출력은 다음 한계가 있었다.

- `[T]`가 실제 reasoning이라기보다 user request rephrasing으로 흐르는 경우가 많았다.
- `[T]` 한 줄 안에 여러 tool action이 합쳐지는 compound action이 자주 나왔다.
- gold hop과 생성한 `[T]`/`[A]`결과를 매칭하는 방식이 rule-based `action_hint` matching이라 v1의 LLM-as-a-judge metric과 직접 비교하기 어렵다.
- `initial_config` 포함 여부까지 동시에 보면서 독립변수가 많아졌다.
- `initial_config`는 BFCL 태스크의 사용자의 현재 상태, 환경 변수등을 의미한다.

### 3.2 v1이 좁힌 질문

v1은 질문을 다음처럼 좁혔다.

> dependency/parallelism을 보기 전에, LLaDA가 exact BFCL function name을 복사해 hop-level action을 회수할 수 있는가?

그래서 v1에서 제거한 것은 다음과 같다.

| 제거한 요소 | 제거 이유 |
|---|---|
| `[T]` thought line | thought confidence보다 action recovery를 먼저 안정화하기 위해 |
| `initial_config` prompt option | 현재 run의 독립변수를 줄이기 위해 |

v1에서 강화한 것은 exact function-name anchor다. v0에서는 `[A]`가 natural language action으로 허용됐지만, v1은 매 action이 `Use <exact_function_name>:`로 시작하도록 요구했다. `Inputs:` 필드도 추가해서 known literal argument와 result-dependent argument를 분리해 볼 수 있게 했다.

## 4. 프롬프트 설계

### 4.1 User prompt 구조

`exact_name_a` user prompt는 다음 구조다.

```text
You are an expert in planning tool use.

You are given a user request and a set of available BFCL functions.
Your task is not to call the functions.
Your task is to write a concise action-only plan for tool use.

Output format:
[A1] Use <exact_function_name>: <intended action>. Inputs: <entities, arguments, or result-dependent inputs>.
[A2] Use <exact_function_name>: <intended action>. Inputs: <entities, arguments, or result-dependent inputs>.

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
- If an input depends on an earlier result, describe that input naturally instead of guessing the concrete value.
- Use only the available functions.
- Include only actions needed to satisfy the user request.
- Do not add verification, inspection, or cleanup actions unless the user explicitly asks for them.
- Do not include extra text before or after the labeled actions.

User request:
{full_user_goal}

Output:
```

### 4.2 `Inputs:` 필드의 의도

`Inputs:`는 executable JSON argument를 요구하기 위한 필드가 아니다. 그 목적은 generated action의 argument grounding을 judge가 더 잘 볼 수 있게 하는 것이다.

예를 들어 user가 `log.txt`, `archive`, `Error`, `20 lines`를 명시했다면 generated action에 그 literal이 들어가야 한다.

```text
[A3] Use grep: Search for the keyword 'Error' in 'log.txt'. Inputs: {"file_name": "log.txt", "pattern": "Error"}
```

반대로 prior tool result가 있어야만 알 수 있는 값은 concrete value를 invent하지 말고 자연어로 unresolved dependency를 쓰도록 했다.

```text
[A2] Use get_order_details: retrieve details for the order just placed. Inputs: order_id from place_order result.
```

이 rule은 hallucinated argument를 줄이기 위한 것이다. 예를 들어 order id가 prior `place_order` 결과에서 나와야 하는데 `{"order_id": 1}`처럼 임의 숫자를 쓰면 judge는 hallucinated argument로 볼 수 있다.

## 5. 실험 파이프라인

### 5.1 Generation

`run_discovery.py`는 각 BFCL sample에 대해 prompt를 만들고 LLaDA backend를 호출한다. 결과는 `raw_generations.jsonl`에 저장된다.

중요 필드는 다음과 같다.

| 필드 | 의미 |
|---|---|
| `question_id` | BFCL sample id |
| `mode` | 이번 run에서는 `exact_name_a` |
| `goal` | full user goal string |
| `prompt` | system/user chat messages |
| `n_functions` | prompt에 들어간 available function 수 |
| `raw_response` | LLaDA 원문 출력 |
| `input_tokens`, `output_tokens` | tokenized prompt/output 길이 |
| `generation_config` | `gen_length`, `steps`, `block_length`, `temperature`, `threshold` |



### 5.2 Parsing

`parse_units.py`는 line-start label `[A#]`를 action boundary로 본다. 각 action segment에서 다음 필드를 추출한다.

| 필드 | 예 | 의미 |
|---|---|---|
| `tool_name` | `grep` | `Use <tool>:`에서 추출한 function name |
| `intent` | `Search for the keyword 'Error' in 'log.txt'` | colon 뒤 action description |
| `known_inputs` | `{"file_name": "log.txt", "pattern": "Error"}` | `Inputs:` 또는 `Known inputs:` 뒤 문자열 |
| `unresolved_inputs` | `order_id from place_order result` | `Unresolved inputs:` 뒤 문자열 |
| `raw_action` | full action line without label | judge에 들어가는 generated action |


### 5.3 Candidate generation

`candidate_generator.py`는 각 generated unit에 대해 같은 sample의 gold graph hop을 candidate로 붙인다. v0의 경우, rule-based filtering으로 생성한 action plan과 gold hop을 비교하여 action name이 일치하는 일부에 대해 llm-as-a-judge를 수행했다.

하지만 이 경우 filtering 에서 탈락한 후보들이 aciton plan의 의도를 갖지만 judge 후보에 포함되지 않는 경우가 발생했다. v1 judge에서는 실제 filtering을 하지 않고 **모든 gold hop을 candidate로 유지**했다.

gold hop이 candidate set에 없어서 recall이 낮아지는 경우를 제거했다.

이번 run의 pairwise judge 수는 다음처럼 결정된다.

```text
sum_over_generated_units(number of gold hops in that unit's sample) = 1066 pairwise judgments
```

### 5.4 Pairwise judge

Codex judge는 generated `[A]` 한 줄과 candidate gold hop 하나를 비교한다. judge는 전체 user goal과 전체 gold trajectory를 context로 보지만, 판정 대상은 현재 candidate pair 하나뿐이다.

judge 질문은 네 가지다.

| 질문 | 가능한 값 | 의미 |
|---|---|---|
| `q1_action_relation` | exact / semantic / partial / no / unclear | action behavior와 primary intent 관계 |
| `q2_input_relation` | compatible / partially_compatible / incompatible / unresolved_ok / not_applicable | generated input과 gold argument 관계 |
| `q3_extra_distinct_action` | yes / no / unclear | 한 `[A]`가 candidate 외 다른 action도 포함하는지 |
| `q4_hallucinated_argument` | yes / no / unclear | prior result가 필요한 concrete value를 지어냈는지 |

judge output은 `judge_pairwise.jsonl`에 저장된다. 이후 `judge_matches.jsonl`에서는 generated unit별로 covered candidate 중 가장 좋은 primary match를 고른다. 우선순위는 `exact > semantic > partial > wrong`이고, 그다음 single-hop 여부, judge confidence, candidate score를 사용한다.

실제 예시로 `multi_turn_base_1`의 `u2` generated action은 다음과 같다.

```text
Use mv: Move the 'log.txt' file to the 'archive' directory. Inputs: {"source": "log.txt", "destination": "archive/log.txt"}
```

이 action은 같은 sample의 gold hop 6개와 각각 pairwise로 비교된다.

| candidate | gold call | q1 action | q2 input | q3 extra | q4 hallucinated | match | confidence | judge reason |
|---|---|---|---|---|---|---|---:|---|
| `h1` | `ls({"a": true})` | no | incompatible | no | no | wrong | 0.96 | generated action은 `ls`가 아니라 move step에 대응 |
| `h2` | `cd({"folder": "workspace"})` | no | incompatible | no | no | wrong | 0.94 | directory 이동이 아니라 `log.txt` 이동 |
| `h3` | `mv({"source": "log.txt", "destination": "archive"})` | exact | compatible | no | no | exact | 0.90 | `archive/log.txt` destination spelling은 다르지만 move intent와 input이 compatible |
| `h4` | `cd({"folder": "archive"})` | no | partially_compatible | no | no | wrong | 0.94 | `archive` token은 공유하지만 action은 `cd`가 아니라 `mv` |
| `h5` | `grep({"file_name": "log.txt", "pattern": "Error"})` | no | partially_compatible | no | no | wrong | 0.95 | `log.txt` token은 공유하지만 grep hop이 아님 |
| `h6` | `tail({"file_name": "log.txt", "lines": 20})` | no | partially_compatible | no | no | wrong | 0.95 | `log.txt` token은 공유하지만 tail hop이 아님 |

resolver는 이 6개 pairwise 결과 중 `h3`만 `candidate_action_covered=true`, `single_hop_match=true`, `match_strength=exact`로 보았기 때문에 `u2 -> h3`를 primary match로 선택한다. 이 예시에서 보듯 candidate score는 후보를 설명하는 보조 정보이고, 최종 회수 여부는 judge의 action/input 판정과 single-hop 판정으로 결정된다.

## 6. Confidence trace 해석

이번 실험에는 두 종류의 confidence가 있다. 서로 다른 값이므로 섞어서 해석하면 안 된다.

### 6.1 LLaDA token confidence

`token_confidence.jsonl`의 `confidence`는 LLaDA denoising 과정에서 mask token을 특정 token으로 commit할 때의 selected-token probability다. 구현상 `remasking=low_confidence`일 때 logits에 softmax를 적용하고, 선택된 token id의 probability를 저장한다.

각 token trace에는 다음 필드가 있다.

| 필드 | 의미 |
|---|---|
| `block` | generation block index |
| `commit_step` | 해당 token이 mask에서 실제 token으로 확정된 generation step |
| `step_in_block` | block 내부 step |
| `position` | generated output 안에서의 token position |
| `token_id`, `token_text` | 확정된 token |
| `confidence` | commit 시점의 selected-token probability |
| `char_start`, `char_end` | decoded response 안의 character span |

예를 들어 `multi_turn_base_1`의 첫 token trace는 다음 형태다.

```json
{"question_id": "multi_turn_base_1", "mode": "exact_name_a", "block": 0, "commit_step": 1, "position": 0, "token_text": "[A", "confidence": 0.992093026638031, "char_start": 0, "char_end": 2}
```

이번 run에는 token-level trace가 6,400개 존재한다. `think_units.jsonl`의 `response_spans`/`field_spans`와 `token_confidence.jsonl`의 `char_start`/`char_end`를 겹침 기준으로 join하면 다음 aggregate를 얻을 수 있다.

| span | token 수 | mean confidence | median | p10 | p90 |
|---|---:|---:|---:|---:|---:|
| all tokens | 6,400 | 0.907 | 0.965 | 0.692 | 0.999 |
| generated action span | 5,659 | 0.900 | 0.960 | 0.673 | 0.999 |
| label span | 516 | 0.969 | 0.984 | 0.932 | 1.000 |
| function/tool name span | 482 | 0.879 | 0.949 | 0.651 | 0.999 |
| intent span | 1,920 | 0.869 | 0.935 | 0.609 | 0.999 |
| known input span | 2,421 | 0.918 | 0.971 | 0.729 | 0.999 |

Unit별 action-span 평균 confidence를 judge match 결과와 붙이면 다음 경향이 있다.

| primary match strength | unit 수 | action-span mean | function-name mean | intent mean | known-input mean |
|---|---:|---:|---:|---:|---:|
| exact | 68 | 0.920 | 0.899 | 0.884 | 0.928 |
| semantic | 10 | 0.865 | 0.803 | 0.856 | 0.894 |
| partial | 38 | 0.890 | 0.795 | 0.874 | 0.900 |
| wrong | 56 | 0.874 | 0.792 | 0.820 | 0.903 |

따라서 token confidence 실험 결과는 raw trace 수준으로는 존재하고, span-level aggregate도 산출 가능하다. 다만 이 값은 모델이 token을 commit할 때의 확률이지 정답 여부가 아니다. Exact match unit의 action-span 평균이 wrong보다 높기는 하지만, 분포가 넓게 겹치며 known input confidence는 wrong에서도 0.903으로 높다. 즉 v1에서 token confidence는 error detector라기보다, function name/intent/action span별 generation certainty를 보는 보조 진단 신호로 해석하는 것이 안전하다.

### 6.2 Judge confidence

`judge_confidence`는 Codex judge가 pairwise 판정에 대해 낸 자기 확신도다. 이것은 LLaDA generation confidence가 아니다. 이번 run에서 primary matched rows의 judge confidence 평균은 0.906, median은 0.920이었다. 즉 judge는 비교적 높은 확신으로 exact/semantic/partial/wrong을 구분한 편이다.

## 7. 지표 정의

이 보고서 본문에서는 실험 해석에 직접 필요한 지표만 사용한다. recall 계열은 gold hop 293개가 denominator이고, generated-action 계열은 generated unit 172개가 denominator다.

| 지표 | denominator | 정의 | 보고서에서 보는 의미 |
|---|---:|---|---|
| `format_parse_rate` | generations | 모델 출력이 parser가 읽을 수 있는 `[A#]` action plan으로 구조화된 비율 | prompt/parser stack이 안정적인지 확인 |
| generated/gold ratio | gold hops | generated action 수를 gold hop 수로 나눈 값 | 낮은 recall이 action 수 부족에서 오는지 확인 |
| `strict_single_action_recall` | gold hops | primary match가 exact이고, 단일 generated action이 단일 gold hop에 대응한 비율 | 가장 보수적인 hop recovery 성능 |
| `partial_or_better_recall` | gold hops | exact/semantic/partial 중 하나로 단일 gold hop을 회수한 비율 | intent를 느슨하게 보았을 때의 회수 상한 |
| function-name validity | generated units | parser가 뽑은 `tool_name`이 해당 sample의 available schema에 실제 존재한 비율 | exact function-name anchor가 얼마나 지켜졌는지 확인 |
| `hallucinated_argument_rate` | generated units | prior result가 필요한 concrete value를 모델이 임의로 생성한 action 비율 | `Inputs:` grounding 실패와 state-dependent argument hallucination 확인 |

`strict_single_action_recall`은 exact function-name validity와 같은 뜻이 아니다. operationally는 resolved primary match가 exact behavior로 판정되고, 한 generated action이 한 gold hop에 대응하는 경우를 뜻한다. judge prompt는 exact를 보수적으로 쓰도록 했고, intent와 input compatibility가 함께 맞아야 exact로 남을 수 있다.

예를 들어 `multi_turn_base_1`의 generated `grep` action은 다음 gold hop과 exact single-hop match로 잡혔다.

```text
Generated:
[A3] Use grep: Search for the keyword 'Error' in 'log.txt'. Inputs: {"file_name": "log.txt", "pattern": "Error"}

Gold:
h5 grep({"file_name": "log.txt", "pattern": "Error"})
```

이 경우 strict recall과 partial-or-better recall에 모두 기여한다. 반대로 function name이 schema에 존재하더라도 input grounding이 틀리거나 한 `[A]` line이 여러 hop을 섞으면 strict single-action recall에는 들어가지 않는다.

예를 들어 `multi_turn_base_107`에서 generated action이 `get_order_details`에 `{"order_id": 1}`을 넣었다면, order id는 prior order placement 결과에서 와야 하므로 hallucinated argument로 잡힌다. 이 action은 operation type은 가까워도 incompatible concrete argument 때문에 covered match로 남기 어렵다.

function-name validity는 judge recall과 별도로 계산한 지표다. parser가 뽑은 `tool_name`이 해당 sample의 available schema function name에 실제 존재하는지 본다.

이번 run:

| 항목 | 값 |
|---|---:|
| generated units | 172 |
| schema-valid function names | 149 |
| invalid function names | 23 |
| function-name validity rate | 86.6% |

자주 나온 invalid name은 다음과 같다.

| invalid generated name | count | expected nearby tool examples |
|---|---:|---|
| `add_stock_to_watchlist` | 4 | `add_to_watchlist` |
| `tweet` | 2 | `post_tweet` |
| `checkTirePressure` | 2 | `check_tire_pressure` |
| `fuel_level` | 2 | `displayCarStatus({"_arg0": "fuel"})` |
| `start_engine` | 2 | `startEngine` |

이 결과는 v1의 중요한 실패다. prompt는 exact name을 요구했지만, LLaDA는 natural API naming prior를 따라 camelCase/snake_case 변형이나 더 그럴듯한 tool name을 만들어냈다.

## 8. Generation 결과

핵심 메시지: v1은 출력 형식 생성에는 성공했지만, gold trajectory를 충분히 길게 펼치지 못했다. 생성된 action은 172개이고, 회수해야 할 gold hop은 293개다. 즉 모델이 만든 action 수가 gold hop의 58.7% 수준이라, judge가 아무리 관대하더라도 full trajectory recall에는 구조적 상한이 생긴다.

| 항목 | 값 |
|---|---:|
| total generations | 50 |
| parsed generations | 50 |
| total generated units | 172 |
| gold hops | 293 |
| generated actions / gold actions ratio | 58.7% |
| mean generated units per sample | 3.44 |
| mean gold hops per sample | 5.86 |
| average generated/gold ratio per sample | 0.664 |
| under-generated samples | 44 / 50 |

이 결과에서 가장 중요한 것은 parse success가 action recovery success와 다르다는 점이다. 형식은 안정적이지만, 모델이 필요한 hop을 충분히 생성하지 않으면 gold hop recall은 올라갈 수 없다.

가장 크게 under-generate된 sample은 다음과 같다.

| sample | gold hops | generated actions | diff |
|---|---:|---:|---:|
| `multi_turn_base_39` | 10 | 4 | -6 |
| `multi_turn_base_97` | 10 | 4 | -6 |
| `multi_turn_base_59` | 10 | 5 | -5 |
| `multi_turn_base_70` | 9 | 4 | -5 |
| `multi_turn_base_188` | 8 | 3 | -5 |

따라서 이 run의 첫 번째 병목은 “모델이 잘못된 action을 많이 만든다”보다 “필요한 action을 충분히 만들지 않는다”에 가깝다. 이 점은 뒤의 실제 데이터 사례에서 `multi_turn_base_39`가 잘 보여준다.

## 9. Judge 최종 지표

핵심 메시지: judge 기준으로 보아도 hop-level action recovery는 제한적이다. strict하게 보면 gold hop의 21.8%만 회수했고, partial match까지 허용해도 33.4%에 머물렀다. 즉 v1은 “형식을 맞춘 action plan”은 만들지만, BFCL full trajectory의 실행 단계를 빠짐없이 복구하는 데에는 아직 부족하다.

| 지표 | 값 | 해석 |
|---|---:|---|
| strict single-action recall | 21.8% | exact behavior와 input compatibility까지 맞는 단일-hop recovery는 낮다 |
| partial-or-better recall | 33.4% | intent를 느슨하게 인정해도 gold hop의 약 1/3만 회수된다 |
| function-name validity | 86.6% | 대부분 schema 안의 이름을 쓰지만, exact-name anchor가 완전히 안정적이지는 않다 |
| hallucinated argument rate | 19.8% | prior result가 필요한 값을 임의로 채우는 문제가 여전히 크다 |

이 네 지표를 함께 보면 실패 양상이 세 갈래로 정리된다. 첫째, 필요한 hop을 충분히 생성하지 못한다. 둘째, 생성한 action 중 일부는 schema 밖 function name을 사용한다. 셋째, action intent가 맞더라도 order id, booking id, lookup result처럼 이전 tool 결과가 필요한 값을 임의로 채우는 경우가 있다.

특히 `Inputs:` 필드는 이런 argument grounding 문제를 보려고 넣은 장치다. 하지만 실제 출력에서는 “이 값은 이전 결과에서 온다”는 unresolved 표현이 충분히 활용되지 않았고, 일부 action은 concrete value를 추측했다. 따라서 v1의 병목은 단순한 format 문제가 아니라, trajectory length, exact schema naming, state-dependent input grounding이 함께 얽힌 문제로 해석해야 한다.

## 10. Sample별 성능

Partial-or-better single-action recall 기준 상위 sample이다. 여기서는 본문 핵심 지표인 strict count와 partial+ count만 남긴다.

| sample | gold | generated | strict | partial+ |
|---|---:|---:|---:|---:|
| `multi_turn_base_139` | 2 | 4 | 2 | 2 |
| `multi_turn_base_50` | 2 | 3 | 2 | 2 |
| `multi_turn_base_137` | 4 | 4 | 3 | 3 |
| `multi_turn_base_117` | 6 | 4 | 3 | 4 |
| `multi_turn_base_91` | 3 | 4 | 2 | 2 |
| `multi_turn_base_6` | 8 | 5 | 4 | 5 |

하위 sample:

| sample | gold | generated | strict | partial+ |
|---|---:|---:|---:|---:|
| `multi_turn_base_57` | 4 | 3 | 0 | 0 |
| `multi_turn_base_24` | 6 | 3 | 0 | 0 |
| `multi_turn_base_26` | 5 | 4 | 0 | 0 |
| `multi_turn_base_56` | 8 | 4 | 1 | 1 |
| `multi_turn_base_62` | 8 | 4 | 1 | 1 |

좋은 sample은 gold hop 수가 작거나, action name과 user request 사이의 lexical alignment가 강한 경우가 많았다. 나쁜 sample은 intermediate lookup, state-dependent argument, exact tool naming, multi-step file/state manipulation이 필요할 때 많았다.

## 11. Tool별 관찰

Gold tool별 partial-or-better recall이 높은 예:

| tool | gold count | partial+ covered | partial+ recall |
|---|---:|---:|---:|
| `get_watchlist` | 5 | 5 | 1.000 |
| `add_to_watchlist` | 4 | 4 | 1.000 |
| `startEngine` | 11 | 10 | 0.909 |
| `get_flight_cost` | 12 | 9 | 0.750 |
| `place_order` | 4 | 3 | 0.750 |

Gold tool별 recall이 낮은 예:

| tool | gold count | partial+ covered | partial+ recall |
|---|---:|---:|---:|
| `get_zipcode_based_on_city` | 14 | 0 | 0.000 |
| `cd` | 14 | 0 | 0.000 |
| `pressBrakePedal` | 11 | 0 | 0.000 |
| `post_tweet` | 8 | 0 | 0.000 |
| `retrieve_invoice` | 6 | 0 | 0.000 |
| `view_messages_sent` | 5 | 0 | 0.000 |
| `authenticate_twitter` | 5 | 0 | 0.000 |
| `get_order_details` | 4 | 0 | 0.000 |

해석:

- 모델은 user-visible high-level actions에는 비교적 잘 반응한다.
- hidden prerequisite나 execution-state step은 자주 생략한다.
- 예: `cd`, `pressBrakePedal`, `get_zipcode_based_on_city`, `authenticate_twitter`, `view_messages_sent`.
- 이 실험은 full trajectory recovery를 보므로, 이런 prerequisite hop 생략이 recall을 크게 낮춘다.

## 12. 실제 데이터 사례

### 12.1 부분 성공: `multi_turn_base_1`

Generated:

```text
[A1] Use ls: List the contents of the current directory. Inputs: {}
[A2] Use mv: Move the 'log.txt' file to the 'archive' directory. Inputs: {"source": "log.txt", "destination": "archive/log.txt"}
[A3] Use grep: Search for the keyword 'Error' in 'log.txt'. Inputs: {"file_name": "log.txt", "pattern": "Error"}
[A4] Use tail: Display the last 20 lines of 'log.txt'. Inputs: {"file_name": "log.txt", "lines": 20}
```

Gold 중 matched hops:

```text
h3 mv({"source": "log.txt", "destination": "archive"})
h5 grep({"file_name": "log.txt", "pattern": "Error"})
h6 tail({"file_name": "log.txt", "lines": 20})
```

Judge 결과:

| generated unit | primary hop | match strength | single-hop | judge confidence | 해석 |
|---|---|---:|---:|---:|---|
| `u2` `mv` | `h3` | exact | true | 0.90 | destination spelling은 다르지만 archive 이동 intent와 input이 compatible |
| `u3` `grep` | `h5` | exact | true | 0.97 | file/pattern이 gold와 일치 |
| `u4` `tail` | `h6` | exact | true | 0.97 | file/line count가 gold와 일치 |
| `u1` `ls` | none | wrong | false | null | gold `ls({"a": true})`의 hidden-file option을 충분히 반영하지 못함 |

이 sample은 visible file actions를 잘 맞춘다. 하지만 gold에는 `cd({"folder": "workspace"})`, `cd({"folder": "archive"})`도 있다. 모델은 directory context 이동 hop을 생략했다. 따라서 `mv`, `grep`, `tail`은 strict recall에 기여하지만, `cd` hop과 hidden `ls` hop은 빠져 recall이 제한된다.

### 12.2 Under-generation: `multi_turn_base_39`

Gold는 10 hops다.

```text
mkdir -> cd -> touch/echo styles.css -> touch/echo index.html -> touch/echo script.js -> ls -> cat styles.css
```

Generated는 4 actions다.

```text
[A1] Use mkdir: Create WebDevProjects.
[A2] Use touch: Create styles.css.
[A3] Use touch: Create index.html.
[A4] Use cat: Display script.js.
```

이 사례의 문제는 generated action 수 자체가 부족하다는 점이다.

| 누락/오류 | 영향 |
|---|---|
| `cd(WebDevProjects)` 누락 | 이후 file operation context가 gold와 달라짐 |
| `echo` content-writing hops 누락 | CSS/HTML/JS 내용 생성이 회수되지 않음 |
| `script.js` 생성 누락 | later file display와 연결되지 않음 |
| turn 3의 `ls` 누락 | user-visible inspection hop 누락 |
| final target 오류 | gold는 `styles.css`를 cat하지만 generated는 `script.js`를 display |

이 sample은 v1의 전형적인 병목을 보여준다. 모델은 high-level goal 일부를 plan으로 만들지만, BFCL gold trajectory의 실행 가능한 세부 hop으로 충분히 분해하지 못했다.

### 12.3 Wrong arithmetic / invented sequence: `multi_turn_base_57`

Gold:

```text
get_zipcode_based_on_city("Crescent Hollow")
get_zipcode_based_on_city("Autumnville")
estimate_distance(cityA, cityB)
logarithm(value=distance, base=10, precision=5)
```

Generated:

```text
Use subtract: Calculate the distance between Crescent Hollow and Autumnville. Inputs: {"a": 100, "b": 50}
Use logarithm: Calculate the logarithm of the distance. Inputs: {"value": 50, ...}
Use round_number: Round the logarithm result.
```

문제:

- schema/gold에 맞는 city zipcode lookup을 사용하지 않았다.
- distance를 `100 - 50` 같은 임의 숫자 계산으로 바꿨다.
- 후속 `logarithm` 입력도 hallucinated value에 의존했다.
- gold에는 `round_number` hop이 없는데 generated plan은 추가했다.

Judge recall은 0이었다. 이 사례는 action recovery 실패와 hallucinated argument가 함께 발생한 예다.

### 12.4 Function-name drift: `multi_turn_base_55`

Gold에는 다음 tool들이 포함된다.

```text
displayCarStatus({"_arg0": "fuel"})
fillFuelTank({"_arg0": 15.0})
pressBrakePedal({"pedalPosition": 1.0})
startEngine({"ignitionMode": "START"})
check_tire_pressure({})
create_ticket(...)
get_ticket(...)
resolve_ticket(...)
```

Generated:

```text
Use checkFuelLevel
Use startEngine
Use checkTirePressure
Use createTicket
Use fetchTicket
Use updateTicket
```

문제는 의미가 가까워 보여도 schema name이 drift한다는 점이다.

| generated name | schema 관점 문제 |
|---|---|
| `checkFuelLevel` | 실제 fuel status는 `displayCarStatus({"_arg0": "fuel"})`로 표현됨 |
| `checkTirePressure` | schema에는 `check_tire_pressure` |
| `createTicket` | schema에는 `create_ticket` |
| `fetchTicket` | schema에는 `get_ticket` |
| `updateTicket` | ticket resolve는 `resolve_ticket` |

judge는 natural-language intent가 가까우면 semantic/partial로 일부 회수할 수 있다. 하지만 executable tool-name validity 관점에서는 실패다. v1 prompt가 exact function name을 요구했기 때문에, 이런 drift는 별도 지표로 반드시 봐야 한다.

### 12.5 Hallucinated prior-result input: `multi_turn_base_107`

이 sample에서는 order workflow가 포함된다. generated action 중 하나는 다음처럼 prior result가 필요한 order id를 concrete value로 썼다.

```text
[A3] Use get_order_details: Retrieve the full details of the Zeta Corp order, including the order ID. Inputs: {"order_id": 1}
```

이 입력은 user request에 직접 주어진 값이 아니다. order id는 `place_order` 결과에서 나와야 한다. prompt는 이런 경우 concrete value를 추측하지 말고 result-dependent input으로 쓰라고 했지만, 모델은 `1`을 invent했다. judge는 이런 row를 hallucinated argument로 본다.

이 사례는 `Inputs:` 필드를 넣은 이유를 잘 보여준다. action intent 자체는 `get_order_details`에 가까울 수 있지만, input grounding이 틀리면 executable trajectory recovery에는 실패한다.

## 13. v0 결과와의 비교

주의: v0와 v1은 evaluator가 다르다.

- v0: rule-based `action_hint` matcher
- v1: all-hop candidate + Codex LLM-as-judge

따라서 숫자를 직접 같은 metric으로 등호 비교하면 안 된다. 아래 비교는 run의 성격을 잡기 위한 참고용이다. 개선/악화 판정에는 같은 evaluator로 재평가한 결과가 필요하다.

### 13.1 v0 TA run

`think_parallel_v0/outputs/llada_think_parallel_20260514_100536`

| mode | units | match rate | tool selection recall | hallucinated action rate | format parse rate |
|---|---:|---:|---:|---:|---:|
| `goal_tools_ta` | 151 | 0.570 | 0.297 | 0.430 | 0.940 |
| `goal_init_tools_ta` | 157 | 0.561 | 0.307 | 0.439 | 1.000 |

### 13.2 v0 A-only run

`think_parallel_v0/outputs/llada_think_parallel_23628`

| mode | units | match rate | tool selection recall | hallucinated action rate | format parse rate |
|---|---:|---:|---:|---:|---:|
| `goal_tools_a` | 290 | 0.286 | 0.294 | 0.714 | 1.000 |
| `goal_init_tools_a` | 299 | 0.184 | 0.188 | 0.816 | 1.000 |

### 13.3 v1 current run

| mode | units | strict recall | partial+ recall | hallucinated arg rate | format parse rate |
|---|---:|---:|---:|---:|---:|
| `exact_name_a` | 172 | 0.218 | 0.334 | 0.198 | 1.000 |

Interpretation:

1. v1의 parse 안정성은 좋다. v0 `goal_tools_ta`의 94% parse rate와 달리 이번 run은 100%였고, v0 A-only도 100%였다.
2. v1은 v0 A-only보다 action 수가 적다. v0 A-only는 290개 이상을 생성했고, v1은 172개를 생성했다. 이 차이는 prompt와 평가 정의가 달라 직접적인 품질 비교로 해석하면 안 된다.
3. v1의 partial+ recall 33.4%와 v0 TA의 rule-based tool_selection_recall 29.7-30.7%는 이름부터 evaluator까지 다르다. 같은 ballpark라는 참고 이상의 결론은 내리기 어렵다.
4. v1의 strict recall 21.8%는 낮다. 여기서 strict는 judge 기준 exact behavior, compatible input, single-hop match이며 exact function-name validity와는 별도다.
5. v1의 hallucinated argument rate 19.8%와 v0 hallucinated action rate는 정의가 다르다. 따라서 v1이 hallucination을 줄였다고 단정하지 말고, v1이 더 적은 action을 생성한 run이라는 사실과 함께 해석해야 한다.

## 14. 현재 실험에서 확인한 것

이번 v1 run으로 확인한 것은 다음이다.

1. LLaDA는 BFCL function schema를 보고 labeled action plan format을 안정적으로 따를 수 있다.
2. `exact_name_a` prompt/parser stack은 50/50 generation parse에 성공했다.
3. 그러나 exact function name 준수는 완벽하지 않다. 13.4% action에서 schema 밖 function name이 나왔다.
4. Full trajectory hop recovery는 낮다. partial-or-better single-hop recall이 33.4%다.
5. 주요 실패는 under-generation, prerequisite hop 생략, state-dependent argument hallucination, function name drift다.
6. 모델은 user-visible goal action에는 강하지만, execution substrate hop에는 약하다. 예를 들어 `cd`, auth/login, lookup, status read, brake/fuel prerequisite, prior-result ID resolution이 자주 빠진다.

## 15. Bottom line

`think_parallel_v1`은 action format 안정화와 all-hop pairwise judge 실행이라는 목적에는 성공했다.

하지만 실험 질문인 “LLaDA가 BFCL full trajectory action plan을 hop 단위로 복구할 수 있는가?”에 대한 답은 아직 제한적이다. strict single-hop recall은 21.8%, partial-or-better도 33.4%에 그쳤다.

따라서 이 run은 dependency/parallelism signal 분석의 본 실험이라기보다, 그 전에 필요한 **action recovery diagnostic baseline**으로 보는 것이 가장 적절하다. 현재 가장 큰 병목은 prompt 형식 준수가 아니라, 필요한 tool-use hop을 빠짐없이 생성하고 exact schema name 및 state-dependent arguments를 안정적으로 grounding하는 능력이다.
