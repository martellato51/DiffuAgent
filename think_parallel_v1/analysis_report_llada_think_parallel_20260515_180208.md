# think_parallel_v1 analysis report

작성 대상 run:
`/home/ilju/research/DiffuAgent/think_parallel_v1/outputs/llada_think_parallel_20260515_180208`

Judge 완료 산출물:

- `judge_candidates.jsonl`
- `judge_pairwise.jsonl`
- `judge_matches.jsonl`
- `judge_metrics.json`

## 1. 결론 요약

이번 `think_parallel_v1` run은 LLaDA가 BFCL multi-turn task에서 strict executable tool-call syntax를 맞추지 못하더라도, **gold trajectory의 hop 단위 action intent를 BFCL function name 중심 prompt로 회수할 수 있는지**를 보는 실험이다. 단, 아래 judge의 `strict` recall은 exact function-name validity 자체가 아니라 judge 기준의 exact behavior, compatible input, single-hop match를 뜻한다.

핵심 결과는 다음과 같다.

| 항목 | 값 |
|---|---:|
| samples | 50 |
| gold hops | 293 |
| generated action units | 172 |
| format parse rate | 100.0% |
| candidate gold coverage | 100.0% |
| strict single-action recall | 21.8% |
| semantic single-action recall | 24.6% |
| partial-or-better single-action recall | 33.4% |
| recall including compound actions | 41.3% |
| unmatched generated action rate | 32.6% |
| compound action rate | 9.9% |
| hallucinated argument rate | 19.8% |
| duplicate action rate | 1.2% |

해석하면, v1 prompt/parser stack은 **형식 안정화에는 성공**했다. `candidate_gold_coverage=1.0`은 all-hop candidate 구조 때문에 거의 by construction이며, 이번 결과의 낮은 recall이 candidate retrieval/filtering 실패에서 온 것은 아니라는 뜻이다. 병목은 주로 generation 자체다. LLaDA가 평균적으로 gold hop 5.86개짜리 task에 action 3.44개만 생성했고, 50개 sample 중 44개에서 gold hop 수보다 적은 action을 냈다.

따라서 현재 v1 결과는 “LLaDA가 일부 high-level tool-use intent는 회수하지만, full trajectory를 hop 단위로 exhaustive하게 펼치는 능력은 아직 부족하다”로 보는 것이 맞다.

## 2. v0와 v1의 실험 차이

### v0가 보던 것

`think_parallel_v0`는 BFCL multi-turn sample의 모든 user turn을 concat한 **offline full-trajectory planning** setting이다. future turn을 포함한 전체 request를 처음부터 보여주고, LLaDA가 tool-use plan을 만들 수 있는지 본다.

대표 mode:

| v0 mode | 출력 | 입력 특징 | 목적 |
|---|---|---|---|
| `goal_tools_ta` | `[T]` + `[A]` | user goal + function schema | think/action plan 생성 |
| `goal_init_tools_ta` | `[T]` + `[A]` | user goal + initial_config + schema | initial state 포함 효과 확인 |
| `goal_tools_a` | `[A]` only | user goal + schema | action-only baseline |
| `goal_init_tools_a` | `[A]` only | user goal + initial_config + schema | initial state 포함 action baseline |

v0의 중요한 성격:

- `[T]` span의 confidence와 gold dependency label 간 상관까지 보려는 흔적이 있다.
- matcher는 rule-based `action_hint` matching이다.
- `initial_config` 포함 여부가 독립변수였다.
- full multi-turn goal을 한 번에 주므로 online BFCL 실행은 아니다.

### v1이 바꾼 것

`think_parallel_v1`은 질문을 더 좁혔다.

> LLaDA가 exact BFCL function name을 anchor로 하여 hop 단위 action plan을 안정적으로 생성할 수 있는가?

v1에서 유지한 것:

- BFCL v3 JSON function schema injection
- offline full-trajectory planning
- gold graph는 generation에 넣지 않고 post-hoc 평가에만 사용

v1 범위에서 제외하거나 후속 실험으로 미룬 것:

- `[T]` thought lines
- `initial_config` prompt option
- dependency/precomputability prediction
- turn-prefix online planning
- Tool-ID/masked schema prompt

v1의 generation mode는 `exact_name_a` 하나다.

```text
[A1] Use <exact_function_name>: <intended action>. Inputs: <entities, arguments, or result-dependent inputs>.
```

