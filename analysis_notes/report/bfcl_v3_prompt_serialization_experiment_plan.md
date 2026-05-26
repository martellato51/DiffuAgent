# BFCL v3 프롬프트 직렬화 및 디코더 검증 노트

날짜: 2026-05-12

## 1. 실험 배경

LLaDA 8B Instruct 모델에 대해 Bitter Lesson 논문의 DiffuAgent 프레임워크로
BFCL 재현 실험을 진행했다. 그런데 초기 결과가 논문 수치를 거의 2배
넘게 상회했다. qwen3 8B는 비교적 논문 재현 범위와 비슷했기 때문에,
문제는 LLaDA 재현 세팅 또는 평가 경로에 더 강하게 있을 가능성이 커졌다.

지난 미팅 때 공유했던 초기 재현 표는 아래와 같다. 이 표는 이후 확인한
v3 whitelist 기준 재현이 아니라, 잘못된 초기 재현 세팅의 결과로 기록한다.
`Avg.`는 category percentage의 단순평균이다.

### 초기 잘못 재현된 결과

#### Non-Live

| | Py simple | Java | JS | Multiple | Parallel | Multiple parallel | Non-Live Avg. |
|---|---:|---:|---:|---:|---:|---:|---:|
| **Qwen3-8B** | 96.0% | 68.0% | 76.0% | 90.0% | 88.0% | 94.0% | **85.3%** |
| **LLaDA-8B** | 80.0% | 46.0% | 48.0% | 66.0% | 32.0% | 38.0% | **51.7%** |

#### Live

| | Live simple | Live multiple | Live parallel | Live multiple parallel | Live Avg. |
|---|---:|---:|---:|---:|---:|
| **Qwen3-8B** | 78.0% | 82.0% | 75.0% | 62.5% | **74.4%** |
| **LLaDA-8B** | 38.0% | 40.0% | 31.3% | 25.0% | **33.6%** |

이 결과는 논문 재현 실패로 보고, 재현 세팅을 다시 정리했다.

## 2. 재현 세팅 재정렬

초기 실험에서는 subset을 만들 때 각 category의 앞 50개를 임의로 고르는
방식에 가까운 whitelist를 사용했다. 이후 원본 repo 쪽에 v3용 whitelist
파일이 따로 있음을 확인했다.

따라서 재현 실험은 다음 방향으로 다시 맞췄다.

```text
1. 논문 재현에 사용된 것으로 보이는 v3 whitelist를 사용한다.
2. 현재 DiffuAgent 트리의 BFCL v4가 아니라, BFCL v3를 GitHub에서 별도 checkout한다.
3. v3 category 체계를 그대로 사용한다.
4. DiffuAgent/LLaDA handler는 v3 checkout에서 실행 가능하도록 맞춘다.
```

이후 분석의 목적은 다음으로 바뀌었다.

```text
v3 whitelist와 BFCL v3 checkout을 사용했는데도 왜 LLaDA 결과가 동일한 hite_list를 적용한 v4 결과와 다르게 나오는가?
그 차이가 데이터, runtime, handler, prompt, decoder 중 어디서 오는가?
```

## 3. 원인 후보를 지워간 과정

whitelist 세팅을 맞춘 뒤에 v3/v4 결과 차이가 남았기 때문에, 가능한 원인을
하나씩 제거했다.

### 1. subset id 및 데이터 변화 문제

`test_case_ids_to_generate_v3.json`로 선택한 id를 사용했기 때문에, 먼저
잘못된 id subset을 쓴 것이 아닌지, 또는 같은 logical id라도 v3/v4에서
실제 데이터 내용이 크게 바뀐 것이 아닌지 확인했다.

비교 기준:

```text
v3 simple      <-> v4 simple_python
v3 java        <-> v4 simple_java
v3 javascript  <-> v4 simple_javascript

나머지 category는 같은 이름끼리 비교:
multiple, parallel, parallel_multiple,
live_simple, live_multiple, live_parallel, live_parallel_multiple
```

renamed category는 id를 canonicalize해서 비교했다.

```text
simple_python_0      -> simple_0
simple_java_0        -> java_0
simple_javascript_0  -> javascript_0
```

결론:

```text
subset id 및 데이터 변화는 큰 score gap의 주원인으로 보기 어렵다.
matched id 기준 function schema는 모든 비교 category에서 100% 동일했다.
question text와 possible answer 차이는 소수 예외 수준이었다.
```

Main data 비교:

| v3 category | v4 category | common | same question | same function schema | same entry excluding id |
|---|---|---:|---:|---:|---:|
| simple | simple_python | 400 | 400/400, 100.0% | 400/400, 100.0% | 400/400, 100.0% |
| java | simple_java | 100 | 100/100, 100.0% | 100/100, 100.0% | 100/100, 100.0% |
| javascript | simple_javascript | 50 | 50/50, 100.0% | 50/50, 100.0% | 50/50, 100.0% |
| multiple | multiple | 200 | 200/200, 100.0% | 200/200, 100.0% | 200/200, 100.0% |
| parallel | parallel | 200 | 198/200, 99.0% | 200/200, 100.0% | 198/200, 99.0% |
| parallel_multiple | parallel_multiple | 200 | 200/200, 100.0% | 200/200, 100.0% | 200/200, 100.0% |
| live_simple | live_simple | 258 | 256/258, 99.2% | 258/258, 100.0% | 256/258, 99.2% |
| live_multiple | live_multiple | 1053 | 1052/1053, 99.9% | 1053/1053, 100.0% | 1052/1053, 99.9% |
| live_parallel | live_parallel | 16 | 16/16, 100.0% | 16/16, 100.0% | 16/16, 100.0% |
| live_parallel_multiple | live_parallel_multiple | 24 | 24/24, 100.0% | 24/24, 100.0% | 24/24, 100.0% |

Possible answer 비교:

| v3 category | v4 category | common | same possible answer |
|---|---|---:|---:|
| simple | simple_python | 400 | 399/400, 99.8% |
| java | simple_java | 100 | 100/100, 100.0% |
| javascript | simple_javascript | 50 | 49/50, 98.0% |
| multiple | multiple | 200 | 200/200, 100.0% |
| parallel | parallel | 200 | 198/200, 99.0% |
| parallel_multiple | parallel_multiple | 200 | 200/200, 100.0% |
| live_simple | live_simple | 258 | 255/258, 98.8% |
| live_multiple | live_multiple | 1053 | 1053/1053, 100.0% |
| live_parallel | live_parallel | 16 | 15/16, 93.8% |
| live_parallel_multiple | live_parallel_multiple | 24 | 24/24, 100.0% |

