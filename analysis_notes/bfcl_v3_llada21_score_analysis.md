# BFCL v3 LLaDA2.1-mini 점수 분석

작성일: 2026-05-14 KST

## 분석 범위

분석 대상은 BFCL v3 single-turn subset 10개이다.

```text
simple,multiple,parallel,parallel_multiple,java,javascript,
live_simple,live_multiple,live_parallel,live_parallel_multiple
```

아래 다섯 실험을 비교한다.

| 실험 | 점수 경로 | 의미 |
|---|---|---|
| LLaDA2.1 baseline legacy prompt | `score/llada21_v3_baseline_st_20260514_005522` | BFCL legacy prompt/function-doc formatting + legacy AST decoder |
| LLaDA2.1 JSON-doc prompt + legacy decoder | `score/llada21_v3_json_st_20260513_181201` | BFCL prompt path에서 function docs만 JSON serialization으로 변경, legacy AST decoder |
| LLaDA2.1 JSON-doc prompt + v4 decoder | `score/llada21_v3_json_st_20260513_181201_v4_decoder` | 위 JSON-doc raw output을 v4 AST decoder로 재평가 |
| LLaDA2.1 native tools + native-tools decoder fix | `score/llada21_v3_native_tools_st_23587_bare_json_decoder` | tokenizer native tool template 사용, bare JSON tool-call parser fix 적용 후 재평가 |
| LLaDA2.1 native tools + exact-name instruction | `score/llada21_v3_native_tools_exact_name_st_23622` | native tool template에 exact function name 복사 instruction을 추가한 ablation |

`Direct Score`는 10개 category score JSON의 `correct_count / total_count`를 직접 합산한 값이다. `CSV Overall`은 BFCL leaderboard의 `data_overall.csv` 값이며, live/non-live/multi-turn summary weighting과 missing category 처리 때문에 direct score와 다르다.

## 요약

| 실험 | Direct Score | Non-Live AST | Live Acc | CSV Overall |
|---|---:|---:|---:|---:|
| LLaDA2.1 baseline legacy prompt | 82 / 440, 18.64% | 13.33% | 1.92% | 4.20% |
| LLaDA2.1 JSON-doc prompt + legacy decoder | 18 / 440, 4.09% | 2.33% | 0.58% | 0.81% |
| LLaDA2.1 JSON-doc prompt + v4 decoder | 18 / 440, 4.09% | 2.33% | 0.58% | 0.81% |
| LLaDA2.1 native tools + native-tools decoder fix | 191 / 440, 43.41% | 42.67% | 4.71% | 12.95% |
| LLaDA2.1 native tools + exact-name instruction | 189 / 440, 42.95% | 44.17% | 4.42% | 13.25% |

결론은 두 가지다.

1. BFCL prompt path에서는 baseline legacy prompt가 JSON-doc prompt보다 낫다. JSON-doc prompt는 raw output이 BFCL call syntax와 더 자주 어긋났고, v4 decoder로 재평가해도 이 run에서는 점수가 개선되지 않았다.
2. native tool path는 parser bug를 고친 뒤 direct score 기준으로 가장 높다. 특히 `simple`, `parallel`, `live_simple`, `live_parallel`에서 baseline보다 크게 좋아졌다. Exact-name instruction ablation은 CSV overall은 소폭 올랐지만 direct score는 소폭 낮아져, 일관된 개선이라기보다는 원인 확인용 ablation으로 해석한다.

## 카테고리별 점수

| 카테고리 | Baseline Legacy | JSON + Legacy | JSON + v4 | Native Tools + Fix | Exact-Name Ablation |
|---|---:|---:|---:|---:|---:|
| simple | 36 / 50, 72.00% | 10 / 50, 20.00% | 10 / 50, 20.00% | 46 / 50, 92.00% | 46 / 50, 92.00% |
| multiple | 1 / 50, 2.00% | 0 / 50, 0.00% | 0 / 50, 0.00% | 18 / 50, 36.00% | 20 / 50, 40.00% |
| parallel | 8 / 50, 16.00% | 1 / 50, 2.00% | 1 / 50, 2.00% | 28 / 50, 56.00% | 29 / 50, 58.00% |
| parallel_multiple | 0 / 50, 0.00% | 0 / 50, 0.00% | 0 / 50, 0.00% | 11 / 50, 22.00% | 12 / 50, 24.00% |
| java | 11 / 50, 22.00% | 0 / 50, 0.00% | 0 / 50, 0.00% | 18 / 50, 36.00% | 13 / 50, 26.00% |
| javascript | 6 / 50, 12.00% | 1 / 50, 2.00% | 1 / 50, 2.00% | 21 / 50, 42.00% | 23 / 50, 46.00% |
| live_simple | 17 / 50, 34.00% | 6 / 50, 12.00% | 6 / 50, 12.00% | 34 / 50, 68.00% | 35 / 50, 70.00% |
| live_multiple | 0 / 50, 0.00% | 0 / 50, 0.00% | 0 / 50, 0.00% | 3 / 50, 6.00% | 2 / 50, 4.00% |
| live_parallel | 3 / 16, 18.75% | 0 / 16, 0.00% | 0 / 16, 0.00% | 8 / 16, 50.00% | 5 / 16, 31.25% |
| live_parallel_multiple | 0 / 24, 0.00% | 0 / 24, 0.00% | 0 / 24, 0.00% | 4 / 24, 16.67% | 4 / 24, 16.67% |

## Native Tool Parser 수정