이 변화의 의도는 dependency 분석 이전에 action recovery 자체를 안정화하는 것이다.

## 3. Judge 설계와 이번 run의 중요한 주의점

현재 v1 judge는 generated `[A]` 한 줄과 candidate gold hop 하나를 pairwise로 비교한다. Codex judge는 다음을 판정한다.

- action relation: exact / semantic / partial / no / unclear
- input relation: compatible / partially compatible / incompatible / unresolved_ok / not_applicable
- compound action 여부
- hallucinated argument 여부
- single hop match 여부

이번 코드에서는 `candidate_generator.py`가 `top_k=5`로 실제 filtering을 하지 않고, **각 generated unit에 대해 해당 sample의 모든 gold hop을 candidate로 유지**한다. 그래서 총 pair 수는 다음처럼 결정된다.

```text
sum_over_units(number of gold hops in that unit's sample) = 1066 pairwise judgments
```

결과적으로 `candidate_gold_coverage=1.0`이 나왔다. 이 값은 성능 신호라기보다 all-hop candidate 설정의 산물이다. 따라서 낮은 recall은 candidate retrieval/filtering 문제가 아니라, 생성된 action의 내용과 granularity 문제로 해석할 수 있다.

## 4. Generation 결과

Generation summary:

| 항목 | 값 |
|---|---:|
| total generations | 50 |
| parsed generations | 50 |
| parse mode `exact_name_a` | 49 generations |
| parse mode `a_only` | 1 generation |
| total generated units | 172 |
| mean units per generation | 3.44 |
| gold hops | 293 |
| mean gold hops per sample | 5.86 |

Generated action 수와 gold hop 수 비교:

| 항목 | 값 |
|---|---:|
| average generated/gold ratio per sample | 0.664 |
| average generated minus gold | -2.42 |
| under-generated samples | 44 / 50 |
| equal count samples | 2 / 50 |
| over-generated samples | 4 / 50 |

가장 많이 under-generate된 sample:

| sample | gold hops | generated actions | diff |
|---|---:|---:|---:|
| `multi_turn_base_39` | 10 | 4 | -6 |
| `multi_turn_base_97` | 10 | 4 | -6 |
| `multi_turn_base_59` | 10 | 5 | -5 |
| `multi_turn_base_70` | 9 | 4 | -5 |
| `multi_turn_base_188` | 8 | 3 | -5 |

이 숫자가 가장 큰 병목이다. 아무리 judge가 관대해도 generated action이 172개뿐이면, 293개 gold hop 전체를 strict single-hop으로 덮는 것은 어렵다.

## 5. Judge 최종 지표

`judge_metrics.json`의 최종 결과:

| metric | value |
|---|---:|
| format_parse_rate | 1.000 |
| candidate_gold_coverage | 1.000 |
| strict_single_action_recall | 0.218 |
| semantic_single_action_recall | 0.246 |
| partial_or_better_recall | 0.334 |
| recall_including_compound | 0.413 |
| compound_action_rate | 0.099 |
| hallucinated_argument_rate | 0.198 |
| unmatched_action_rate | 0.326 |
| duplicate_action_rate | 0.012 |

Unit-level resolved match breakdown:

| category | count | denominator | rate |
|---|---:|---:|---:|
| covered generated units | 116 | 172 | 67.4% |
| single-hop matched units | 99 | 172 | 57.6% |
| exact primary matches | 68 | 172 | 39.5% |
| semantic primary matches | 10 | 172 | 5.8% |
| partial primary matches | 38 | 172 | 22.1% |
| wrong / unmatched primary | 56 | 172 | 32.6% |
| compound units | 17 | 172 | 9.9% |
| hallucinated-argument units | 34 | 172 | 19.8% |
| duplicate primary matches | 2 | 172 | 1.2% |

Pairwise judge diagnostics:

| field | main counts |
|---|---|
| match strength | wrong 931, exact 68, partial 52, semantic 15 |
| q1 action relation | no 885, exact 113, partial 45, semantic 23 |
| q2 input relation | incompatible 674, partially compatible 190, compatible 103, not_applicable 98, unresolved_ok 1 |
| q3 extra distinct action | no 960, yes 106 |
| q4 hallucinated argument | no 910, yes 156 |