따라서 단순히 “id가 틀렸다” 또는 “v3/v4 데이터가 많이 달라졌다”로는
LLaDA의 큰 차이를 설명하기 어렵다. qwen3 8B가 v3/v4 및 논문 재현 범위와
비교적 비슷한 수치를 보인 것도 이 판단을 강화한다.

다만 완전히 동일한 것은 아니고, 소수의 question text 또는 possible answer
차이는 있었다. 대표 예시는 다음과 같다.

#### Question text 차이 예시

| ID | 차이 |
|---|---|
| `parallel_84` | v3에는 첫 번째 자동차의 가속도 계산까지 포함되어 있고, v4는 그 부분이 빠져 세 대의 displacement 계산으로 시작한다. |
| `parallel_170` | v3는 2년, 다음 3년, 남은 5년 구간을 묻고, v4는 first 2 years, first 3 years, first 5 years처럼 누적 기간 표현으로 바뀌었다. |
| `live_simple_137-90-0` | v3는 `November 1, 2023 at 10pm CEST`, v4는 `November 1, 2023 at 8pm London time`으로 표현이 다르다. |
| `live_multiple_44-17-0` | v3에는 transaction summary 요청 문장이 추가로 있고, v4에는 해당 문장이 없다. |

#### Possible answer 차이 예시

| ID | v3 possible answer | v4 possible answer | 의미 |
|---|---|---|---|
| `simple_363` | `find_closest` | `restaurant_search.find_closest` | function name에 namespace prefix가 추가됨 |
| `javascript_41` | `queue` | `queue_1` | JavaScript function name이 다름 |
| `parallel_155` | 두 번째 call의 `standardize` 허용값이 `[true, false]` | 두 번째 call의 `standardize` 허용값이 `[true]` | 정답 허용 범위가 좁아짐 |
| `parallel_158` | `random.normalvariate` call 2개 | 같은 call이 각각 중복되어 총 4개 | 병렬 호출 개수 ground truth가 다름 |
| `live_simple_137-90-0` | `dateOrTime`: `2023-11-01T22:00:00` | `dateOrTime`: `2023-11-01T20:00:00` | timezone 표현 차이가 정답 시간 차이로 반영됨 |
| `live_parallel_9-5-0` | `operating_system0` | `operating_system` | parameter 이름 typo 또는 schema 정정으로 보이는 차이 |

이 예외들은 실제로 존재하므로 완전히 무시하면 안 된다. 하지만 양적으로는
소수이고, 특히 function schema는 matched id 전체에서 100% 동일했다. 따라서
이 예외들이 LLaDA v3/v4의 큰 score gap을 주도한다고 보기는 어렵다.

### 2. Fast-dLLM float32/float64 문제

이전에는 single-turn에서 float64, multiturn에서 OOM 때문에 float32를 썼다.
새 실험에서는 모두 float32로 돌렸기 때문에, softmax dtype 변화가 원인일
수 있다고 의심했다.

그래서 Fast-dLLM 변경을 되돌려 원래 float64 softmax 경로로 복구한 뒤
single-turn을 다시 확인했다.

결론:

```text
float64로 되돌려도 v3 LLaDA single-turn 결과의 큰 차이는 해소되지 않았다.
따라서 주된 원인은 Fast-dLLM float32/float64 차이가 아니다.
```

### 3. v3 shim handler 문제

v3 checkout에 DiffuAgent handler를 맞추기 위해 compatibility layer를 만들었다.
그래서 v4 DiffuAgent handler와 완전히 같은 경로가 아니라서 문제가 생겼을
가능성을 확인했다.

문제는 BFCL v3와 현재 DiffuAgent BFCL 트리의 handler API가 다르다는 점이다.
v4 쪽은 `DiffuagentBaseHandler -> DLLMHandler -> LocalDLLMHandler` 경로를
쓴다. 이 경로 안에는 backend 선택, feature backend, prompt formatting,
DLLM query, response cleanup이 한 흐름으로 들어 있다.

반면 v3 checkout은 해당 base class 구조가 없기 때문에, v4 handler를 그대로
상속해서 쓸 수 없었다. 그래서 v3에서는 `BackbonePromptingHandler`라는
v3-compatible base를 만들고, 그 위에 `LocalDLLMHandler`를 얹는 shim을
구성했다.

v3 shim에서 v4와 맞춘 항목은 다음과 같다.

| 항목 | v4 DiffuAgent 경로 | v3 shim에서 맞춘 방식 |
|---|---|---|
| prompt 전처리 | `func_doc_language_specific_pre_processing()` 후 `system_prompt_pre_processing_chat_model()` 사용 | 같은 함수들을 호출해서 BFCL prompting message를 구성 |
| formatted prompt logging | `json.dumps({"messages": messages, "functions": function}, ensure_ascii=False)` | 같은 형태로 `formatted_prompt`를 만들어 `inference_input_log`에 저장 |
| LLaDA backend | `LocalDLLMBackend`로 Fast-dLLM LLaDA를 in-process 호출 | 같은 `LocalDLLMBackend` wrapper를 v3 checkout에 복사/적용 |
| token budget | input token 수와 `LLADA_CONTEXT_LENGTH`, `LLADA_GEN_LENGTH`로 max token 계산 | 같은 방식으로 `max_tokens` 계산 |
| query path | v4 base의 `_query_dllm(messages, function, quiet=False)` | v3 shim의 `_query_prompting()`에서 `self.dllm.chat_completion(...)` 직접 호출 |
| `</think>` cleanup | diagnostic mode가 아니면 `</think>` 뒤만 남김 | 같은 조건으로 `response.text = response.text.split("</think>", 1)[-1].strip()` 적용 |
| lazy loading | 첫 inference 때 backend 초기화 | `self.dllm is None`이면 `_initialize_backend()` 호출 |
| selector/editor | backbone-only 평가에서는 사용하지 않음 | `_initialize_features()`를 no-op으로 두고 selector/editor 없이 실행 |

```text
v4 LocalDLLMHandler:
  DiffuagentBaseHandler 기반
  backend="dllm", feature_backend="dllm"
  _format_prompt(), _query_dllm(), _parse_query_response_prompting()을 base 경로에서 사용

v3 LocalDLLMHandler shim:
  BackbonePromptingHandler(BaseHandler) 기반
  v3 BFCL API에 맞게 message/add turn/decode 메서드 직접 구현
  v4의 formatted_prompt, DLLM query, </think> cleanup, lazy loading을 수동으로 재현
```