`score/llada21_v3_native_tools_st_23587`의 최초 점수는 0.00%였다. 하지만 result를 보면 모델 raw output은 비어 있지 않았다. 예를 들어 native tool run은 아래처럼 bare JSON tool call을 생성했다.

```json
{"name": "algebra.quadratic_roots", "arguments": {"a": 1, "b": -3, "c": 2}}
```

문제는 `LocalLLaDA21ToolsHandler.decode_ast()`가 `<tool_call>...</tool_call>` 태그 내부 JSON만 추출했다는 점이다. LLaDA2.1 tokenizer decode 과정에서 special token이 제거되거나 모델이 태그 없이 JSON만 낸 경우, parser가 유효한 tool call을 모두 `[]`로 버렸다. 그 결과 score JSON에서는 전 category가 `wrong_count` 계열로 실패했다.

수정 내용은 native-tools handler에만 국한된다.

- 기존 `<tool_call>...</tool_call>` parser는 유지한다.
- 태그가 없으면 문자열 안의 bare JSON object들을 순서대로 추출한다.
- `{"name": str, "arguments": dict}` 형태만 BFCL function call로 변환한다.
- 생성 로직과 `skip_special_tokens=True`는 변경하지 않았다.

수정 후 같은 result directory를 재사용해 evaluate-only로 재평가했다.

```text
RESULT_DIR=result/llada21_v3_native_tools_st_23587
SCORE_DIR=score/llada21_v3_native_tools_st_23587_bare_json_decoder
RUN_GENERATE=0
RUN_EVAL=1
```

이 재평가에서 CSV overall은 0.00%에서 12.95%로, direct score는 0 / 440에서 191 / 440으로 회복했다. 따라서 native-tools 최초 0점은 모델이 모든 문제를 틀린 것이 아니라, parser adapter bug로 보는 것이 맞다.

## JSON Prompt/V4 Decoder 해석

`run_exp_v3_llada2_1_json_singleturn.job`와 `run_exp_v3_llada2_1_json_v4_decoder_eval.job`는 native tool path 위에 올리는 실험이 아니다.

- JSON-doc prompt 실험은 BFCL legacy prompt path에서 function docs serialization만 JSON으로 바꾼다.
- v4 decoder 실험은 JSON-doc raw output을 BFCL AST decoder v4로 재채점한다.
- native tools 실험은 `tokenizer.apply_chat_template(..., tools=functions)`를 쓰고 BFCL legacy `[func(...)]` system prompt를 넣지 않는다.

따라서 native tools 결과는 `JSON-doc prompt + v4 decoder`와 별도로 해석해야 한다. native tools에 `BFCL_FUNCTION_DOC_SERIALIZATION=json`이나 `BFCL_AST_DECODER=v4`를 얹는 것은 실험 의미가 거의 없거나 혼동을 만든다.

## LLaDA-8B와의 비교

`bfcl_v3_prompt_serialization_experiment_plan.md`에서 다룬 기본 LLaDA는 LLaDA2.1-mini가 아니라 `backbone/llada` / LLaDA-8B-Instruct 계열이다. 같은 BFCL v3 single-turn subset과 score schema라서 숫자를 나란히 볼 수는 있지만, 모델 크기와 generation backend가 다르므로 strict apples-to-apples 비교는 아니다.

비교에 사용한 현재 v3 score directory는 다음과 같다.

| 실험 | 점수 경로 |
|---|---|
| LLaDA-8B baseline legacy prompt | `score/llada_v3_baseline_st_23553` |
| LLaDA-8B JSON-doc prompt + legacy decoder | `score/llada_v3_json_st_23567` |
| LLaDA-8B JSON-doc prompt + v4 decoder | `score/llada_v3_json_st_23567_v4_decoder` |

| 모델 / 실험 | Direct Score | Non-Live AST | Live Acc | CSV Overall |
|---|---:|---:|---:|---:|
| LLaDA2.1-mini baseline legacy prompt | 82 / 440, 18.64% | 13.33% | 1.92% | 4.20% |
| LLaDA2.1-mini JSON-doc prompt + legacy decoder | 18 / 440, 4.09% | 2.33% | 0.58% | 0.81% |
| LLaDA2.1-mini JSON-doc prompt + v4 decoder | 18 / 440, 4.09% | 2.33% | 0.58% | 0.81% |
| LLaDA2.1-mini native tools + decoder fix | 191 / 440, 43.41% | 42.67% | 4.71% | 12.95% |
| LLaDA2.1-mini native tools + exact-name instruction | 189 / 440, 42.95% | 44.17% | 4.42% | 13.25% |
| LLaDA-8B baseline legacy prompt | 132 / 440, 30.00% | 36.00% | 2.50% | 10.43% |
| LLaDA-8B JSON-doc prompt + legacy decoder | 168 / 440, 38.18% | 36.50% | 3.17% | 10.79% |
| LLaDA-8B JSON-doc prompt + v4 decoder | 241 / 440, 54.77% | 60.00% | 5.48% | 17.83% |

기본 LLaDA-8B에서는 `JSON-doc prompt + v4 decoder`가 가장 강하다. 반면 LLaDA2.1-mini의 JSON-doc/v4 decoder 실험은 개선이 없었고, native tool path에 parser fix를 적용했을 때 가장 크게 회복했다. 즉 “JSON-doc + v4 decoder” 개선은 기본 LLaDA-8B prompt/decoder 문제에는 잘 맞았지만, LLaDA2.1-mini native tool 실험에는 그대로 올릴 수 있는 처방이 아니다.

