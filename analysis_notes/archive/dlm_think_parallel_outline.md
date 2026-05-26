# DLM이 think/action rationale을 잘 생성하는가? — BFCL 기반 실험 설계 문서

## 1. 실험의 목적

현재 LLaDA-8B-Instruct는 BFCL/tau2에서 strict tool-call format, JSON schema 준수, policy following, long workflow 수행에서 문제가 관찰되었다. 따라서 바로 “DLM이 agent를 잘하는가?”를 묻기보다, 더 작은 질문으로 분해해야 한다.

핵심 질문은 다음이다.

> DLM은 strict tool call은 못 하더라도, tool call 직전에 필요한 think/action rationale은 제대로 생성할 수 있는가?

즉, DLM에게 실제 tool call을 생성시키기 전에, 다음 능력을 분리해서 확인한다.

- user request에서 필요한 정보를 파악하는가?
- 적절한 tool을 고를 수 있는가?
- 필요한 argument entity를 찾을 수 있는가?
- action intention을 자연어 또는 pseudo-call 형태로 표현할 수 있는가?
- 여러 tool call이 필요한 경우 step을 나누어 설명할 수 있는가?
- 병렬 가능한 action과 순차 의존 action을 혼동하지 않는가?

이 실험은 이후 masking intervention / denoising dynamics 분석으로 넘어가기 전의 sanity check 역할을 한다.

---

## 2. 왜 이 실험을 먼저 해야 하나?

DLM의 denoising dynamics와 subtask dependency의 관계를 보려면, 먼저 DLM이 생성하는 think/action span 자체가 의미 있어야 한다. 만약 DLM이 single-call 상황에서도 잘못된 tool을 고르거나, argument를 추출하지 못하거나, 불필요한 step을 생성한다면, 이후 denoising dynamics 분석에서 성능 하락의 원인을 분리하기 어렵다.

예를 들어 masking intervention에서 downstream think 품질이 나빠졌다고 하더라도, 그 이유가 다음 중 무엇인지 구분해야 한다.

1. DLM이 애초에 think/action plan을 만들 능력이 부족해서인가?
2. prerequisite span이 mask되어 dependency가 깨졌기 때문인가?
3. tool format 또는 JSON 출력 실패 때문인가?
4. task 자체가 너무 어려워서인가?

따라서 먼저 tool call execution을 제거하고, planning-only / think-only 버전의 BFCL을 만들어 DLM의 기본 reasoning 능력을 확인한다.

---

## 3. BFCL에서의 실험 변형: Planning-only BFCL

BFCL 원래 setting은 user query와 tool schema가 주어졌을 때, 모델이 실제 function call을 생성하는 것이다. 하지만 여기서는 strict function call을 요구하지 않는다.

대신 다음과 같은 planning-only task로 변형한다.

### 입력

```text
User request:
{bfcl_user_query}

Available tools:
{tool_schemas}
```

### 출력

```text
[T1] one short thought
[A1] one intended action in natural language or pseudo-call
[T2] one short thought
[A2] one intended action
...
```

이때 `[A]`는 strict JSON이 아니라 자연어 action intention 또는 pseudo-call이면 된다.

예:

```text
[T1] The user asks for the current weather in Seoul.
[A1] Use get_weather with city = Seoul.
```

또는:

```text
[A1] get_weather(city="Seoul")
```

---

## 4. 기본 프롬프트

초기 실험에서는 다음 프롬프트를 사용한다.

```text
You are given a user request and a list of available tools.

Your task is not to call the tools.
Your task is to write a structured reasoning plan for tool use.

Rules:
- Use the exact labels [T1], [A1], [T2], [A2], ...
- Each [T] must be one short sentence explaining what needs to be known or decided.
- Each [A] must be one short sentence describing the intended tool/action.
- Do not output JSON.
- Do not include any extra text before or after the labeled steps.
- Stop when the user request can be solved.

User request:
{user_request}

Available tools:
{tool_schemas}

Output:
```

---

## 5. 예시

### 예시 입력

```text
User request:
Compare the current weather in Seoul and Tokyo.

Available tools:
- get_weather(city: string): returns current weather for a city
- search_web(query: string): searches the web
- calculate(expression: string): evaluates an expression
```

### 기대 출력