즉 “v4 handler를 그대로 복사해서 썼다”가 아니라, v3 BFCL이 요구하는 handler
interface 위에서 v4 backbone-only DLLM 동작을 맞춘 것이다.

이 shim을 맞춘 뒤 확인한 내용:

```text
handler query/cleanup 경로를 v4-style에 가깝게 맞춰도,
v3 LLaDA raw output의 큰 형식 차이는 그대로 남았다.
```

특히 handler를 맞춘 뒤에도 LLaDA raw output에서는
`function({"arg": value})` 형태와 missing required parameter 문제가 계속
두드러졌다. 따라서 handler shim 차이는 완전히 0이라고 할 수는 없지만,
이 시점의 큰 score gap을 설명하는 주원인으로 보기는 어려웠다.

남아 있는 handler 관련 차이는 다음과 같다.

```text
1. v3 shim은 v4 DiffuagentBaseHandler를 직접 상속하지 않는다.
2. backend/feature_backend autodetection 구조는 v4보다 단순하다.
3. v3 BFCL의 add-turn / parse-response interface에 맞춰 일부 메서드를 재구현했다.
4. selector/editor mixin은 backbone-only 실험이므로 사용하지 않는다.
```

### 4. 프롬프트 직렬화 문제

v3와 v4의 전체 프롬프트를 비교하면서 가장 강한 차이가 보였다.

v3는 function docs를 Python 객체 repr처럼 넣는다.

```python
[{'name': 'foo', 'parameters': {'type': 'dict'}}]
```

v4-style 경로는 pretty JSON처럼 넣는다.

```json
[
    {
        "name": "foo",
        "parameters": {
            "type": "dict"
        }
    }
]
```

이 차이는 LLaDA에게 매우 크게 작용했다. v3에서 function docs를 pretty
JSON으로 바꾸자 raw output 분포가 v4 reference와 가까워졌다.

결론:

```text
프롬프트 직렬화는 LLaDA raw output 형식을 바꾸는 핵심 원인이다.
```

#### Raw output 형식 관찰

프롬프트 직렬화 실험 이후, LLaDA의 차이는 단순 score 차이가 아니라 raw
output 형식 차이로도 설명된다는 점이 분명해졌다.

여기서 `v3 초기`는 BFCL v3 checkout 그대로, Python repr-style function
docs형식의 원본 프롬프트를 쓴 결과이고, `v4 reference`는 기존 DiffuAgent BFCL 트리에서
재현했었던 LLaDA 결과를 뜻한다. `v3 pretty-JSON prompt 수정 후`는 v3의
function docs 직렬화만 v4-style pretty JSON에 가깝게 바꾼 결과다.

| 실행/조건 | 주로 관찰된 출력 경향 | 예시 |
|---|---|---|
| v3 초기 | Python repr style을 따라가는 positional dict call | `function({"arg": value})` |
| v4 reference | decoder가 기대하는 keyword-style call | `function(arg=value)` |
| v3 pretty-JSON prompt 수정 후 | v4 reference에 가까운 keyword-style call 증가 | `function(arg=value)` |

하지만 score는 raw output 변화만큼 회복되지 않았다. 그래서 추가 원인을
찾게 됐다.

따라서 이후 분석은 “LLaDA가 왜 서로 다른 함수 호출 형식을 내는가”와
“그 형식을 v3/v4 decoder가 어떻게 처리하는가”를 같이 보게 됐다.

### 5. v3/v4 Python decoder 차이

pretty JSON prompt 이후 LLaDA는 v4와 비슷하게 multiline list 형태의 출력을
더 많이 만들었다.

예:

```python
[
    foo(a=1),
    bar(b=2)
]
```

그런데 v3 decoder는 이 출력을 파싱하기 전에 `[]`를 제거한다.

```python
cleaned_input = input_str.strip("[]'")
```

그러면 위 출력이 다음처럼 바뀐다.

```python
    foo(a=1),
    bar(b=2)
```

이 문자열은 Python expression으로 파싱할 수 없어서 `unexpected indent`가
난다.

반면 v4-style decoder는 대괄호를 유지한다.

```python
cleaned_input = input_str.strip().strip("'")
```

그래서 multiline list expression이 정상적으로 `ast.parse()`에 들어간다.

결론:

```text
v3 json-prompt 결과가 v4 raw output과 비슷해졌는데도 점수가 낮은 이유는,
v3 decoder가 v4-style multiline list output을 잘 못 받아서다.
```

## 4. 비교 대상 run

이후 표에서 비교하는 LLaDA run은 네 가지다. 모두 single-turn 결과에서
가져온 score이며, multi-turn 결과는 이 표에 포함하지 않는다.

| Run | 의미 | Generation | Eval/decoder |
|---|---|---|---|
| v3 baseline | function docs를 바꾸기 전 BFCL v3 checkout 결과 | 새로 생성 | v3 decoder |
| v3 json-prompt | v3에서 function docs만 pretty JSON으로 바꾼 결과 | 새로 생성 | v3 decoder |
| v3 json + v4 decoder | `v3 json-prompt` raw output을 그대로 재사용한 re-score 결과 | 생성 없음 | v4-style Python decoder |
| v4 reference | 기존 DiffuAgent BFCL 트리에서 생성되어 있던 LLaDA 결과 | 기존 결과 사용 | v4-style decoder |

중요한 점은 `v3 json + v4 decoder`는 새 generation 실험이 아니라는 것이다.
`result/llada_st_20260512_050853`의 raw output은 그대로 두고, decoder만
바꿔 score를 다시 계산했다.

## 5. Raw output 형식 비교

먼저 generation 결과 자체가 어떻게 달라졌는지 확인했다. matched 440개
single-turn subset id에서 다음 두 패턴이 raw output에 나타나는지 세었다.

```text
dict-style positional arg: function({"arg": value})
keyword-style arg:        function(arg=value)
```

이 카운트는 배타적 분류가 아니라 패턴 존재 여부다. 따라서 한 출력이 두
패턴을 모두 포함하거나, 어느 쪽에도 명확히 걸리지 않을 수 있고, 합이
440이 될 필요는 없다.

| Run | Dict-style | Keyword-style |
|---|---:|---:|
| v3 baseline | 232/440 | 186/440 |
| v3 json-prompt | 89/440 | 322/440 |
| v4 reference | 65/440 | 334/440 |

```text
v3 baseline vs v3 json-prompt: 405/440 raw outputs changed
```