Exact-name instruction ablation은 BFCL CSV overall 기준으로는 `12.95% -> 13.25%`로 소폭 상승했지만, 10개 category direct score 기준으로는 `191 / 440 -> 189 / 440`으로 소폭 하락했다. 따라서 leaderboard summary 관점에서는 약간 유리하지만, case-level 전체 성공 수 기준에서는 native-tools decoder fix 단독 run이 더 높다.

## Best-Case Interface 비교

현재 관찰된 best run끼리 비교하면 아래 조합이다.

| 축 | LLaDA-8B Best | LLaDA2.1-mini Best |
|---|---|---|
| 모델명 | `backbone/llada` | `backbone/llada2.1-mini-native-tools` |
| 점수 경로 | `score/llada_v3_json_st_23567_v4_decoder` | `score/llada21_v3_native_tools_st_23587_bare_json_decoder` |
| 결과 경로 | `result/llada_v3_json_st_23567` | `result/llada21_v3_native_tools_st_23587` |
| 프롬프트 인터페이스 | BFCL text prompt | LLaDA2.1 tokenizer native tools |
| 함수 문서 전달 방식 | system prompt 안에 pretty JSON text로 삽입 | `tools=functions`로 chat template에 JSON tool object 전달 |
| 기대 raw output | 보통 `[func(arg=...)]` 형태의 BFCL/Python-call-like string | 이상적으로 `<tool_call>{"name": ..., "arguments": {...}}</tool_call>` 형태의 native tool JSON |
| 디코더 | BFCL AST v4 decoder | bare JSON fallback이 추가된 native-tools JSON decoder |
| Direct score | 241 / 440, 54.77% | 191 / 440, 43.41% |
| CSV overall | 17.83% | 12.95% |

이 비교는 strict한 backbone-only 비교가 아니라, 현재까지 확인한 각 모델의 가장 강한 interface끼리 비교한 것이다. LLaDA2.1-mini는 tokenizer에 tool-aware chat template이 있으므로 native tools path를 자연스러운/canonical tool-call interface로 볼 수 있다. 다만 이 실험들에서 LLaDA-8B는 같은 native tool interface를 쓰지 않는다. LLaDA-8B의 best score는 BFCL prompt path에서 JSON-formatted function docs와 v4 AST decoder를 사용한 결과다.

두 best run을 case 단위로 비교하면, 점수 차이는 대부분 남아 있는 parser 문제로 설명되지 않는다.

```text
total cases:     440
both correct:    138
only LLaDA2.1:    53
only LLaDA-8B:   103
both wrong:      146
```

LLaDA2.1-mini native tools가 더 강한 카테고리는 `simple`, `parallel`, `live_simple`이다. LLaDA-8B JSON+v4가 앞서는 카테고리는 주로 `multiple`, `parallel_multiple`, `java`, `javascript`, `live_multiple`이다.

| 카테고리 | LLaDA2.1 Native Tools + Fix | LLaDA-8B JSON + v4 |
|---|---:|---:|
| simple | 46 / 50, 92.00% | 39 / 50, 78.00% |
| multiple | 18 / 50, 36.00% | 40 / 50, 80.00% |
| parallel | 28 / 50, 56.00% | 23 / 50, 46.00% |
| parallel_multiple | 11 / 50, 22.00% | 25 / 50, 50.00% |
| java | 18 / 50, 36.00% | 27 / 50, 54.00% |
| javascript | 21 / 50, 42.00% | 30 / 50, 60.00% |
| live_simple | 34 / 50, 68.00% | 28 / 50, 56.00% |
| live_multiple | 3 / 50, 6.00% | 14 / 50, 28.00% |
| live_parallel | 8 / 16, 50.00% | 8 / 16, 50.00% |
| live_parallel_multiple | 4 / 24, 16.67% | 7 / 24, 29.17% |

LLaDA-8B는 맞고 LLaDA2.1-mini는 틀린 103개 case에서, LLaDA2.1의 주요 failure family는 다음과 같다.

```text
53 simple_function_checker
34 parallel_function_checker_no_order
8  value_error
6  type_error
2  multiple_function_checker
```

대표 case는 다음과 같다.

- `multiple_1`: candidate function에 `math.triangle_area_heron`이 있었지만 LLaDA2.1은 `math.triangle_area_on`을 생성했다. LLaDA-8B는 `math.triangle_area_heron(...)`을 생성했다.
- `multiple_114`: 정답 함수는 `prediction.evolution`이지만 LLaDA2.1은 의미상 그럴듯하지만 틀린 `calculate_probability`를 선택했다. LLaDA-8B는 `prediction.evolution(...)`을 선택했다.
- `parallel_multiple_117`: 정답 call은 `concert.book_ticket`과 `festival.book_ticket`을 구분해야 한다. LLaDA2.1은 이를 generic `book_ticket` 쪽으로 뭉개고 `add_ons` 대신 `addons`를 사용했다. LLaDA-8B는 namespaced function을 보존했다.
- `live_multiple_1034-262-0`: 정답 함수는 `audit_log_api.AuditLogApi.get_access_logs`이지만 LLaDA2.1은 `CustomDashboardsApi.get_shareable_api_tokens`를 선택했다. LLaDA-8B는 access-log API를 선택했다.

따라서 native-tools parser fix 이후 남은 LLaDA2.1의 격차는 주로 exact tool selection, namespace preservation, argument-name grounding, multi/parallel call composition 문제다. 최초 native-tools 0.00% 점수는 parser adapter bug였지만, fix 이후에도 LLaDA-8B JSON+v4보다 낮은 차이는 parser만으로 설명되지 않는다.