```text
[T1] I need the current weather in Seoul.
[A1] Use get_weather with city = Seoul.
[T2] I need the current weather in Tokyo.
[A2] Use get_weather with city = Tokyo.
[T3] I need to compare the two weather results.
[A3] Compare the Seoul and Tokyo weather values.
```

여기서 중요한 점은 `[A1]`, `[A2]`가 실제 JSON tool call이 아니라는 것이다. 이 단계의 목적은 strict schema generation이 아니라 tool-use reasoning을 확인하는 것이다.

---

## 6. DAG를 입력으로 줄 것인가?

초기 실험에서는 DAG를 주지 않는 것이 좋다.

### Setting A. No-DAG Planning

입력:

```text
user request + tool schemas
```

출력:

```text
[T][A] plan
```

목적:

> LLaDA가 스스로 user request와 tool schema만 보고 tool-use think/action plan을 만들 수 있는지 확인한다.

이 setting이 메인 sanity check다.

### Setting B. DAG-aware Verbalization

입력:

```text
user request + tool schemas + gold DAG
```

출력:

```text
[T][A] plan
```

목적:

> LLaDA가 주어진 DAG를 자연어 think/action sequence로 잘 verbalize할 수 있는지 확인한다.

이 setting은 후속 masking intervention에서 gold span sequence를 만들거나 upper-bound를 확인하는 데 사용한다.

### 권장 순서

```text
1. No-DAG Planning
2. DAG-aware Verbalization
3. Gold [T][A] sequence 기반 masking intervention
4. DLM-generated [T][A] sequence 기반 masking intervention
```

---

## 7. BFCL subset 추천 순서

처음부터 전체 BFCL을 돌리기보다 category별 난이도를 낮은 것부터 본다.

추천 순서:

```text
1. simple
2. multiple
3. parallel
4. parallel_multiple
5. multi-turn
```

각 단계에서 확인할 질문은 다르다.

| BFCL subset | 확인할 질문 |
|---|---|
| simple | 단일 tool call의 think/action rationale을 만들 수 있는가? |
| multiple | 여러 tool call을 빠뜨리지 않고 나열할 수 있는가? |
| parallel | 독립적인 tool call들을 분리된 action으로 표현할 수 있는가? |
| parallel_multiple | 병렬 가능한 action과 후속 aggregation action을 구분할 수 있는가? |
| multi-turn | state/history를 반영한 plan을 만들 수 있는가? |

---

## 8. 평가 기준

평가는 rule-based 평가와 LLM-as-judge를 혼합한다.

### 8.1 Rule-based 평가

BFCL에는 gold function call이 있으므로 `[A]` span에 대해서는 상당 부분 자동 평가가 가능하다.

평가 항목:

- format adherence: `[T1]`, `[A1]` 형식을 지켰는가?
- tool selection recall: 필요한 gold tool을 모두 언급했는가?
- tool selection precision: 불필요한 tool을 추가하지 않았는가?
- argument extraction accuracy: 필요한 argument value를 올바르게 포함했는가?
- missing action rate: 필요한 action을 빠뜨렸는가?
- hallucinated action rate: 존재하지 않는 tool/action을 만들었는가?
- natural language/action consistency: `[T]`와 `[A]`가 서로 일관적인가?

예:

Gold call:

```text
get_weather(city="Seoul")
```

Model action:

```text
[A1] Use get_weather with city = Seoul.
```

자동 평가:

```text
tool name match: yes
argument match: yes
```

---

### 8.2 LLM-as-judge 평가

LLM-as-judge는 rule-based로 평가하기 어려운 항목에 사용한다.

주로 평가할 것:

- rationale이 user request와 맞는가?
- action intention이 올바른가?
- step이 너무 많거나 불필요하지 않은가?
- dependency/order가 타당한가?
- parallel 가능한 action을 불필요하게 순차 의존처럼 쓰지 않았는가?
- dependent action을 prerequisite 없이 먼저 실행하려 하지 않았는가?

Judge prompt 예시:

```text
You are evaluating a model-generated tool-use plan.

Given:
1. User request
2. Available tools
3. Gold function calls
4. Model-generated [T][A] plan

Evaluate the plan using the following criteria:
- Does each action correspond to a necessary gold tool call?
- Are the required arguments correctly inferred?
- Are there unnecessary or hallucinated actions?
- Is the reasoning consistent with the actions?
- Is the dependency/order valid?

Return JSON only:
{
  "format_valid": true/false,
  "tool_selection_correct": true/false,
  "argument_correct": true/false,
  "no_hallucinated_action": true/false,
  "dependency_order_valid": true/false,
  "overall_plan_correct": true/false,
  "brief_reason": "..."
}
```

LLM-as-judge만 사용하면 불안정할 수 있으므로, tool name / argument / format은 rule-based로 먼저 평가하고, rationale과 dependency-order validity만 judge에 맡기는 것이 좋다.

---

## 9. 실험 결과를 어떻게 해석할 것인가?

### 좋은 결과

다음 결과가 나오면 DLM이 think/action planner로는 가능성이 있다고 볼 수 있다.

```text
format adherence 높음
tool selection recall 높음
argument extraction accuracy 높음
hallucinated action rate 낮음
rationale-action consistency 높음
parallel subset에서 independent action을 잘 분리함
```

이 경우 후속 실험으로 넘어갈 수 있다.

```text
DLM-generated [T][A] span의 denoising dynamics 분석
masking intervention
readiness / dependency signal 추정
AR executor batching
```

### 나쁜 결과

다음 결과가 나오면 DLM-generated think를 바로 쓰기 어렵다.

```text
format adherence 낮음
잘못된 tool 선택 많음
argument 누락 많음
hallucinated action 많음
parallel action을 잘못 순차화함
dependent action을 너무 일찍 제안함
```

이 경우 후속 masking intervention은 gold `[T][A]` sequence로 먼저 수행해야 한다.

---

## 10. masking intervention과의 연결

이 실험은 최종 목표가 아니라 후속 실험의 선행 조건이다.

전체 흐름:

```text
Step 1. BFCL planning-only setting에서 DLM이 [T][A] think/action을 잘 생성하는지 확인
Step 2. DLM이 명시적으로 dependency / parallelization label을 맞히는지 확인
Step 3. gold [T][A] sequence로 masking intervention 수행
Step 4. DLM-generated [T][A] sequence로 masking intervention 확장
Step 5. denoising dynamics를 readiness / dependency signal로 사용해 AR batching
```

여기서 Step 1의 목적은 다음을 확인하는 것이다.

> DLM이 strict tool call은 못 하더라도, tool-use reasoning span을 생성할 수 있는가?

이 질문에 어느 정도 긍정적인 답이 나와야, DLM-generated think/action span을 대상으로 denoising dynamics를 분석할 수 있다.

---

## 11. 최소 실행 계획

처음에는 다음 정도로 작게 시작한다.

### Dataset

```text
BFCL simple 50개
BFCL multiple 50개
BFCL parallel 50개
```

### Model output

```text
[T1] ...
[A1] ...
[T2] ...
[A2] ...
```

### Evaluation

```text
1. format adherence
2. tool selection precision / recall
3. argument match
4. hallucinated action rate
5. missing action rate
6. dependency/order validity by LLM-as-judge
```

### 분석표 예시

| Subset | Format | Tool Recall | Tool Precision | Arg Match | Hallucination | Overall Plan |
|---|---:|---:|---:|---:|---:|---:|
| simple | - | - | - | - | - | - |
| multiple | - | - | - | - | - | - |
| parallel | - | - | - | - | - | - |

---

## 12. 최종 요약

이 실험은 “DLM이 agent를 잘하는가?”를 묻는 것이 아니라, 더 작은 질문을 묻는다.

> DLM은 tool call을 실제로 실행하기 전, 어떤 tool을 왜 써야 하는지에 대한 think/action rationale을 잘 만들 수 있는가?

BFCL에서 이를 확인하기 위해, 원래의 strict function-calling task를 planning-only task로 변형한다. LLaDA에게 JSON tool call 대신 `[T1][A1][T2][A2]...` 형식의 structured plan을 생성하게 하고, gold function call과 비교해 tool selection, argument extraction, hallucination, dependency/order validity를 평가한다.

이 결과가 좋으면 DLM-generated think/action span을 사용해 denoising dynamics와 subtask dependency의 관계를 분석할 수 있다. 결과가 나쁘면, 먼저 gold `[T][A]` sequence로 masking intervention을 수행해야 한다.