따라서 function docs 직렬화 차이는 실제 모델 출력에 강하게 작용한다.
이건 단순 formatting 차이가 아니다.

### Python/JavaScript 성공 전환 사례

v3 baseline과 v3 json-prompt의 차이가 가장 크게 보이는 category는 Python
simple과 JavaScript다. score 파일은 summary 뒤에 실패 case만 저장하므로,
`baseline` 실패 목록에는 있는데 `json-prompt` 실패 목록에는 사라진 id를
성공 전환 case로 보았다.

| Category | v3 baseline | v3 json-prompt | 성공 전환 | 회귀 | Net |
|---|---:|---:|---:|---:|---:|
| Python simple | 15/50 (30.00%) | 37/50 (74.00%) | 23 | 1 | +22 |
| JavaScript | 13/50 (26.00%) | 30/50 (60.00%) | 19 | 2 | +17 |

Python simple의 성공 전환은 대부분 baseline에서 dict positional call이 나오고,
v3 decoder/checker가 argument를 비워서 `missing_required`로 실패한 경우다.
pretty JSON prompt에서는 같은 case가 keyword call로 바뀌면서 통과한다.

```text
simple_57 / calculate_cell_density

baseline:
  [calculate_cell_density({'optical_density': 0.6, 'dilution': 5, 'calibration_factor': 1e9})]
  decoded: [{"calculate_cell_density": {}}]
  error: Missing required parameter: 'optical_density'.

json-prompt:
  [calculate_cell_density(optical_density=0.6, dilution=5)]
  result: success
```

```text
simple_79 / create_histogram

baseline:
  [create_histogram({'data': [85, 90, 88, 92, 86, 89, 91], 'bins': 5})]
  decoded: [{"create_histogram": {}}]
  error: Missing required parameter: 'data'.

json-prompt:
  [create_histogram(data=[85, 90, 88, 92, 86, 89, 91], bins=5)]
  result: success
```

JavaScript도 같은 패턴이 많다. baseline에서는 `function({...})` 형태가
argument binding에 실패하고, json-prompt에서는 `function(arg=value)` 형태로
바뀌어 성공한다.

```text
javascript_4 / emailFormatValidator

baseline:
  [emailFormatValidator({'email': 'example@domain.com', 'domain': 'domain.com'})]
  decoded: [{"emailFormatValidator": {}}]
  error: Missing required parameter: 'email'.

json-prompt:
  [emailFormatValidator(email='example@domain.com', domain='domain.com')]
  result: success
```

```text
javascript_30 / setText

baseline:
  [{'name': 'setText', 'parameters': {'newText': 'Hello, World!', 'start': '5', 'length': '7'}}]
  error: Did not output in the specified format.

json-prompt:
  [setText(newText='Hello, World!', start=5, length=7)]
  result: success
```

성공 전환 case의 baseline error type도 이 해석과 맞다.

| Category | Main baseline error among recovered cases |
|---|---|
| Python simple | `missing_required` 19개, `decoder_failed` 3개, `missing_optional` 1개 |
| JavaScript | `missing_required` 15개, `decoder_failed` 2개, `wrong_func_name` 1개, `wrong_output_format` 1개 |

즉 Python/JavaScript의 큰 상승폭은 모델이 문제의 의미를 새로 이해했다기보다,
function doc 직렬화가 출력 surface form을 `function({"arg": value})`에서
`function(arg=value)` 쪽으로 이동시켰고, 그 결과 v3 checker가 argument를
정상 binding할 수 있게 된 영향이 크다.

## 6. Decoder 차이

그런데 `v3 json-prompt`는 raw output 형식이 v4 reference에 가까워졌는데도
score가 충분히 회복되지 않았다. 여기서 decoder 차이가 다음 후보가 됐다.

pretty JSON prompt 이후 LLaDA는 다음처럼 multiline list expression을 더 많이
출력했다.

```python
[
    calculate_area_under_curve(function="lambda: x**2", interval=[1, 3], method="trapezoidal")
]
```

이 형식은 list expression으로 파싱하면 유효한 Python이다.

현재 DiffuAgent/v4-style decoder는 바깥 대괄호를 유지한다.

```python
cleaned_input = input_str.strip().strip("'")
parsed = ast.parse(cleaned_input, mode="eval")
```

반면 v3 checkout decoder는 `ast.parse()` 전에 바깥 대괄호를 제거한다.

```python
cleaned_input = input_str.strip("[]'")
parsed = ast.parse(cleaned_input, mode="eval")
```

single-line이면 v3 방식도 자주 통과한다.

```python
[foo(a=1)]
```

대괄호 제거 후:

```python
foo(a=1)
```

하지만 multiline이면 실패한다.

```python
[
    foo(a=1),
    bar(b=2)
]
```

대괄호 제거 후:

```python
    foo(a=1),
    bar(b=2)
```

결과:

```text
IndentationError: unexpected indent
```

decoder를 바꾸기 전 score 파일에서 확인한 `unexpected_indent` 실패 수:

| Run | unexpected_indent |
|---|---:|
| v3 baseline | 3 |
| v3 json-prompt | 197 |
| v4 reference | 0 |

따라서 v3 json-prompt 결과는 raw output 형식상 v4에 가까워졌지만, v3
decoder가 그 형식을 대량으로 실패시키고 있었다.

## 7. Decoder re-score 검증 결과

계획대로 모델을 다시 돌리지 않고, v3 checkout의 Python AST decoder만
v4-style로 바꾼 뒤 기존 `v3 json-prompt` result를 다시 score했다.

수정:

```python
cleaned_input = input_str.strip("[]'")
```

에서:

```python
cleaned_input = input_str.strip().strip("'")
```

로 변경했다.

re-score 대상:

```text
result/llada_st_20260512_050853
```

새 score directory:

```text
score/llada_st_20260512_050853_v4_decoder
```

failure count 비교:

| Run | Total failed rows in score files | unexpected_indent | invalid/decode | missing_required |
|---|---:|---:|---:|---:|
| v3 baseline | 324 | 3 | 86 | 173 |
| v3 json-prompt | 279 | 197 | 223 | 20 |
| v3 json + v4 decoder | 213 | 0 | 64 | 67 |
| v4 reference | 201 | 0 | 56 | 47 |

결과:

```text
unexpected_indent가 197 -> 0으로 사라졌다.
overall accuracy가 10.82 -> 17.23으로 상승했다.
non-live aggregate가 36.50 -> 58.00으로 상승했다.
parallel은 2.00 -> 40.00으로 회복했다.
multiple_parallel은 8.00 -> 46.00으로 회복했다.
```