## 프롬프트와 Function Schema 인터페이스

두 best run은 같은 BFCL function schema를 모델에게 전달하지만, 노출되는 interface가 다르다.

### LLaDA-8B JSON-doc prompt path

`BFCL_FUNCTION_DOC_SERIALIZATION=json`은 BFCL system prompt 안의 function list를 pretty JSON text로 렌더링한다. 개념적으로 모델은 아래와 같은 일반 text/chat prompt를 보게 된다.

```text
사용 가능한 함수는 다음과 같다:
[
    {
        "name": "math.triangle_area_heron",
        "description": "Calculates the area of a triangle using Heron's formula...",
        "parameters": {
            "type": "dict",
            "required": ["side1", "side2", "side3"],
            "properties": {
                "side1": {"type": "integer", "description": "..."},
                "side2": {"type": "integer", "description": "..."},
                "side3": {"type": "integer", "description": "..."}
            }
        }
    }
]

함수 호출은 BFCL 형식으로 반환하라. 예: [func(arg=value)].
```

디코딩 전 raw output은 보통 JSON이 아니다. BFCL/Python-call-like text다.

```text
[math.triangle_area_heron(side1=3, side2=4, side3=5)]
```

모델이 바깥 bracket을 생략하면 default BFCL decoder가 AST parsing 전에 bracket을 보정한다.

```python
if not result.startswith("["):
    result = "[" + result
if not result.endswith("]"):
    result = result + "]"
```

이 decoder는 임의의 JSON tool call을 BFCL call로 바꾸지 않는다. `func(arg=...)` 같은 call expression을 기대한다.

### LLaDA2.1 native-tools path

`backbone/llada2.1-mini-native-tools`는 BFCL legacy `[func(...)]` system prompt를 추가하지 않는다. handler는 BFCL function list를 native tools로 전달한다.

```python
tokenizer.apply_chat_template(
    messages,
    tools=functions,
    add_generation_prompt=True,
    tokenize=False,
)
```

LLaDA2.1 tokenizer template은 각 tool을 `<tools>` XML tag 안에 `tojson`으로 serialize하고, native tool-call instruction을 추가한다.

```text
<tools>
{"name": "math.triangle_area_heron", "description": "...", "parameters": {...}}
{"name": "math.circle_area", "description": "...", "parameters": {...}}
</tools>

각 function call에 대해 function name과 arguments를 담은 JSON object를
<tool_call></tool_call> XML tag 안에 반환하라:
<tool_call>
{"name": <function-name>, "arguments": <args-json-object>}
</tool_call>
```

기대 raw output은 JSON tool-call content이며, 이상적으로는 아래 형태다.

```text
<tool_call>
{"name": "math.triangle_area_heron", "arguments": {"side1": 3, "side2": 4, "side3": 5}}
</tool_call>
```

관찰된 result에서는 LLaDA2.1이 같은 JSON object를 `<tool_call>` tag 없이 내는 경우가 많았다.

```json
{"name": "math.triangle_area_heron", "arguments": {"side1": 3, "side2": 4, "side3": 5}}
```

native-tools decoder fix는 tagged JSON과 bare JSON을 모두 valid native tool-call output으로 취급한 뒤, BFCL evaluator의 internal AST form으로 변환한다.

```python
[{"math.triangle_area_heron": {"side1": 3, "side2": 4, "side3": 5}}]
```

따라서 LLaDA2.1 native-tools의 function docs는 JSON-shaped이지만, LLaDA-8B JSON-doc prompt 실험과 같은 것은 아니다. LLaDA-8B는 pretty JSON을 plain prompt text로 받고 `[func(...)]`를 생성하도록 요구받는다. LLaDA2.1은 tokenizer의 native `tools=` channel을 통해 JSON tool object를 받고 JSON tool call을 생성하도록 요구받는다.

## Raw Output, Decoder, Checker 관계

BFCL에서 구분해야 할 것은 모델의 raw output과 decoder 이후의 internal representation이다.

LLaDA-8B prompt path에서 모델에게 요구하는 raw output은 `{}`가 없는 BFCL/Python-call-like string이다.

```text
[math.triangle_area_heron(side1=3, side2=4, side3=5)]
```

BFCL 기본 decoder는 이 string을 AST parse해서 checker가 비교하는 internal representation으로 바꾼다.

```python
[{"math.triangle_area_heron": {"side1": 3, "side2": 4, "side3": 5}}]
```

LLaDA2.1 native-tools path에서 모델에게 요구하는 raw output은 JSON tool call이다.

```json
{"name": "math.triangle_area_heron", "arguments": {"side1": 3, "side2": 4, "side3": 5}}
```

`LocalLLaDA21ToolsHandler.decode_ast()`는 이 JSON tool call을 같은 internal representation으로 바꾼다.

```python
[{"math.triangle_area_heron": {"side1": 3, "side2": 4, "side3": 5}}]
```

따라서 checker 단계에서는 LLaDA-8B와 LLaDA2.1 native-tools가 같은 decoded 형식으로 비교된다.

```text
LLaDA-8B:
  raw [foo(x=1)]
  -> BFCL AST decoder
  -> [{"foo": {"x": 1}}]
  -> BFCL checker

LLaDA2.1 native-tools:
  raw {"name": "foo", "arguments": {"x": 1}}
  -> LocalLLaDA21ToolsHandler.decode_ast()
  -> [{"foo": {"x": 1}}]
  -> BFCL checker
```