Primary matched rows의 judge confidence는 평균 0.906, median 0.920이었다. 즉 judge는 애매한 낮은 confidence로 대충 맞춘 것이 아니라, 비교적 확신 있게 wrong/partial/exact를 구분한 편이다.

## 6. Sample별 성능

Partial-or-better single-action recall 기준 상위 sample이다. 여기서 `semantic+`는 exact 또는 semantic single-hop match의 누적 count이고, `partial+`는 exact, semantic, partial single-hop match의 누적 count다.

| sample | gold | generated | strict | semantic+ | partial+ | incl compound |
|---|---:|---:|---:|---:|---:|---:|
| `multi_turn_base_139` | 2 | 4 | 2 | 2 | 2 | 2 |
| `multi_turn_base_50` | 2 | 3 | 2 | 2 | 2 | 2 |
| `multi_turn_base_137` | 4 | 4 | 3 | 3 | 3 | 3 |
| `multi_turn_base_117` | 6 | 4 | 3 | 3 | 4 | 4 |
| `multi_turn_base_91` | 3 | 4 | 2 | 2 | 2 | 2 |
| `multi_turn_base_6` | 8 | 5 | 4 | 4 | 5 | 5 |

하위 sample:

| sample | gold | generated | strict | semantic+ | partial+ | incl compound |
|---|---:|---:|---:|---:|---:|---:|
| `multi_turn_base_57` | 4 | 3 | 0 | 0 | 0 | 0 |
| `multi_turn_base_24` | 6 | 3 | 0 | 0 | 0 | 2 |
| `multi_turn_base_26` | 5 | 4 | 0 | 0 | 0 | 2 |
| `multi_turn_base_56` | 8 | 4 | 1 | 1 | 1 | 1 |
| `multi_turn_base_62` | 8 | 4 | 1 | 1 | 1 | 1 |

좋은 sample은 gold hop 수가 작거나, action name과 user request 사이의 lexical alignment가 강한 경우가 많다. 나쁜 sample은 intermediate lookup, state-dependent argument, exact tool naming, multi-step file/state manipulation이 필요할 때 많았다.

## 7. Tool별 관찰

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
- 그러나 hidden prerequisite나 execution-state step은 자주 생략한다.
- 예: `cd`, `pressBrakePedal`, `get_zipcode_based_on_city`, `authenticate_twitter`, `view_messages_sent`.
- 이 실험은 full trajectory recovery를 보므로, 이런 prerequisite hop 생략이 recall을 크게 낮춘다.

## 8. Exact function name 준수

`exact_name_a` prompt는 exact BFCL function name 사용을 요구했지만, 실제 generated tool name 중 일부는 schema에 없는 이름이었다.

| 항목 | 값 |
|---|---:|
| generated units | 172 |
| schema-valid function names | 149 |
| invalid function names | 23 |
| function-name validity rate | 86.6% |

자주 나온 invalid name:

| invalid generated name | count | expected nearby tool examples |
|---|---:|---|
| `add_stock_to_watchlist` | 4 | `add_to_watchlist` |
| `tweet` | 2 | `post_tweet` |
| `checkTirePressure` | 2 | `check_tire_pressure` |
| `fuel_level` | 2 | `displayCarStatus({"_arg0": "fuel"})` |
| `start_engine` | 2 | `startEngine` |

이것은 v1의 중요한 실패다. prompt는 exact name을 요구하지만, LLaDA는 natural API naming prior를 따라 camelCase/snake_case 변형이나 더 그럴듯한 tool name을 만들어낸다.

## 9. 대표 사례

### 부분 성공 사례: `multi_turn_base_1`

Generated:

```text
[A1] Use ls: List the contents of the current directory.
[A2] Use mv: Move the 'log.txt' file to the 'archive' directory.
[A3] Use grep: Search for the keyword 'Error' in 'log.txt'.
[A4] Use tail: Display the last 20 lines of 'log.txt'.
```

Gold:

```text
h3 mv({"source": "log.txt", "destination": "archive"})
h5 grep({"file_name": "log.txt", "pattern": "Error"})
h6 tail({"file_name": "log.txt", "lines": 20})
```

Judge는 위 세 개를 exact로 봤다. 다만 같은 sample에서 `cd({"folder": "workspace"})`, `cd({"folder": "archive"})`는 빠졌다. 즉 visible user action은 맞추지만 execution context 이동 hop은 생략했다.