해석:

```text
decoder mismatch 가설은 강하게 확인됐다.
v3 json-prompt 결과가 낮았던 큰 이유는 모델 output이 나빠서라기보다,
v3 decoder가 v4-style multiline list output을 unexpected indent로 실패시켰기 때문이다.
```

## 8. 최종 점수 비교

아래 점수표는 모두 single-turn score에서 가져왔다. aggregate 표에서는 category
단순평균을 앞에 쓰고, 기존에 보던 BFCL `AST Summary`를 괄호에 함께 적는다.
예를 들어 `33.67% (33.83%)`는 단순평균 33.67%, BFCL AST Summary 33.83%라는
뜻이다. BFCL CSV의 `Overall Acc`, `Non_Live Overall Acc`, `Live Overall Acc`는
subset run에서 평가하지 않은 category를 0점처럼 포함할 수 있으므로,
prompt/decoder 비교의 핵심 수치로 사용하지 않는다.

계산 규칙:

```text
non-live simple avg = six non-live category percentage의 산술 평균

non-live AST Summary = ((python_simple + java + javascript) / 3
                        + multiple + parallel + multiple_parallel) / 4

live simple avg = four live category percentage의 산술 평균

live AST Summary = executed live AST entries의 sample-weighted average
                 = (correct_simple + correct_multiple + correct_parallel
                    + correct_multiple_parallel) / (50 + 50 + 16 + 24)
```

예를 들어 `v3 json + v4 decoder` live AST는
`(27 + 14 + 7 + 7) / 140 = 39.29%`이고, 네 live category percentage의
단순 평균 `(54.00 + 28.00 + 43.75 + 29.17) / 4 = 38.73%`와 다르다.

### 기존 결과

기존 분석에서 사용한 score directory:

```text
LLaDA v3 baseline:
  /home/ilju/research/bfcl_v3_ea13468/berkeley-function-call-leaderboard/score/llada_st_20260512_041601

LLaDA v3+json:
  /home/ilju/research/bfcl_v3_ea13468/berkeley-function-call-leaderboard/score/llada_st_20260512_050853

LLaDA v3+json+v4decoder:
  /home/ilju/research/bfcl_v3_ea13468/berkeley-function-call-leaderboard/score/llada_st_20260512_050853_v4_decoder

LLaDA v4 reference:
  /home/ilju/research/DiffuAgent/unified_envs/gorilla/berkeley-function-call-leaderboard/score/llada_st_20260511_095626

Qwen3 v3:
  /home/ilju/research/bfcl_v3_ea13468/berkeley-function-call-leaderboard/score/qwen3_st_20260512_043633

Qwen3 v4 reference:
  /home/ilju/research/DiffuAgent/unified_envs/gorilla/berkeley-function-call-leaderboard/score/qwen3_st_20260511_092203
```

주의: 기존 LLaDA v4 reference는 이후 정리한 LLaDA decoding 설정과 다르다.
로그 기준으로 이 run은 `LLADA_BLOCK_LENGTH=128`, `LLADA_THRESHOLD=null`
였고, 실제 generation 로그도 `block_length=128`, `threshold=None`으로
찍혀 있다. 이후 재실험 job은 `LLADA_BLOCK_LENGTH=32`,
`LLADA_THRESHOLD=0.9`를 사용했다. 따라서 기존 v4 reference는 경향성 확인에는
유용하지만, 현재 표준화한 재실험 설정과의 엄밀한 apples-to-apples 비교로는
보지 않는다.

#### Existing Aggregate

| Model group | Run | Non-live simple avg (AST Summary) | Live simple avg (AST Summary) | BFCL reported overall |
|---|---|---:|---:|---:|
| LLaDA | v3_baseline | 33.67% (33.83%) | 14.67% (17.86%) | 9.82% |
| LLaDA | v3+json | 45.67% (36.50%) | 20.23% (24.29%) | 10.82% |
| LLaDA | v3+json+v4decoder | 60.67% (58.00%) | 38.73% (39.29%) | 17.23% |
| LLaDA | v4_reference | 62.67% (57.00%) | 42.77% (43.57%) | 10.06% |
| Qwen3 | v3_qwen | 84.00% (86.67%) | 75.96% (77.14%) | 26.57% |
| Qwen3 | v4_qwen | 84.00% (86.67%) | 75.42% (77.14%) | 16.38% |

#### Existing LLaDA Detail

| Run | Py simple | Java | JS | Multiple | Parallel | Multiple parallel | Non-live simple avg (AST) |
|---|---:|---:|---:|---:|---:|---:|---:|
| v3_baseline | 30.00% | 44.00% | 26.00% | 68.00% | 8.00% | 26.00% | 33.67% (33.83%) |
| v3+json | 74.00% | 58.00% | 60.00% | 72.00% | 2.00% | 8.00% | 45.67% (36.50%) |
| v3+json+v4decoder | 80.00% | 58.00% | 60.00% | 80.00% | 40.00% | 46.00% | 60.67% (58.00%) |
| v4_reference | 92.00% | 62.00% | 68.00% | 86.00% | 32.00% | 36.00% | 62.67% (57.00%) |

| Run | Live simple | Live multiple | Live parallel | Live multiple parallel | Live simple avg (AST) |
|---|---:|---:|---:|---:|---:|
| v3_baseline | 10.00% | 32.00% | 0.00% | 16.67% | 14.67% (17.86%) |
| v3+json | 40.00% | 18.00% | 6.25% | 16.67% | 20.23% (24.29%) |
| v3+json+v4decoder | 54.00% | 28.00% | 43.75% | 29.17% | 38.73% (39.29%) |
| v4_reference | 56.00% | 38.00% | 56.25% | 20.83% | 42.77% (43.57%) |

#### Existing Qwen3 Detail

| Run | Py simple | Java | JS | Multiple | Parallel | Multiple parallel | Non-live simple avg (AST) |
|---|---:|---:|---:|---:|---:|---:|---:|
| v3_qwen | 94.00% | 66.00% | 76.00% | 94.00% | 88.00% | 86.00% | 84.00% (86.67%) |
| v4_qwen | 94.00% | 66.00% | 76.00% | 92.00% | 90.00% | 86.00% | 84.00% (86.67%) |