여기서 `[{ "foo": {"x": 1} }]`는 BFCL이 모델에게 직접 요구하는 raw output이 아니라, decoder 이후 checker가 사용하는 내부 표현이다. LLaDA2.1 native-tools decoder도 raw output을 `[foo(x=1)]` string으로 바꾸지 않고, 바로 이 내부 표현으로 변환한다.

이 관점에서 raw -> decoder -> checker pipeline은 비교 가능하다. 두 모델 모두 자기 output contract에 맞는 decoder를 거친 뒤 같은 checker로 평가된다. 다만 output contract와 decoder가 서로 다르므로, 이것은 “동일 prompt/decoder에서 backbone만 바꾼 비교”가 아니라 “각 모델의 tool-call interface를 BFCL internal format으로 정규화한 비교”다. LLaDA2.1 native-tools decoder는 함수명을 고치거나 argument를 추론하지 않고 JSON structure를 내부 표현으로 옮기는 adapter 역할만 한다.

## Multiple/Java Task 형태

`multiple` category는 대체로 하나의 user request에 대해 여러 후보 함수가 제공되고, 그중 정확한 하나를 고르는 task다. 현재 subset 기준으로 평균 후보 함수 수는 약 2.79개이고 최대 4개다.

예시:

```text
질문: Calculate the area of a triangle, given the lengths of its three sides: 3, 4, and 5.
후보 함수:
- math.triangle_area_heron(side1, side2, side3)
- math.circle_area(radius)
- math.triangle_area_base_height(base, height)
정답: math.triangle_area_heron(side1=3, side2=4, side3=5)
```

이 category에서는 함수 description과 parameter schema를 보고 semantically 맞는 함수를 고르고, 정확한 function name과 argument name을 보존해야 한다. LLaDA2.1 native-tools는 이 영역에서 `math.triangle_area_on`처럼 존재하지 않는 비슷한 이름을 만들거나, `prediction.evolution` 대신 `calculate_probability`처럼 의미상 가까워 보이지만 틀린 후보를 고르는 실패가 많았다.

`java`와 `javascript` category는 후보 함수가 보통 하나뿐이다. 현재 subset 기준으로 평균 후보 함수 수는 1.00개다. 대신 함수명이 Java class/method 또는 JavaScript function name 형태이고, argument type/name/value를 언어권 schema에 맞게 정확히 유지해야 한다.

Java 예시:

```text
질문: Firebird database view 'EmployeeView'의 full SQL creation script with header 생성
후보 함수:
- FireBirdUtils.getViewSourceWithHeader(monitor, view, source)
정답:
- FireBirdUtils.getViewSourceWithHeader(
    monitor="dbMonitor",
    view="EmployeeView",
    source="SELECT * FROM Employee WHERE status = 'active'"
  )
```

LLaDA2.1 native-tools의 실제 실패 예시는 `FireBirdUtils.getViewSourceWithHeader` 대신 `FireBirdUtils.getViewWithHeader`를 생성한 경우다. 후보가 하나뿐인데도 method name 일부를 생략하거나 바꾸는 것이므로, 이쪽은 tool selection보다는 exact name copying/name grounding 문제가 강하다.

또 다른 Java 예시는 boolean/type grounding 문제다.

```text
정답: InsnDecoder.invokePolymorphic(insn="instructionData", isRange=true)
LLaDA2.1 출력: {"name": "InsnDecoder.invokePolymorphic", "arguments": {"insn": "<instructionData>", "isRange": "true"}}
```

함수명은 맞았지만 `instructionData`에 불필요한 angle bracket이 붙고, boolean `true`가 string `"true"`로 출력되어 value/type mismatch가 발생했다.

## LLaDA2.1이 Multiple에 약한 이유에 대한 추론

현재 결과만으로 단정할 수는 없지만, case-level pattern을 보면 LLaDA2.1 native-tools가 `multiple`에서 약한 이유는 다음 쪽으로 추론된다.

1. Native JSON output format 자체는 안정적이다. Parser fix 이후 `simple`은 46 / 50, `parallel`은 28 / 50까지 올라갔다. 따라서 multiple 약점은 JSON syntax를 못 맞춰서라기보다, 후보 함수 중 정확한 schema entry를 고르는 문제에 가깝다.
2. `multiple`은 평균 약 2.79개의 후보 함수가 있고, 서로 비슷한 domain의 함수가 함께 주어진다. 예를 들어 triangle area task에서 Heron formula와 base-height formula가 함께 나온다. LLaDA2.1은 이때 exact candidate name을 복사하기보다 의미상 그럴듯한 이름을 생성하는 경향이 있었다.
3. Native tool template은 함수 schema를 JSON tool object로 주지만, BFCL의 `[func(...)]` prompt처럼 “반드시 제공된 함수명 그대로 출력하라”는 pressure가 충분하지 않을 수 있다. 실제 실패는 없는 함수명 생성, namespace 누락, 비슷한 후보 선택으로 많이 나타났다.
4. 모델 크기보다는 학습된 tool-call interface, prompt salience, identifier copying 특성이 영향을 주는 것으로 보는 편이 더 타당하다. 특히 `math.triangle_area_heron` -> `math.triangle_area_on`, `FireBirdUtils.getViewSourceWithHeader` -> `FireBirdUtils.getViewWithHeader`처럼 긴 identifier를 정확히 복사하는 능력이 LLaDA-8B JSON+v4 setting보다 약해 보인다.
5. `multiple`에서 LLaDA-8B JSON+v4는 40 / 50, LLaDA2.1 native-tools는 18 / 50이다. 격차가 큰 failure family도 `simple_function_checker:wrong_func_name`이 많다. 이는 decoder 이후 checker가 동일한 상태에서도 LLaDA2.1 decoded result의 함수명 자체가 틀렸다는 뜻이다.