또한 `[A1] Use ls`는 현재 디렉터리 listing intent는 맞지만 gold가 요구하는 hidden-file option `ls({"a": true})`와 충분히 compatible하지 않아 최종 covered match로 잡히지 않았다. 그래서 이 사례는 “visible action 일부를 잘 맞춘 부분 성공”으로 보는 것이 정확하다.

### Under-generation / file workflow 실패: `multi_turn_base_39`

Gold는 10 hops:

```text
mkdir -> cd -> touch/echo styles.css -> touch/echo index.html -> touch/echo script.js -> ls -> cat styles.css
```

Generated는 4 actions:

```text
[A1] Use mkdir: Create WebDevProjects.
[A2] Use touch: Create styles.css.
[A3] Use touch: Create index.html.
[A4] Use cat: Display script.js.
```

문제:

- `cd(WebDevProjects)` 누락
- `echo` content-writing hops 누락
- `script.js` 파일 생성 누락
- turn 3의 `ls` 누락
- turn 4의 target이 gold `styles.css`인데 generated는 `script.js`

이 sample은 v1의 가장 전형적인 병목을 보여준다. 모델은 high-level goal 일부를 plan으로 만들지만, BFCL gold trajectory의 실행 가능한 세부 hop으로 충분히 분해하지 못했다.

### Wrong arithmetic / invented tool sequence: `multi_turn_base_57`

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

- schema/gold에 맞는 city zipcode lookup을 사용하지 않음
- distance를 임의 숫자 계산으로 hallucination
- 후속 logarithm 입력도 hallucinated value에 의존

Judge recall은 0이었다.

### Function name drift: `multi_turn_base_55`

Gold:

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

문제:

- 의미는 가까운 action들이 있지만 exact schema name이 많이 drift한다.
- fuel amount, brake prerequisite, exact ticket IDs 같은 state-dependent argument가 빠진다.
- 이런 경우 judge가 semantic/partial, 때로는 exact behavior match로 일부 회수할 수는 있다. 하지만 실제 executable tool-name validity에는 치명적이며, judge recall과 별도 지표로 봐야 한다.

## 10. v0 결과와의 비교

주의: v0와 v1은 evaluator가 다르다.

- v0: rule-based `action_hint` matcher
- v1: all-hop candidate + Codex LLM-as-judge

따라서 숫자를 직접 같은 metric으로 등호 비교하면 안 된다. 아래 비교는 run의 성격을 잡기 위한 참고용이며, 개선/악화 판정에는 v0 outputs를 v1 judge로 재평가한 공통 evaluator가 필요하다.

### v0 TA run

`think_parallel_v0/outputs/llada_think_parallel_20260514_100536`

| mode | units | match rate | tool selection recall | hallucinated action rate | format parse rate |
|---|---:|---:|---:|---:|---:|
| `goal_tools_ta` | 151 | 0.570 | 0.297 | 0.430 | 0.940 |
| `goal_init_tools_ta` | 157 | 0.561 | 0.307 | 0.439 | 1.000 |

### v0 A-only run

`think_parallel_v0/outputs/llada_think_parallel_23628`

| mode | units | match rate | tool selection recall | hallucinated action rate | format parse rate |
|---|---:|---:|---:|---:|---:|
| `goal_tools_a` | 290 | 0.286 | 0.294 | 0.714 | 1.000 |
| `goal_init_tools_a` | 299 | 0.184 | 0.188 | 0.816 | 1.000 |

### v1 current run

| mode | units | strict recall | semantic recall | partial+ recall | incl compound recall | hallucinated arg rate | format parse rate |
|---|---:|---:|---:|---:|---:|---:|---:|
| `exact_name_a` | 172 | 0.218 | 0.246 | 0.334 | 0.413 | 0.198 | 1.000 |

Interpretation:

1. v1의 parse 안정성은 좋다. v0 `goal_tools_ta`의 94% parse rate와 달리 이번 run은 100%였고, v0 A-only도 100%였다.
2. v1은 v0 A-only보다 action 수가 적다. v0 A-only는 290개 이상을 생성했고, v1은 172개를 생성했다. 이 차이는 prompt와 평가 정의가 달라 직접적인 품질 비교로 해석하면 안 된다.
3. v1의 partial+ recall 33.4%와 v0 TA의 rule-based tool_selection_recall 29.7-30.7%는 이름부터 evaluator까지 다르다. 같은 ballpark라는 참고 이상의 결론은 내리기 어렵다.
4. v1의 strict recall 21.8%는 낮다. 여기서 strict는 judge 기준 exact behavior, compatible input, single-hop match이며 exact function-name validity와는 별도다.
5. v1의 hallucinated argument rate 19.8%와 v0 hallucinated action rate는 정의가 다르다. 따라서 v1이 hallucination을 줄였다고 단정하지 말고, v1이 더 적은 action을 생성한 run이라는 사실과 함께 별도 재평가가 필요하다.

## 11. 무엇을 알게 되었나

이번 v1 실험으로 확인한 것:

1. LLaDA는 BFCL function schema를 보고 labeled action plan format을 안정적으로 따를 수 있다.
2. 그러나 exact function name 준수는 완벽하지 않다. 13.4% action에서 schema 밖 function name이 나왔다.
3. Full trajectory hop recovery는 아직 낮다. partial-or-better single-hop recall이 33.4%다.
4. Candidate retrieval/filtering bottleneck은 이번 run에서는 제거됐다. candidate coverage가 100%인 것은 all-hop candidate 구조의 결과다.
5. 주요 실패는 under-generation, prerequisite hop 생략, state-dependent argument hallucination, function name drift다.
6. 모델은 user-visible goal action에는 강하지만, execution substrate hop에는 약하다. 예를 들어 `cd`, auth/login, lookup, status read, brake/fuel prerequisite, prior-result ID resolution이 자주 빠진다.

## 12. 다음 실험 제안

다음 단계는 v1의 현재 형태를 바로 dependency/parallelism 분석으로 넘기기보다, action recovery recall을 먼저 올리는 것이 좋다.

우선순위:

1. **Turn-level planning으로 전환**
   - full future-turn concat은 long context와 future leakage를 동시에 만든다.
   - `turn_level_llmcompiler_dlm_plan.md`의 방향처럼 current turn + previous observation context로 나누면 missed prerequisite와 reference resolution을 더 명확히 분석할 수 있다.

2. **LLMCompiler-style numbered call syntax 실험**
   - `[A] Use function: intent`는 자연어 plan으로 흐르기 쉽다.
   - `1. function_name(arg=value)` 형태는 exact function name과 argument grounding을 더 강제할 수 있다.

3. **Schema name copying 강화**
   - invalid function name이 23/172개다.
   - prompt에 “copy function names character-for-character”를 더 강하게 넣거나, available function names만 별도 compact list로 user prompt 근처에 재노출하는 ablation이 필요하다.

4. **Exhaustiveness constraint 추가**
   - 현재 모델은 high-level action만 뽑고 prerequisite hop을 생략한다.
   - “include navigation/login/lookup/status-read actions when required before the final user-visible action” 같은 rule을 추가해 볼 만하다.

5. **Argument hallucination 분리 평가**
   - `unresolved inputs` 필드가 거의 활용되지 않았다.
   - prior-result-dependent argument를 concrete value로 invent하지 말고 `$previous_result` 또는 natural unresolved marker로 쓰도록 별도 examples를 넣는 것이 좋아 보인다.

6. **v0/v1 공통 evaluator로 재평가**
   - v0와 v1의 직접 비교를 원하면 v0 outputs도 현재 v1 judge로 다시 평가해야 한다.
   - 지금 보고서의 v0 비교는 방향성 참고이지 strict apples-to-apples 비교가 아니다.

## 13. Bottom line

`think_parallel_v1`은 action format 안정화와 all-hop pairwise judge 실행이라는 목적에는 성공했다. 특히 이번 run에서는 candidate coverage가 100%라서 candidate retrieval/filtering 문제와 generation 문제를 분리해서 볼 수 있다.

하지만 실험 질문인 “LLaDA가 BFCL full trajectory action plan을 hop 단위로 복구할 수 있는가?”에 대한 답은 아직 제한적이다. strict single-hop recall은 21.8%, partial-or-better도 33.4%에 그쳤다. compound까지 포함해도 41.3%다.

따라서 v1은 dependency/parallelism signal 분석으로 바로 넘어가기 전의 **action recovery diagnostic baseline**으로 보는 것이 가장 적절하다. 후속 실험은 exact function copying, exhaustive decomposition, turn-level context를 먼저 개선해야 한다.