| Run | Live simple | Live multiple | Live parallel | Live multiple parallel | Live simple avg (AST) |
|---|---:|---:|---:|---:|---:|
| v3_qwen | 78.00% | 80.00% | 75.00% | 70.83% | 75.96% (77.14%) |
| v4_qwen | 80.00% | 80.00% | 75.00% | 66.67% | 75.42% (77.14%) |

### 재실험 결과

재현용 job을 정리한 뒤 다시 실행한 score directory:

```text
LLaDA v3 baseline:
  /home/ilju/research/bfcl_v3_ea13468/berkeley-function-call-leaderboard/score/llada_v3_baseline_st_20260512_085513

LLaDA v3+json:
  /home/ilju/research/bfcl_v3_ea13468/berkeley-function-call-leaderboard/score/llada_v3_json_st_20260512_085618

LLaDA v3+json+v4decoder:
  /home/ilju/research/bfcl_v3_ea13468/berkeley-function-call-leaderboard/score/llada_v3_json_st_20260512_085618_v4_decoder

LLaDA v4:
  /home/ilju/research/DiffuAgent/unified_envs/gorilla/berkeley-function-call-leaderboard/score/llada_v4_st_20260512_105544

Qwen3 v3:
  /home/ilju/research/bfcl_v3_ea13468/berkeley-function-call-leaderboard/score/qwen3_v3_baseline_st_20260512_103414

Qwen3 v4:
  /home/ilju/research/DiffuAgent/unified_envs/gorilla/berkeley-function-call-leaderboard/score/qwen3_v4_st_20260512_104532
```

#### Reproduction Aggregate

| Model group | Run | Non-live simple avg (AST Summary) | Live simple avg (AST Summary) | BFCL reported overall |
|---|---|---:|---:|---:|
| LLaDA | v3_baseline | 33.67% (33.83%) | 14.67% (17.86%) | 9.82% |
| LLaDA | v3+json | 45.67% (36.50%) | 20.23% (24.29%) | 10.82% |
| LLaDA | v3+json+v4decoder | 60.67% (58.00%) | 38.73% (39.29%) | 17.23% |
| LLaDA | v4_llada | 57.67% (55.50%) | 42.86% (42.14%) | 9.76% |
| Qwen3 | v3_qwen | 84.00% (86.67%) | 75.96% (77.14%) | 26.57% |
| Qwen3 | v4_qwen | 84.33% (87.17%) | 76.46% (77.86%) | 16.50% |

#### Reproduction LLaDA Detail

| Run | Py simple | Java | JS | Multiple | Parallel | Multiple parallel | Non-live simple avg (AST) |
|---|---:|---:|---:|---:|---:|---:|---:|
| v3_baseline | 30.00% | 44.00% | 26.00% | 68.00% | 8.00% | 26.00% | 33.67% (33.83%) |
| v3+json | 74.00% | 58.00% | 60.00% | 72.00% | 2.00% | 8.00% | 45.67% (36.50%) |
| v3+json+v4decoder | 80.00% | 58.00% | 60.00% | 80.00% | 40.00% | 46.00% | 60.67% (58.00%) |
| v4_llada | 78.00% | 52.00% | 56.00% | 84.00% | 32.00% | 44.00% | 57.67% (55.50%) |

| Run | Live simple | Live multiple | Live parallel | Live multiple parallel | Live simple avg (AST) |
|---|---:|---:|---:|---:|---:|
| v3_baseline | 10.00% | 32.00% | 0.00% | 16.67% | 14.67% (17.86%) |
| v3+json | 40.00% | 18.00% | 6.25% | 16.67% | 20.23% (24.29%) |
| v3+json+v4decoder | 54.00% | 28.00% | 43.75% | 29.17% | 38.73% (39.29%) |
| v4_llada | 56.00% | 30.00% | 56.25% | 29.17% | 42.86% (42.14%) |

#### Reproduction Qwen3 Detail

| Run | Py simple | Java | JS | Multiple | Parallel | Multiple parallel | Non-live simple avg (AST) |
|---|---:|---:|---:|---:|---:|---:|---:|
| v3_qwen | 94.00% | 66.00% | 76.00% | 94.00% | 88.00% | 86.00% | 84.00% (86.67%) |
| v4_qwen | 94.00% | 66.00% | 76.00% | 92.00% | 90.00% | 88.00% | 84.33% (87.17%) |

| Run | Live simple | Live multiple | Live parallel | Live multiple parallel | Live simple avg (AST) |
|---|---:|---:|---:|---:|---:|
| v3_qwen | 78.00% | 80.00% | 75.00% | 70.83% | 75.96% (77.14%) |
| v4_qwen | 80.00% | 80.00% | 75.00% | 70.83% | 76.46% (77.86%) |

### 재실험 판정

재실험은 기존 분석의 큰 경향을 재현한다.

```text
LLaDA:
  v3 baseline -> v3+json -> v3+json+v4decoder로 갈수록 AST score가 오른다.
  v3+json+v4decoder는 v4 LLaDA에 매우 가까운 수준까지 회복된다.

Qwen3:
  v3/v4 차이가 매우 작다.
  따라서 LLaDA의 큰 차이는 모델 공통 현상이라기보다
  LLaDA가 prompt serialization과 decoder mismatch에 민감한 현상으로 보는 편이 맞다.
```

기존 v4 LLaDA reference와 재실험 v4 LLaDA는 category-level 값이 완전히 같지는
않다. 이 차이는 랜덤성보다는 LLaDA decoding 환경변수 차이로 설명하는 것이
가장 자연스럽다. 기존 v4 reference는 `LLADA_BLOCK_LENGTH=128`,
`LLADA_THRESHOLD=null`였고, 재실험 v4는 `LLADA_BLOCK_LENGTH=32`,
`LLADA_THRESHOLD=0.9`였다. 엄밀한 비교는 재실험 v4를 우선해야 하지만,
aggregate 기준의 큰 결론은 두 v4 run 모두에서 유지된다.

```text
기존:   v3+json+v4decoder 58.00 / 39.29, v4 reference 57.00 / 43.57
재실험: v3+json+v4decoder 58.00 / 39.29, v4_llada    55.50 / 42.14
```

즉 non-live에서는 `v3+json+v4decoder`가 v4와 같거나 조금 높고, live에서는
v4가 몇 point 높다. Qwen3는 기존과 재실험 모두 v3/v4 aggregate 차이가
1 point 안팎이다.

## 9. 현재 해석

현재까지 가장 설득력 있는 설명은 다음이다.