따라서 다음 개선 방향은 decoder보다 prompt/interface 쪽이다. 예를 들어 native tools prompt에 “function name은 `<tools>` 안에 제공된 `name` 값을 정확히 복사하고 새 이름을 만들지 말라”는 instruction을 추가하거나, decoding 후 후보 함수명과 exact match하지 않는 output을 별도 분석하는 방식이 우선이다. 단, 후자는 post-hoc correction이 될 수 있으므로 성능 비교에서는 별도 run으로 분리해야 한다.

## Java/JavaScript 실패 사례와 해석

LLaDA-8B JSON+v4는 맞고 LLaDA2.1 native-tools는 틀린 case만 보면, `java`와 `javascript`에서도 양상이 조금 다르다.

```text
java:
  both correct: 14
  only LLaDA2.1 correct: 4
  only LLaDA-8B correct: 13
  both wrong: 19

javascript:
  both correct: 17
  only LLaDA2.1 correct: 4
  only LLaDA-8B correct: 13
  both wrong: 16
```

`java`에서 LLaDA2.1이 LLaDA-8B 대비 잃는 13개 case의 주요 원인은 `wrong_func_name`이다.

```text
8 simple_function_checker:wrong_func_name
1 simple_function_checker:missing_required
1 simple_function_checker:wrong_count
1 type_error:java
1 value_error:others
1 value_error:string
```

대표 예시는 다음과 같다.

```text
정답:
FireBirdUtils.getViewSourceWithHeader(...)

LLaDA2.1:
{"name": "FireBirdUtils.getViewWithHeader", ...}

LLaDA-8B:
[FireBirdUtils.getViewSourceWithHeader(...)]
```

```text
정답:
configStorage.dynamicCredentialsScheduledExecutorService(...)

LLaDA2.1:
{"name": "configStorage.dynamicCredentialsExecutorService", ...}

LLaDA-8B:
[configStorage.dynamicCredentialsScheduledExecutorService(...)]
```

```text
정답:
DB2Tablespace.resolveTablespaceReference(...)

LLaDA2.1:
{"name": "DB2TablespaceReference", ...}

LLaDA-8B:
[DB2Tablespace.resolveTablespaceReference(...)]
```

즉 Java에서는 후보 함수가 하나뿐이어도 긴 class/method identifier를 정확히 복사하지 못하고 일부를 생략하거나 재구성하는 문제가 크다. 이는 multiple의 wrong function name과 같은 계열의 name grounding/copying 문제다.

`javascript`에서 LLaDA2.1이 LLaDA-8B 대비 잃는 13개 case는 `wrong_func_name`도 있지만, language-specific type/value mismatch가 더 두드러진다.

```text
5 type_error:js
4 simple_function_checker:wrong_func_name
2 value_error:others
1 simple_function_checker:wrong_count
1 value_error:string
```

대표 예시는 다음과 같다.

```text
정답:
fetchSalesDepartmentRecords(databaseName="employeeRecords", queryFunction=getSales)

LLaDA2.1:
{"name": "getSales", "arguments": {"databaseName": "employeeRecords", "queryFunction": "function(record) { ... }"}}

LLaDA-8B:
[fetchSalesDepartmentRecords(databaseName=employeeRecords, queryFunction=getSales)]
```

이 case에서는 LLaDA2.1이 함수명 자체를 callback/helper name인 `getSales`로 잘못 선택했고, `queryFunction`도 identifier `getSales`가 아니라 함수 body string으로 확장했다.

또 다른 유형은 native JSON이 literal value를 충실하게 내면서 JS checker의 기대와 어긋나는 경우다.

```text
정답:
getActiveDataEntries(listElement="listElement", attribute="data-active", value=true)

LLaDA2.1:
{"name": "getActiveDataEntries", "arguments": {"listElement": "listElement", "attribute": "data-active", "value": true}}

failure:
type_error:js, parameter 'value'에서 bool이 들어왔다고 판단
```

```text
정답:
configureShaderMaterial(object3D="meshObject", textures=textureList, property="materialProps")

LLaDA2.1:
{"name": "configureShaderMaterial", "arguments": {"property": "materialProps", "textures": ["texture1", "texture2"], "object3D": "meshObject"}}

LLaDA-8B:
[configureShaderMaterial(property='materialProps', textures='textureList', object3D='meshObject')]
```

이런 case는 LLaDA2.1이 자연어에서 값을 풀어서 literal JSON으로 만들지만, BFCL 정답은 prompt에 등장한 변수명/identifier를 보존하기를 기대한다. LLaDA-8B의 `[func(...)]` call-like output은 `textureList`, `getSales`, `shapeStatements` 같은 identifier를 그대로 쓰는 경향이 있어 이 benchmark에서는 유리할 수 있다.

## 현재 예상 원인

LLaDA2.1이 LLaDA-8B보다 큰 계열이라는 점을 고려하면, 단순히 모델 크기 때문에 LLaDA-8B가 더 잘한다는 설명은 설득력이 낮다. 현재 결과에서 더 그럴듯한 원인은 다음과 같다.