```text
1. v3 prompt의 Python repr-style function docs가 LLaDA를 dict-style call로 유도한다.
2. function docs를 v4처럼 pretty JSON으로 바꾸면 LLaDA output이 v4-style keyword call에 가까워진다.
3. 그런데 이때 multiline list output도 늘어난다.
4. v3 decoder는 []를 제거해서 multiline list output을 unexpected indent로 실패시킨다.
5. v4-style decoder는 []를 유지하므로 같은 출력을 정상 파싱할 수 있다.
```

즉, LLaDA v3 결과가 낮았던 이유는 단일 원인이 아니라 다음 두 단계가
겹친 결과로 보는 것이 맞다.

```text
프롬프트 직렬화 차이가 모델 출력 형식을 바꾸고,
그 바뀐 출력 형식 중 multiline list를 v3 decoder가 잘못 처리한다.
```

재실험 결과는 이 해석을 다시 확인했다. v3 LLaDA baseline과 v3+json은
기존 run과 재실험 run의 `model_result_raw` / `model_result_decoded`가
440개 모두 동일했고, score도 동일했다. 따라서 v3 쪽 차이는 run-to-run
랜덤성으로 설명하기 어렵다.

반면 기존 LLaDA v4 reference와 재실험 v4 LLaDA는 서로 완전히 같은 비교군이
아니다. 기존 v4 reference는 로그상 `LLADA_BLOCK_LENGTH=128`,
`LLADA_THRESHOLD=null`였고, 재실험 v4는 `LLADA_BLOCK_LENGTH=32`,
`LLADA_THRESHOLD=0.9`였다. LLaDA diffusion decoding에서는 이 값들이 생성
trajectory를 바꾸므로, v4 reference와 재실험 v4의 category-level 차이는
랜덤성보다 decoding setting 차이로 설명하는 것이 더 자연스럽다.

따라서 현재 결론은 다음처럼 정리한다.

```text
1. v3 LLaDA 실험은 결정론적으로 재현됐다.
2. v3+json+v4decoder는 v4 LLaDA 수준에 상당히 근접한다.
3. 기존 v4 reference는 decoding env가 달랐으므로 엄밀 비교의 기준으로 삼지 않는다.
4. apples-to-apples 비교는 표준화한 재실험 v4 LLaDA를 우선한다.
5. 그래도 기존 v4 reference와 재실험 v4 모두에서 큰 경향성은 유지된다.
```

### v3+json+v4decoder와 v4가 여전히 다른 이유

`v3+json+v4decoder`는 v4 실험과 완전히 같은 generation이 아니다. 더 정확히는
v3 checkout에서 생성한 raw output을 v4-style decoder로 다시 채점한 것이다.
따라서 decoder mismatch는 제거했지만, 다음 차이는 남아 있다.

```text
1. prompt 전체가 v4와 완전히 같지는 않다.
   - v3+json은 function docs 직렬화만 v4에 가깝게 바꾼 것이다.
   - system prompt wording, category naming, handler formatting의 세부 차이는 남을 수 있다.

2. v3/v4 데이터와 ground truth가 완전히 동일하다고 단정할 수 없다.
   - whitelist id는 맞췄지만, 같은 id의 prompt/function schema/answer가
     v3와 v4에서 부분적으로 다를 수 있다.
   - 앞서 live category 일부에서 prompt wording과 schema 차이가 확인됐다.

3. handler 경로가 다르다.
   - v3에는 DiffuAgent/LLaDA backbone handler를 이식해서 사용했다.
   - v4는 DiffuAgent tree의 native handler 경로를 사용한다.
   - 같은 decoding env라도 prompt assembly, cleanup, truncation, logging 주변 코드가 다를 수 있다.

4. decoder가 해결하는 것은 parsing 실패이지 모델 출력 자체의 semantic error가 아니다.
   - v4 decoder로 unexpected_indent는 사라지지만,
     missing_required, type/value mismatch, wrong function call은 여전히 남는다.
```

그래서 `v3+json+v4decoder`가 v4에 근접하는 것은 decoder/prompt serialization
가설을 지지하지만, 두 결과가 완전히 같아야 한다는 뜻은 아니다.

### 논문 보고 수치와 재현 수치 차이

논문 표에서는 LLaDA-8B가 BFCL single-turn에서 상당히 낮게 보고된다.
예를 들어 표의 live 평균은 `S=8.0, M=26.0, P=0.0, PM=12.5`의 단순 평균인
`11.6`이다. 우리 v3 baseline은 같은 live category에서
`10.00, 32.00, 0.00, 16.67`이고, 단순 평균은 `14.67`, sample-weighted
AST Summary는 `17.86`이다. 즉 baseline만 놓고 보면 논문보다 높지만,
방향성은 비슷하다.

차이가 날 수 있는 이유는 다음과 같다.

```text
1. metric aggregation이 다를 수 있다.
   - 이 문서는 category 단순평균과 BFCL CSV의 AST Summary를 병기한다.
   - 논문 표의 live 평균은 category percentage의 단순평균으로 보인다.
   - non-live도 논문이 어떤 category/aggregation을 썼는지에 따라
     BFCL AST Summary와 직접 일치하지 않을 수 있다.

2. LLaDA decoding env가 결과에 크게 영향을 준다.
   - 기존 v4 reference만 보아도 block_length/threshold 차이로 category 값이 달라졌다.
   - 논문 실행의 exact LLADA_BLOCK_LENGTH, threshold, Fast-dLLM 설정이 다르면
     같은 whitelist라도 결과가 달라질 수 있다.

3. paper pipeline과 현재 재현 pipeline이 완전히 같지 않을 수 있다.
   - 현재 v3는 backbone handler, partial/subset eval, env-based prompt/decoder 분기를
     명시적으로 정리한 재현용 checkout이다.
   - 논문 실행 코드의 prompt assembly, output cleanup, truncation, parser 버전,
     Fast-dLLM commit이 다르면 LLaDA처럼 민감한 모델에서는 차이가 커질 수 있다.

4. whitelist가 같아도 task payload가 완전히 같다는 뜻은 아니다.
   - v3/v4 사이에 같은 id라도 function doc, prompt wording, possible answer가
     일부 다를 수 있다.

5. Qwen3는 v3/v4 및 논문 표와 비교적 가까운 편이다.
   - 따라서 whitelist 자체가 완전히 틀렸다는 설명보다는,
     LLaDA가 prompt serialization, decoder, diffusion decoding setting에
     훨씬 민감하다는 설명이 더 설득력 있다.
```