1. **Exact identifier copying 압력 차이**  
   LLaDA-8B JSON+v4 setting은 raw output이 `[function_name(...)]`이므로 답의 첫 token부터 후보 함수명을 그대로 복사해야 한다. 반면 LLaDA2.1 native-tools는 JSON object의 `"name"` field 안에 함수명을 넣는다. 이 차이가 긴 namespaced function name을 그대로 복사하는 압력에 영향을 줄 수 있다.

2. **Native tools template의 compact JSON salience 문제**  
   LLaDA2.1 template의 `tojson`은 tool object를 JSON string으로 serialize한다. 이 schema는 내용상 BFCL function schema와 같지만, pretty JSON system prompt처럼 indentation과 line break로 `name`, `description`, `parameters`가 크게 분리되어 보이는 형태는 아니다. 여러 후보가 있는 `multiple`에서는 exact `name` field의 salience가 부족했을 가능성이 있다.

3. **JSON output 문법 부담은 주원인으로 보기 어렵다**  
   LLaDA2.1은 parser fix 이후 `simple` 46 / 50, `parallel` 28 / 50을 기록했고, 실패 case도 malformed JSON보다는 `wrong_func_name`, `wrong_count`, type/value mismatch가 많았다. 따라서 `{`, `"`, `:`가 많아서 JSON을 못 쓴다는 설명보다는, JSON 안에 어떤 function name/value를 넣을지의 grounding 문제가 더 핵심이다.

4. **Identifier vs literal value 보존 차이**  
   JavaScript와 일부 Java case에서는 BFCL이 `getSales`, `textureList`, `docFields`, `userProfile` 같은 변수명/identifier를 보존하기를 기대한다. LLaDA2.1 native JSON은 이를 실제 literal 값, 함수 body, list/dict로 풀어 쓰는 경향이 있고, 이 때문에 value/type mismatch가 난다. LLaDA-8B의 call-like raw output은 identifier를 그대로 두는 방식과 더 잘 맞는 경우가 있다.

5. **Tool selection과 argument grounding이 동시에 얽힘**  
   `multiple`에서는 후보 함수 선택이 먼저 틀리고, `java/javascript`에서는 후보가 하나여도 긴 function name이나 argument value representation이 틀어진다. 공통적으로 “schema에 있는 표면형을 그대로 선택/복사/보존하는 능력”이 LLaDA2.1 native-tools의 현재 병목으로 보인다.

따라서 다음 실험 가설은 “LLaDA2.1이 smaller/weaker라서”가 아니라, native tools prompt/interface가 BFCL의 exact-name benchmark와 덜 맞는다는 쪽이 더 강하다. 이를 확인하려면 native tool template 또는 wrapper prompt에 아래 성격의 instruction을 추가한 별도 run이 필요하다.

```text
Use only function names exactly as written in <tools>.
Do not invent, shorten, rename, translate, or paraphrase function names.
For arguments that refer to variables, functions, objects, or handles named in the user query,
preserve the identifier string instead of expanding it into literal content.
```

이 실험에서 `multiple`의 `wrong_func_name`과 `java/javascript`의 identifier/value mismatch가 줄어들면, 현재 추론이 맞다는 강한 증거가 된다.

## Exact-Name Instruction Ablation 결과

위 가설 중 function-name copying pressure만 최소 변경으로 확인하기 위해 아래 instruction 두 문장을 native-tools system message로 추가한 ablation을 수행했다.

```text
Use only function names exactly as written in <tools>.
Do not invent, shorten, rename, or translate function names.
```

실험 경로는 다음과 같다.

```text
log:    /data/home/martellato41/research/logs/run_exp_v3_llada2_1_native_tools_exact_name_singleturn.23622.log
result: result/llada21_v3_native_tools_exact_name_st_23622
score:  score/llada21_v3_native_tools_exact_name_st_23622
```

로그에서 확인한 주요 설정은 다음과 같다.

```text
MODEL_NAME: backbone/llada2.1-mini-native-tools
LLADA21_NATIVE_TOOLS_EXACT_NAME_INSTRUCTION: 1
BFCL_FUNCTION_DOC_SERIALIZATION: legacy
BFCL_AST_DECODER: legacy
RUN_GENERATE: 1
RUN_EVAL: 1
```

점수 변화는 mixed result다.

| 카테고리 | Native Tools + Fix | Exact-Name Ablation | 변화 |
|---|---:|---:|---:|
| simple | 46 / 50 | 46 / 50 | 0 |
| multiple | 18 / 50 | 20 / 50 | +2 |
| parallel | 28 / 50 | 29 / 50 | +1 |
| parallel_multiple | 11 / 50 | 12 / 50 | +1 |
| java | 18 / 50 | 13 / 50 | -5 |
| javascript | 21 / 50 | 23 / 50 | +2 |
| live_simple | 34 / 50 | 35 / 50 | +1 |
| live_multiple | 3 / 50 | 2 / 50 | -1 |
| live_parallel | 8 / 16 | 5 / 16 | -3 |
| live_parallel_multiple | 4 / 24 | 4 / 24 | 0 |
| total direct | 191 / 440 | 189 / 440 | -2 |
| CSV overall | 12.95% | 13.25% | +0.30 pp |

Case-level로는 15개가 새로 맞고, 17개가 새로 틀렸다.

```text
both correct: 174
only native-tools fix correct: 17
only exact-name ablation correct: 15
both wrong: 234
```

긍정적인 변화는 예상대로 `multiple`과 일부 JavaScript identifier 보존 case에서 나타났다.

```text
multiple_1:
  old: {"name": "math.triangle_area_on", ...}
  new: {"name": "math.triangle_area_heron", ...}
  result: wrong_func_name -> correct

multiple_62:
  old: {"name": "nature_park.find_nearby", "arguments": {"amenities": [...]}}
  new: {"name": "nature_park.find_nearby", "arguments": {"features": [...]}}
  result: missing_required -> correct

javascript_15:
  old: labels/data/chartLayout를 literal list/object로 확장
  new: axisLabelsArray/dataPointsArray/chartLayoutObject identifier 보존
  result: wrong_count -> correct

javascript_48:
  old: oldVnode/vnode를 HTML literal로 확장
  new: oldVirtualNode/newVirtualNode identifier 보존
  result: value_error -> correct
```

하지만 부정적인 변화도 분명했다. 특히 `java`에서는 기존에 맞던 긴 class/method name이 instruction 추가 후 오히려 짧아지거나 재구성되는 case가 늘었다.

```text
java_17:
  old: GenericTypesVisitor.attachGenericTypesInfo
  new: GenericTypes.attachGenericTypesInfo
  result: correct -> wrong_func_name

java_53:
  old: VotingOnlyNodePlugin.fullMasterWithOlderState
  new: VotingOnlyNode.fullMasterWithOlderState
  result: correct -> wrong_func_name

java_69:
  old: DurationImpl.alignSigns
  new: alignSigns
  result: correct -> wrong_func_name
```

`live_parallel`에서도 기존에 맞던 value가 바뀌어 match가 깨졌다.

```text
live_parallel_2-0-2:
  old: Boston, MA unit=fahrenheit / San Francisco, CA unit=fahrenheit
  new: Boston, MA unit=celsius / San Francisco, CA unit=fahrenheit
  result: correct -> cannot_find_match

live_parallel_3-0-3:
  old: 여러 location의 unit=fahrenheit
  new: 여러 location의 unit=celsius
  result: correct -> cannot_find_match
```

해석은 다음과 같다.

1. Exact-name instruction은 `multiple`에서 일부 wrong function name을 실제로 고쳤다. 따라서 “native tools prompt의 exact-name pressure 부족” 가설은 일부 지지된다.
2. 하지만 instruction 두 문장만으로 전반 성능이 개선되지는 않았다. 전체 direct score는 -2이고, failure type 전체 집계에서 `wrong_func_name`은 오히려 `100 -> 111`로 증가했다.
3. Java에서 악화된 사례는 단순히 “함수명을 정확히 복사하라”는 instruction이 긴 class/method identifier 보존을 안정적으로 강화하지 못한다는 것을 보여준다.
4. JavaScript 일부 gain은 exact function name보다 identifier/literal 보존 차이에서 나온다. 즉 function-name instruction만으로도 출력 분포가 바뀌었지만, 원래 가설의 모든 부분을 직접 겨냥하지는 못했다.
5. 이 ablation은 원인 분석에는 유용하지만, 현재 best direct-score run으로 채택하기에는 부족하다. Direct score 기준으로는 `native tools + decoder fix`가 더 높고, CSV overall 기준으로만 exact-name ablation이 소폭 높다.

따라서 다음에 더 파본다면 instruction을 더 세게 넣기보다는, function-name copying과 identifier preservation을 분리한 ablation이 필요하다. 예를 들어 function name만 강조하는 실험과, variable/function/object identifier 보존을 별도로 강조하는 실험을 나누어야 한다.

## 실패 패턴

주요 실패 유형은 다음과 같다.

| 실험 | 주요 실패 유형 |
|---|---|
| Baseline legacy prompt | `ast_decoder:decoder_failed` 328, `ast_decoder:decoder_wrong_output_format` 16, `type_error:simple` 4, `simple_function_checker:wrong_func_name` 4 |
| JSON-doc + legacy decoder | `ast_decoder:decoder_failed` 411, `ast_decoder:decoder_wrong_output_format` 9 |
| JSON-doc + v4 decoder | `ast_decoder:decoder_failed` 410, `ast_decoder:decoder_wrong_output_format` 9 |
| Native tools + decoder fix | `simple_function_checker:wrong_func_name` 100, `parallel_function_checker_no_order:wrong_count` 48, `parallel_function_checker_no_order:cannot_find_match` 41 |
| Exact-name ablation | `simple_function_checker:wrong_func_name` 111, `parallel_function_checker_no_order:wrong_count` 47, `parallel_function_checker_no_order:cannot_find_match` 43 |

baseline/JSON prompt path의 병목은 주로 BFCL AST syntax를 안정적으로 맞추지 못하는 것이다. native tools + fix에서는 decoder가 더 이상 전체를 버리지 않으며, 남은 실패는 주로 잘못된 함수 선택, 병렬 호출 개수, argument value/type mismatch 쪽이다.

## 결론

1. LLaDA2.1 single-turn 비교에서 현재 가장 강한 축은 `native tools + native-tools decoder fix`이다.
2. native tools 최초 0점 run은 parser bug의 산물이라 성능 비교표에는 fixed score를 함께 명시해야 한다.
3. JSON-doc prompt와 v4 decoder는 BFCL prompt/AST parser 계열 실험으로 유지하고, native tools 실험과 섞어 해석하지 않는다.
4. Exact-name instruction ablation은 `multiple`과 `javascript` 일부 case를 개선했지만 `java`와 `live_parallel`을 악화시켜 direct score 기준 best는 되지 못했다.
5. 다음 개선은 native tools에서 function-name copying과 identifier preservation을 분리해서 검증하는 방향이 우선이다.