따라서 현재 결과는 “논문 수치를 그대로 복제했다”기보다는, 논문에서 관찰된
LLaDA의 취약성이 prompt/decoder/decoding 설정에 의해 크게 증폭 또는 완화될
수 있음을 보여준다.

## 10. 다음 검증 계획

decoder 변수는 상당 부분 확인됐다. 다음 검증은 이제 두 갈래로 나눈다.

우선순위:

```text
1. 기존 v4 reference와 같은 decoding env로 v4 LLaDA를 다시 실행한다.
   - LLADA_BLOCK_LENGTH=128
   - LLADA_THRESHOLD=null
   - 목적: 기존 v4 reference가 같은 설정에서 재현되는지 확인한다.

2. 표준화한 재실험 설정에서 v3+json+v4decoder와 v4 LLaDA를 id별로 비교한다.
   - v3+json+v4decoder: 58.00 / 39.29
   - 재실험 v4 LLaDA: 55.50 / 42.14
   - 목적: 남은 category-level 차이가 어떤 id에서 발생하는지 확인한다.

3. v3+json+v4decoder의 실패 유형을 샘플링한다.
   - decoder_failed / syntax 계열
   - missing_required 계열
   - type/value mismatch 계열
   - 목적: decoder로 해결된 부분과 모델 출력 자체의 남은 오류를 분리한다.

4. Qwen3는 보조 sanity check로 유지한다.
   - 기존/재실험 모두 v3/v4 차이가 작다.
   - 목적: LLaDA 특이적인 민감도라는 해석을 계속 검증한다.
```

비교할 score:

```text
기존 LLaDA v3 baseline:
  /home/ilju/research/bfcl_v3_ea13468/berkeley-function-call-leaderboard/score/llada_st_20260512_041601

재실험 LLaDA v3 baseline:
  /home/ilju/research/bfcl_v3_ea13468/berkeley-function-call-leaderboard/score/llada_v3_baseline_st_20260512_085513

기존 LLaDA v3 json-prompt:
  /home/ilju/research/bfcl_v3_ea13468/berkeley-function-call-leaderboard/score/llada_st_20260512_050853

재실험 LLaDA v3 json-prompt:
  /home/ilju/research/bfcl_v3_ea13468/berkeley-function-call-leaderboard/score/llada_v3_json_st_20260512_085618

재실험 LLaDA v3 json-prompt + v4-style decoder:
  /home/ilju/research/bfcl_v3_ea13468/berkeley-function-call-leaderboard/score/llada_v3_json_st_20260512_085618_v4_decoder

기존 LLaDA v4 reference, decoding env caveat 있음:
  /home/ilju/research/DiffuAgent/unified_envs/gorilla/berkeley-function-call-leaderboard/score/llada_st_20260511_095626

재실험 LLaDA v4, 표준화한 비교 우선 대상:
  /home/ilju/research/DiffuAgent/unified_envs/gorilla/berkeley-function-call-leaderboard/score/llada_v4_st_20260512_105544

재실험 Qwen3 v3:
  /home/ilju/research/bfcl_v3_ea13468/berkeley-function-call-leaderboard/score/qwen3_v3_baseline_st_20260512_103414

재실험 Qwen3 v4:
  /home/ilju/research/DiffuAgent/unified_envs/gorilla/berkeley-function-call-leaderboard/score/qwen3_v4_st_20260512_104532
```

기록할 항목:

```text
overall accuracy
non-live average
live average
category-level scores
unexpected_indent failure count
decode/syntax failure count
missing-required-parameter failure count
id별 raw output diff
id별 valid/invalid 전환
LLaDA decoding env
```

## 11. 판정 기준

### decoder 가설 확인

다음이 동시에 보이면 decoder mismatch가 큰 원인이다.

```text
unexpected_indent 실패가 대부분 사라진다.
parallel / multiple_parallel 점수가 회복된다.
LLaDA generation 없이 re-score만으로 점수가 오른다.
```

### 부분 확인

`unexpected_indent`는 사라지지만 점수 상승이 작다면, decoder는 원인 중
하나지만 충분조건은 아니다. 남는 후보:

```text
1. matched id라도 v3/v4 실제 task 내용 또는 ground truth가 다름
2. function docs JSON 여부 외의 프롬프트 문구 차이
3. handler query/cleanup 경로 차이
4. prompt 길이/layout 차이에 따른 실제 모델 출력 차이
```

### 기각

bracket을 유지해도 `unexpected_indent`가 계속 많다면 bracket stripping이
주원인이 아니다. 그 경우 다음을 확인한다.

```text
1. raw output이 유효한 list expression 밖에 indentation을 포함하는지
2. raw output이 truncation 되었는지
3. Python 외 Java/JavaScript parser에서 별도 문제가 있는지
```

## 12. 재현성과 job 분기

현재 코드는 별도의 rollback 파일을 두는 구조가 아니다. v3 checkout의
`bfcl_eval/model_handler/utils.py`에 두 환경변수 분기가 들어가 있고, 각 job
wrapper가 어떤 분기를 사용할지 명시한다.

```text
BFCL_FUNCTION_DOC_SERIALIZATION=legacy | json
BFCL_AST_DECODER=legacy | v4
```

기본 runner인 `jobs/run_bfcl_llada.job`와 `jobs/run_bfcl_qwen3.job`는 기본값으로
v3 baseline에 해당하는 `legacy/legacy`를 사용한다. 실험별 wrapper는 다음처럼
분기를 고정한다.

```text
run_exp_v3_llada_baseline_singleturn.job:
  BFCL_FUNCTION_DOC_SERIALIZATION=legacy
  BFCL_AST_DECODER=legacy

run_exp_v3_llada_json_singleturn.job:
  BFCL_FUNCTION_DOC_SERIALIZATION=json
  BFCL_AST_DECODER=legacy

run_exp_v3_llada_json_v4_decoder_eval.job:
  BFCL_FUNCTION_DOC_SERIALIZATION=json
  BFCL_AST_DECODER=v4
  RUN_GENERATE=0
  RUN_EVAL=1

run_exp_v3_qwen3_baseline_singleturn.job:
  BFCL_FUNCTION_DOC_SERIALIZATION=legacy
  BFCL_AST_DECODER=legacy
```

따라서 “rollback”은 소스 파일을 되돌리는 작업이 아니라, baseline wrapper를
실행하거나 환경변수를 `legacy/legacy`로 두는 것을 의미한다. 결과 디렉터리와
score 디렉터리는 덮어쓰지 않는다. 현재 분석은 각 중간 결과를 서로 비교하는
방식이므로, run별 산출물을 보존해야 한다.
