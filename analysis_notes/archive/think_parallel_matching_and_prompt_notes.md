# Think Parallel 프롬프트 및 매칭 분석 노트

날짜: 2026-05-15

대상 run:

```text
/home/ilju/research/DiffuAgent/think_parallel_v0/outputs/llada_think_parallel_20260514_100536
/home/ilju/research/DiffuAgent/think_parallel_v0/outputs/llada_think_parallel_23628
```

이 문서는 `think_parallel_v0`의 현재 결과를 바탕으로, 프롬프트 문제,
필수 metric, gold hop matching 방식, 그리고 matcher 개선 방향을 정리한다.

## 1. 보고서 목적과 현재 입력 구성

이 보고서의 핵심 질문은 다음이다.

```text
LLaDA 같은 DLM은 BFCL에서 strict tool-call format을 잘 맞추지 못하더라도,
agentic task를 수행하기 위한 think/action plan은 만들 수 있는가?
```

이 질문을 보는 이유는 더 큰 연구 목표와 연결된다.

```text
agentic task의 subtask 중에서
미리 결정할 수 있는 action과
이전 실행/관찰 이후에야 결정할 수 있는 action을 구분하고 싶다.
```

```text
denoising dynamic과 병렬화 가능한 hop의 think사이 상관관계가 있는가? 라는 질문에 대한 답을 얻기 전
논리를 확고화 하기위한 선행질문이라고 보면된다.
```

따라서 현재 실험에서 `[T]`와 `[A]`는 다음 역할을 가진다.

```text
[T]:
  다음 tool을 왜 써야 하는지, 지금 무엇을 확인하거나 정해야 하는지 적은 짧은 문장.

[A]:
  exact BFCL function-call syntax가 아니라,
  어떤 tool/action을 의도하는지 보여주는 action anchor.
```

### 1.1 Full User Goal

현재 full user goal은 BFCL sample의 모든 user turn을 단순히 이어 붙여 만든다.
구현은 `think_parallel_v0/src/bfcl_data.py`의 `join_user_goal()`을 따른다.

BFCL sample의 `question`은 turn들의 list다.

```python
question = [
    [{"role": "user", "content": "..."}],
    [{"role": "user", "content": "..."}],
]
```

현재 구현은 각 turn에서 `role == "user"`인 message의 `content`만 모은다.
assistant/tool message는 full goal 생성에 쓰지 않는다.

결과 문자열은 다음 형식이다.

```text
[turn 1] first user request
[turn 2] second user request
...
```

예시:

```text
[turn 1] I am alex. Check if the current directory is under my name and list all the visible and hidden contents in the current directory now, please.
[turn 2] Go to workspace directory and move one of the 'log.txt' files into a new directory 'archive'.
[turn 3] Investigate within 'log.txt' for the occurrence of the keyword 'Error'.
[turn 4] Finally, show the last 20 lines the file.
```

중요한 점은, 현재 setting이 online multi-turn execution이 아니라는 것이다.

```text
현재 실험:
  모든 future user turn까지 포함한 offline global goal을 한 번에 제공한다.

온라인 BFCL 실행:
  매 turn마다 현재까지의 대화 prefix만 보고 action을 결정한다.
```

즉 현재 실험은 “global goal이 주어졌을 때 coarse/subtask-level plan을 만들 수
있는가?”를 보는 P0 sanity check다.

### 1.2 Initial Config

`initial_config`는 BFCL sample 안에 들어있는 초기 환경 상태다. 파일 상태,
예약 상태, 메시지 상태, DB-like state, 앱 내부 state 같은 시작 조건을 담을 수
있다.

현재 구현에서는 `sample.get("initial_config", {})`로 읽고, 값이 없으면 빈 dict로
처리한다.

`initial_config`는 아래 mode에 포함된다.

```text
goal_init_tools_ta
goal_init_tools_a
```

prompt에는 다음 heading으로 들어간다.

```text
Initial environment configuration summary:
{compact_initial_config_json}
```

요약 방식:

```text
1. dict/list를 재귀적으로 순회한다.
2. {"type": "file", "content": ...} 형태의 file node는 content를 최대 300자로 자른다.
3. 전체 config를 json.dumps(..., sort_keys=True)로 문자열화한다.
4. 전체 문자열이 5000자를 넘으면 잘라서 ...<truncated>를 붙인다.
```

예를 들어 원래 `initial_config`가 다음과 같다면:

```json
{
  "filesystem": {
    "workspace": {
      "log.txt": {
        "type": "file",
        "content": "Error: failed to open socket\nWarning: retrying\n..."
      }
    }
  },
  "current_directory": "/home/alex",
  "user": "alex"
}
```

prompt에는 대략 다음처럼 compact JSON 문자열로 들어간다.

```text
Initial environment configuration summary:
{"current_directory": "/home/alex", "filesystem": {"workspace": {"log.txt": {"content": "Error: failed to open socket\nWarning: retrying\n...", "type": "file"}}}, "user": "alex"}
```

파일 내용이 길면 `content`만 먼저 300자로 잘리고, 전체 initial config 문자열이
너무 길면 마지막에 `...<truncated>`가 붙는다.

이번 A-only 결과에서 initial_config 포함 mode가 더 나빠진 것은
initial_config 자체가 불필요하다는 뜻이 아니다. 현재 prompt에서 initial_config가
들어가면 모델이 exact function name을 덜 쓰고 자연어 action 설명으로 더 많이
흐르는 문제가 관찰되었다.

### 1.3 Function Schema

function schema는 `sample["function"]`에서 가져온다. BFCL v3의
`func_doc_language_specific_pre_processing()`을 거친 뒤,
`system_prompt_pre_processing_chat_model()`을 통해 system message에 주입된다.

즉 function schema는 user prompt에 직접 붙이지 않는다.

```text
system message:
  BFCL v3 기본 system prompt
  + JSON serialized function schema
  + diagnostic override

user message:
  planning-only instruction
  + full user goal
  + optional initial_config summary
```

기본 실행은 `v3+json`이다.

```text
BFCL_FUNCTION_DOC_SERIALIZATION=json
CATEGORY=multi_turn_base
IDS_FILE=test_case_ids_to_generate_v3.json
```

## 2. 현재 run의 요약 해석

이번 run은 BFCL `multi_turn_base` 50개 sample에 대해 `both_ta`를 실행한
결과다.

```text
modes:
  - goal_tools_ta
  - goal_init_tools_ta

generation_config:
  gen_length = 128
  steps = 128
  block_length = 32
  temperature = 0.0
  threshold = 0.9
```

핵심 결과:

| Mode | format_parse_rate | tool_selection_recall | missing_action_rate | hallucinated_action_rate | compound_action_rate |
|---|---:|---:|---:|---:|---:|
| `goal_tools_ta` | 0.940 | 0.297 | 0.703 | 0.430 | 0.020 |
| `goal_init_tools_ta` | 1.000 | 0.307 | 0.693 | 0.439 | 0.019 |

현재 결과는 다음처럼 해석하는 것이 안전하다.

```text
형식 준수는 비교적 좋다.
하지만 gold trajectory의 action/tool hop 회수율은 낮다.
initial_config는 parse stability에는 도움을 주지만, action recall을 크게 올리지는 못했다.
compound action 문제는 이번 run에서 주 병목은 아니다.
```

따라서 이 run만으로는 “LLaDA가 exact BFCL tool-call format은 못 맞춰도
think/action plan은 잘 만든다”고 주장하기 어렵다. 보다 조심스럽게는
다음 정도로 말할 수 있다.

```text
LLaDA는 planning-only [T]/[A] 형식은 상당히 잘 따른다.
그러나 현재 prompt와 matcher 기준에서는 필요한 action/tool hop을 충분히 회수하지 못한다.
```

### 2.1 A-only run 분석

`llada_think_parallel_23628`은 같은 `multi_turn_base` 50개 sample에 대해
`both_a`를 실행한 A-only action-planning baseline이다.

```text
modes:
  - goal_tools_a
  - goal_init_tools_a

parse:
  raw_generations.jsonl = 100
  think_units.jsonl = 100
  matched_units.jsonl = 100
  parse_mode = a_only for all 100 generations
```

핵심 결과:

| Mode | units | matched | match_rate | tool_selection_recall | missing_action_rate | hallucinated_action_rate | compound_action_rate |
|---|---:|---:|---:|---:|---:|---:|---:|
| `goal_tools_a` | 290 | 83 | 0.286 | 0.294 | 0.706 | 0.714 | 0.007 |
| `goal_init_tools_a` | 299 | 55 | 0.184 | 0.188 | 0.812 | 0.816 | 0.010 |

포맷 관점에서는 A-only prompt가 매우 안정적이다.

```text
goal_tools_a:
  format_parse_rate = 1.000
  a_only_format_rate = 1.000
  units per generation mean = 5.80

goal_init_tools_a:
  format_parse_rate = 1.000
  a_only_format_rate = 1.000
  units per generation mean = 5.98
```

하지만 action coverage 관점에서는 `goal_tools_a`가 TA mode와 거의 비슷하고,
`goal_init_tools_a`는 오히려 더 나쁘다.

```text
TA baseline:
  goal_tools_ta      recall = 0.297
  goal_init_tools_ta recall = 0.307

A-only:
  goal_tools_a       recall = 0.294
  goal_init_tools_a  recall = 0.188
```

따라서 A-only 결과는 다음처럼 읽는 것이 안전하다.

```text
A-only는 [T] rephrasing 문제를 제거한다.
그러나 [T]를 제거해도 action/tool hop recall은 개선되지 않았다.
즉 현재 병목은 [T] 생성 때문만이 아니라, action을 exact function name으로 회수하는 능력 또는 prompt/matcher 정렬에도 있다.
```

특히 `goal_init_tools_a`가 나빠진 이유는 initial_config 자체가 나쁘다기보다,
initial_config가 들어간 prompt에서 모델이 exact function name을 덜 쓰고
자연어 작업 설명으로 더 많이 흐른 것이 크다.

```text
goal_tools_a:
  total units = 290
  units with no function mention = 162
  unmatched units = 207
  unmatched with no function mention = 162
  unmatched with function mention = 45

goal_init_tools_a:
  total units = 299
  units with no function mention = 198
  unmatched units = 244
  unmatched with no function mention = 198
  unmatched with function mention = 46
```

즉 `goal_init_tools_a`의 unmatched action 대부분은 모델이 action을 다음처럼
표현했기 때문에 발생했다.

```text
Check if the current directory is under my name and list all the visible and hidden contents.
Navigate to the workspace directory.
Move one of the 'log.txt' files into a new directory named 'archive'.
Investigate within 'log.txt' for the occurrence of the keyword 'Error'.
Show the last 20 lines of the file.
```

사람이 보면 각각 `ls`, `cd`, `mv`, `grep`, `tail`에 대응될 수 있지만,
현재 matcher는 exact function mention 중심이므로 전부 unmatched가 된다.

반면 `goal_tools_a`는 같은 sample에서 더 평가 가능한 형태를 출력했다.

```text
[A1] Use ls to list the contents of the current directory.
[A3] Use cd to navigate to the workspace directory.
[A4] Use mv to move one of the 'log.txt' files into a new directory 'archive'.
[A5] Use grep to investigate within 'log.txt' for the occurrence of the keyword 'Error'.
[A6] Use tail to show the last 20 lines of the file.
```

다만 `goal_tools_a`도 완전히 좋은 것은 아니다. 불필요하거나 gold에 없는
action을 추가하는 경향이 있다.

```text
Use pwd to check if the current directory is under Alex's name.
Use ls to list the contents of the new 'archive' directory.
```

이런 action은 실제로 그럴듯할 수 있지만 gold hop에는 없으므로 hallucinated 또는
extra action으로 잡힌다.

샘플별로 보면 `goal_tools_a`가 `goal_init_tools_a`보다 나은 sample이 많다.

```text
goal_tools_a recall > goal_init_tools_a recall: 14 samples
goal_init_tools_a recall > goal_tools_a recall: 2 samples
tie: 34 samples
```

대표 차이:

| Sample | `goal_tools_a` | `goal_init_tools_a` | 해석 |
|---|---:|---:|---|
| `multi_turn_base_1` | 5/6 | 0/6 | init mode가 tool name 없이 자연어 action만 출력 |
| `multi_turn_base_7` | 3/4 | 0/4 | init mode가 directory/file 작업을 자연어로만 출력 |
| `multi_turn_base_108` | 4/6 | 0/6 | init mode가 function mention을 잃음 |
| `multi_turn_base_117` | 4/6 | 0/6 | init mode가 function mention을 잃음 |
| `multi_turn_base_143` | 0/6 | 3/6 | init_config가 필요한 stock/order/account context를 일부 도와줌 |

이 결과는 A-only baseline의 목적을 분명하게 보여준다.

```text
A-only 좋음 + TA의 T가 copy:
  action planning은 가능하고, [T] 설계가 문제일 가능성.

이번 결과:
  A-only도 recall이 낮다.
  특히 no-function-mention action이 많다.
  따라서 [T] 이전에 action format/prompt/matcher 정렬을 먼저 고쳐야 한다.
```

현재 A-only 결과를 연구 주장으로 연결하면 다음 정도가 적절하다.

```text
LLaDA는 A-only label 형식 자체는 안정적으로 따른다.
하지만 exact BFCL tool-call format 없이도 필요한 tool intent를 충분히 회수한다고 말하기에는 아직 약하다.
현재 strict function-name matcher 기준으로는 goal_tools_a recall이 약 0.29에 머문다.
initial_config를 붙인 A-only prompt는 오히려 function-name usage를 약화시켰다.
```

## 3. 현재 실험의 가장 큰 문제

현재 가장 큰 문제는 하나로 압축하면 다음이다.

```text
현재 실험은 "think를 잘하는가?"를 묻고 있지만,
실제 측정은 아직 "function-name 기반 action anchor를 얼마나 회수했는가?"에 가깝다.
```

즉 연구 질문과 현재 operational metric 사이에 간격이 있다.

연구 질문:

```text
DLM이 exact tool-call format을 못 맞춰도,
agent task의 subtask 중 미리 결정 가능한 부분을 think/action으로 잡아낼 수 있는가?
```

현재 측정:

```text
generated [A] 문장에 gold function name이 들어 있는가?
그 function name을 gold hop에 붙일 수 있는가?
```

이 간격 때문에 현재 결과만으로는 “LLaDA가 agent task를 위한 think를 제대로
한다”고 충분히 답하기 어렵다.

### 3.1 프롬프트 문제

현재 프롬프트는 `[T]/[A]` 또는 `[A]` label format은 안정적으로 유도한다.
하지만 “미리 결정 가능한 subtask를 식별한다”는 의도를 충분히 직접적으로
반영하지는 않는다.

현재 prompt의 장점:

```text
1. BFCL function schema를 그대로 사용한다.
2. exact BFCL function-call syntax는 요구하지 않는다.
3. [T]/[A] 또는 [A]-only 형식은 잘 유도한다.
```

현재 prompt의 약점:

```text
1. [T]가 local reasoning이 아니라 user request rephrasing으로 흐를 수 있다.
2. [A]가 exact function name 없이 자연어 작업 설명으로 흐를 수 있다.
3. "미리 결정 가능"과 "관찰 이후 결정 필요"의 구분을 직접 요구하지 않는다.
```

`[A1] Use <exact_function_name>: <one-sentence purpose>`처럼 조이는 것은
평가 안정성에는 도움이 된다. 다만 사용자의 우려처럼 레퍼런스성이 약해질 수
있다. BFCL 기본 prompt나 DiffuAgent 선행 repo의 원래 목적은 executable function
call을 생성하는 것이지, 이런 labeled planning line을 생성하는 것이 아니기
때문이다.

따라서 프롬프트 개선은 다음 원칙이 좋다.

```text
BFCL-native schema와 system prompt는 유지한다.
출력만 exact call이 아니라 "action plan diagnostic format"으로 바꾼다.
형식을 강제하되, 새로운 taxonomy나 synthetic few-shot은 먼저 넣지 않는다.
```

추천되는 다음 prompt 방향:

```text
[A1] Use <exact_function_name>: <intended action>. Known inputs: <known entities/arguments>. Unresolved inputs: <inputs that must come from prior tool results, if any>.
```

이 형식은 exact BFCL call format은 아니지만, BFCL function name과 argument
intent를 모두 남긴다. 즉 레퍼런스를 완전히 버리는 것이 아니라 BFCL-native
tool schema를 anchor로 삼는 절충안이다.

여기서 argument는 “정답 function call의 모든 인자를 맞히기”가 아니다. 지금 단계의
목표는 다음 두 가지다.

```text
1. user request나 initial_config에 이미 주어진 known input을 보존하는가?
2. 이전 tool 결과가 필요한 unresolved input을 지어내지 않고 표시하는가?
```

`PRECOMPUTABLE` 같은 status를 출력하게 하는 것은 지금 단계에서는 하지 않는다.
그것은 action recovery 다음 단계의 dependency/DAG 판단 실험으로 분리한다.

### 3.2 Matcher 문제

현재 matcher는 function name mention을 중심으로 gold hop에 붙인다. 이 방식은
초기 진단용으로는 단순하고 재현 가능하지만, “think/action intent”를 보기에는
부족하다.

핵심 한계:

```text
1. 같은 function이 여러 hop에 반복되면 first-unused hop에 붙을 수 있다.
2. argument/entity intent를 충분히 보지 않는다.
3. tool name이 없지만 의미상 맞는 action은 놓친다.
4. 한 [A]가 여러 hop을 차지하면 recall은 올라가지만 decomposition 실패가 가려진다.
```

사용자 질문처럼, 결국 우리가 보고 싶은 것은 함수명만이 아니라 argument를 포함한
의도다. 예를 들어 다음 두 action은 같은 `get_flight_cost`라도 서로 다른 action
intent일 수 있다.

```text
Use get_flight_cost for New York to Seoul.
Use get_flight_cost for Boston to Paris.
```

따라서 rule-based matcher만으로는 최종 주장까지 가기 어렵다. 다만 바로
LLM-as-judge를 주 metric으로 쓰기보다는 다음 순서가 좋다.

```text
1. deterministic argument-aware matcher를 먼저 추가한다.
2. 같은 function 후보 중 argument/entity overlap이 가장 큰 hop을 고른다.
3. 그 뒤 LLM-as-judge를 audit 또는 보조 metric으로 사용한다.
4. 최종적으로 rule score와 judge score가 얼마나 일치하는지 보고 신뢰도를 판단한다.
```

LLM-as-judge를 적극 쓰는 것은 타당하다. 특히 “의도” 평가는 rule만으로 어렵다.
하지만 처음부터 judge만 쓰면 재현성과 실패 분석이 흐려진다. 따라서
ParallelAgent에서 한 것처럼 judge prompt를 세밀하게 설계하되, deterministic
matcher와 함께 쓰는 hybrid가 더 안전하다.

### 3.3 근본적인 세팅 문제

현재 global goal은 모든 user turn을 단순 concat한 offline goal이다. 이 setting은
“전체 task가 주어졌을 때 어떤 subtask/action이 미리 정해질 수 있는가?”를
보기 위한 핵심 setting에 가깝다.

현재 global-goal setting이 보는 것:

```text
전체 future user requests를 알고 있을 때,
모델이 전체 trajectory를 subtask/action 단위로 나누고,
그중 어떤 action이 다른 action 결과 없이 정해질 수 있는지 드러낼 수 있는가?
```

turn-prefix planning이 보는 것:

```text
현재 turn까지의 정보만 있을 때,
지금 미리 결정 가능한 action은 무엇이고,
어떤 action은 관찰/실행 결과 이후로 미뤄야 하는가?
```

따라서 turn-prefix planning은 global goal의 대체가 아니다. 오히려 다른 질문을
본다. turn-prefix는 future turn의 지시를 모르기 때문에, 전체 task 기준으로
미리 결정 가능한 action을 모두 식별하기 어렵다.

권장 해석:

```text
global goal:
  subtask 병렬화와 pre-computable action 분석에 적합한 main setting.
  전체 task를 안다는 oracle-style 조건이므로 online agent 현실성과는 다르다.

turn-prefix planning:
  online deployment realism을 보기 위한 follow-up setting.
  현재 시점에서 agent가 실제로 무엇을 결정할 수 있는지 평가한다.
```

즉 현재 연구 목표가 “전체 agentic task의 subtask 중 미리 결정 가능한 것을
구분한다”라면 global goal setting이 먼저 오는 것이 맞다. 다만 슬라이드나
논문에서는 이것이 online execution setting이 아니라는 점을 명확히 밝혀야 한다.

## 4. 프롬프트 문제점

현재 prompt는 `[T]/[A]` 형식을 꽤 잘 유도한다. 문제는 출력된 `[A]`가
평가 가능한 action intent로 충분히 고정되지 않는다는 점이다.

### 4.1 자연어 작업 설명으로 흐르는 문제

현재 prompt에는 이미 다음 제약이 있다.

```text
When an [A] uses an available function, start the sentence with that exact function name or with 'Use <function_name>'.
```

하지만 실제 output에는 다음처럼 tool name 없이 자연어 작업 설명만 쓰는 경우가
있다.

```text
[A] Display the content of project_analysis.txt.
[A] Create a duplicate of the file.
[A] Compare content with the old file.
```

사람이 보면 각각 `cat`, `cp`, `diff` 또는 유사 tool intent를 떠올릴 수 있다.
그러나 현재 matcher는 exact function name 중심이므로 이런 문장을 gold hop에
매칭하지 못할 수 있다.

따라서 `[A]` 형식은 더 강하게 고정하는 편이 좋다.

```text
[A1] Use <exact_function_name>: <one-sentence purpose>
```

예:

```text
[A1] Use ls: list visible and hidden files in the current directory.
[A2] Use mv: move log.txt into archive.
[A3] Use grep: search log.txt for "Error".
```

이 형식은 exact BFCL function-call syntax를 요구하지 않으면서도, tool intent
평가를 안정화한다.

### 4.2 `[T]`가 user goal rephrasing이 되는 문제

현재 `[T]`는 “다음 action을 왜 해야 하는가”라기보다 user request를 다시
풀어쓰는 경우가 많다.

예상되는 실패 형태:

```text
[T1] Check if the current directory is under my name and list all contents.
```

이 문장은 think라기보다 user instruction의 재진술에 가깝다. 따라서 TA mode의
프롬프트에는 다음 제약을 추가할 수 있다.

```text
Each [T] should state the local reason for the next tool action,
not restate the user's request.
```

다만 현재 단계에서는 `[T]` 품질을 먼저 주장하기보다, A-only mode로 action
planning baseline을 확인하는 것이 더 안전하다.

```text
A-only가 좋음:
  LLaDA가 action/tool intent는 회수할 수 있다.
  이후 [T]가 rephrasing인지, reasoning signal인지 분석할 수 있다.

A-only도 나쁨:
  [T] 문제가 아니라 basic action planning부터 약하다.
```

## 5. 꼭 필요한 지표

현재 단계에서 가장 중요한 지표는 많지 않다.

| 지표 | 정의 | 계산식 | 해석 | 현재 주의점 |
|---|---|---|---|---|
| `format_parse_rate` | output이 parser로 회수 가능한 비율 | `parse_mode != "failed"` generation 수 / 전체 generation 수 | 실험 output 형식 안정성 | 낮으면 matching/confidence 해석 불안정 |
| `ta_format_rate` | TA 형식으로 파싱된 비율 | `parse_mode == "ta"` generation 수 / 전체 generation 수 | `[Tn]`/`[An]` 형식 준수 | TA mode에서만 핵심 |
| `a_only_format_rate` | A-only 형식으로 파싱된 비율 | `parse_mode == "a_only"` generation 수 / 전체 generation 수 | `[An]` 형식 준수 | A-only mode에서만 핵심 |
| `match_rate` | generated unit 중 gold hop에 하나 이상 붙은 비율 | matched units / generated units | 생성한 action 중 평가 가능한 action 비율 | gold coverage가 아니라 unit precision에 가까움 |
| `tool_selection_recall` | gold hop 중 generated action이 회수한 비율 | matched gold hops / total gold hops | 필요한 function/action coverage | 현재는 function-name 중심 recall에 가까움 |
| `missing_action_rate` | gold hop 중 놓친 비율 | `(total gold hops - matched gold hops) / total gold hops` | 필요한 action 누락 정도 | 현재 구현에서는 거의 `1 - tool_selection_recall` |
| `hallucinated_action_rate` | generated unit 중 gold hop에 안 붙은 비율 | unmatched units / generated units | extra/unmatched action 비율 | 진짜 hallucination, tool-name missing, matcher miss가 섞임 |
| `compound_action_rate` | 한 unit이 여러 tool/hop을 포함한 비율 | compound units / generated units | action decomposition 실패 신호 | 주 성공 metric에서는 실패로 보고, coverage upper-bound에서만 별도 계산 |
| `think_mean_confidence` | `[T]` span token confidence 평균 | `[T]` char span과 겹치는 trace token confidence 평균 | denoising certainty | recall이 낮으면 label별 해석이 불안정 |
| `action_mean_confidence` | `[A]` span token confidence 평균 | `[A]` char span과 겹치는 trace token confidence 평균 | action span denoising certainty | A-only에서는 주요 confidence 지표 |
| `ranking.weak_a_above_strong` | Weak-A confidence가 Strong보다 높은 pairwise 비율 | Weak-A/Strong matched units의 confidence pairwise 비교 | dependency label별 denoising signal 후보 | matching이 안정된 뒤 해석해야 함 |

현재 단계에서 슬라이드에 우선 넣을 지표는 아래 다섯 개다.

```text
format_parse_rate
tool_selection_recall
missing_action_rate
hallucinated_action_rate
compound_action_rate
```

보조 지표:

다음 지표들은 후속 분석에서는 중요하지만, 현재처럼 recall이 낮을 때는
조심스럽게 봐야 한다.

```text
think_mean_confidence
action_mean_confidence
ranking.weak_a_above_strong
ranking.independent_above_strong
```

이들은 “DLM denoising dynamics에 dependency type을 구분할 수 있는 힌트가
있는가?”를 보기 위한 보조 축이다. 하지만 generated action이 gold hop에
불안정하게 붙으면 label별 confidence 통계도 오염된다.

## 6. 현재 gold hop matching 방식

현재 matcher는 semantic judge가 아니라 rule-based matcher다. 핵심은
generated `[A]` 문장 안의 function name mention을 gold hop의 function name에
붙이는 것이다.

### 6.1 기본 절차

1. generated action text에서 available function 이름을 찾는다.

```text
[A1] Use get_flight_cost to check the flight price.
```

위 문장에서는 `get_flight_cost`가 mentioned tool로 추출된다.

2. gold graph의 hop에서 function name을 추출한다.

```text
h1: get_nearest_airport_by_city(...)
h2: get_flight_cost(...)
h3: book_flight(...)
```

3. mentioned tool과 gold hop tool name이 같으면 매칭한다.

```text
generated mentions get_flight_cost
gold hop h2 is get_flight_cost
=> generated unit -> h2
```

4. 이미 매칭된 gold hop은 다시 쓰지 않는다.

5. 한 generated unit이 여러 tool을 언급하면 여러 hop에 붙을 수 있다.

```text
[A1] Use cat to read the file and grep to find Error.
=> matched_hop_ids = [cat hop, grep hop]
=> compound_action = True
```

### 6.2 같은 tool이 gold hop에 여러 번 있을 때

현재 구현의 중요한 한계다. 같은 tool name을 가진 gold hop이 여러 개 있으면,
현재 matcher는 argument나 문맥을 깊게 비교하지 않고, 아직 쓰이지 않은 첫 번째
같은-tool hop을 고른다.

예:

```text
gold:
  h1: cat("a.txt")
  h3: cat("b.txt")
  h5: cat("result.txt")

generated:
  [A1] Use cat to inspect result.txt.
```

현재 matcher는 `result.txt`를 보고 h5를 고르는 것이 아니라, h1이 아직
unused이면 h1에 먼저 붙일 수 있다.

따라서 현재 `tool_selection_recall`은 다음에 가깝다.

```text
정확한 argument-level trajectory recall
  보다는
필요한 tool family 또는 function name을 어느 정도 회수했는지
```

### 6.3 compound action 처리

gold graph에 별도 “compound hop” 단위가 있는 것은 아니다. gold는 function-call
hop들의 리스트다. compound 여부는 generated unit을 gold hop에 매칭한 뒤
사후적으로 판단한다.

예:

```text
generated:
  [A1] Use cat and grep to inspect the file.

gold:
  h1: cat(...)
  h2: grep(...)
```

현재 matcher는 한 문장이 hop 두 개를 차지하도록 허용한다.

```text
matched_hop_ids = ["h1", "h2"]
compound_action = True
```

즉 compound action은 coverage에는 관대하게 작동한다. 하지만 서브태스크 단위
병렬화 가능성을 보려면, compound action은 decomposition 실패 신호로 별도
관리해야 한다.

## 7. Prompt / Matcher 수정 계획

다음 수정의 목표는 “LLaDA가 exact BFCL call syntax를 못 맞춰도 agentic
subtask/action intent를 만들 수 있는가?”를 더 직접적으로 평가하는 것이다.

### 7.1 Prompt 수정 계획

현재 prompt는 label format은 잘 유도하지만, action을 exact function name과
argument/entity intent로 안정적으로 남기지 못한다. 다만 `Use <exact_function_name>`
형식을 main으로 두면 또 다른 문제가 생긴다.

```text
Use <exact_function_name> 형식의 장점:
  exact executable BFCL call syntax는 요구하지 않는다.
  matcher가 쉽고 hop anchor가 안정적이다.

Use <exact_function_name> 형식의 약점:
  BFCL function-name selection/copying 능력과 action planning 능력이 다시 섞인다.
  실패했을 때 "계획을 못 한 것"인지 "정확한 함수명을 못 쓴 것"인지 분리하기 어렵다.
```

따라서 prompt 조건은 하나로 고정하지 말고, 다음처럼 역할을 나누는 것이 좋다.

#### A. Tool-ID A-only: action intent main diagnostic

```text
[A1] Tool #k | Intent: <intended action> | Known inputs: <known entities/arguments> | Unresolved inputs: <inputs from prior tool results, if any>
```

예:

```text
[A1] Tool #1 | Intent: list visible and hidden entries in the current directory | Known inputs: current directory, include hidden files | Unresolved inputs: none
[A2] Tool #2 | Intent: move into the workspace directory | Known inputs: workspace | Unresolved inputs: none
[A3] Tool #3 | Intent: move log.txt into archive | Known inputs: log.txt, archive | Unresolved inputs: none
[A4] Tool #4 | Intent: search log.txt for Error | Known inputs: log.txt, "Error" | Unresolved inputs: none
```

이 조건의 목적은 exact BFCL function name copying을 줄이고, action intent와
known entity/argument recovery를 더 직접적으로 보는 것이다.

중요한 주의:

```text
Tool-ID 조건이 의미 있으려면 prompt 안에서 원래 function name이 그대로 노출되지 않아야 한다.
즉 BFCL system prompt의 function schema를 그대로 쓰면서 Tool #k만 추가하면 분리가 약하다.
이 조건은 별도의 masked/aliased function schema serialization이 필요하다.
```

예를 들어 evaluator는 내부적으로 다음 mapping을 갖는다.

```text
Tool #1 -> ls
Tool #2 -> cd
Tool #3 -> mv
Tool #4 -> grep
```

하지만 모델 output에는 `ls`, `cd`, `mv`, `grep` 같은 exact function name을 요구하지
않는다.

#### B. Exact-name A-only: upper-bound/control

```text
[A1] Use <exact_function_name>: <intended action>. Known inputs: <known entities/arguments>. Unresolved inputs: <inputs from prior tool results, if any>.
```

예:

```text
[A1] Use ls: list visible and hidden files in the current directory. Known inputs: current directory, include hidden files. Unresolved inputs: none.
[A2] Use cd: move into the workspace directory. Known inputs: workspace. Unresolved inputs: none.
[A3] Use mv: move log.txt into archive. Known inputs: log.txt, archive. Unresolved inputs: none.
[A4] Use grep: search log.txt for "Error". Known inputs: log.txt, "Error". Unresolved inputs: none.
```

이 조건은 exact executable BFCL call format은 아니지만, exact function name을
출력해야 한다. 따라서 main claim보다는 upper-bound/control로 둔다.

해석:

```text
Tool-ID는 좋은데 exact-name이 나쁨:
  action intent는 잡지만 exact function-name copying이 약할 수 있음.

Tool-ID도 나쁨:
  function name 문제가 아니라 action planning 자체가 약할 수 있음.

exact-name만 좋음:
  강한 schema/name anchor가 있어야만 action recovery가 되는 것일 수 있음.
```

#### C. Natural TA: denoising dynamics main setting 후보

denoising dynamics와 `[T]`를 보려면, 너무 call-like한 형식만으로는 부족하다.
따라서 matcher가 안정된 뒤에는 자연어에 가까운 TA 조건이 필요하다.

예:

```text
[T1] The next step is to inspect the directory contents before file operations.
[A1] I would use the file-listing tool to list visible and hidden entries in the current directory. Known inputs: current directory, include hidden files. Unresolved inputs: none.

[T2] The next step is to move into the workspace before moving the file.
[A2] I would use the directory-change tool to move into workspace. Known inputs: workspace. Unresolved inputs: none.
```

이 조건은 가장 자연스럽지만, semantic matching 의존도가 커진다. 따라서 바로 main
metric으로 쓰기보다, Tool-ID / exact-name 조건으로 matcher와 action recovery를
먼저 안정화한 뒤 진행한다.

공통 규칙:

```text
1. Each [A] should describe exactly one intended tool/action.
2. Do not combine multiple tool actions in one [A].
3. Include known file names, ids, dates, locations, entities, and other key inputs when they are stated in the user request or initial_config.
4. If an input must come from a previous tool result, write it under "Unresolved inputs"; do not invent its value.
5. Do not output executable argument syntax such as arg=value or JSON objects.
6. Do not add verification, cleanup, or inspection actions unless explicitly requested.
7. [Tn], when present, should explain only [An], not the whole user turn.
```

예:

```text
[A1] Use get_stock_info: retrieve recent market data for Zeta Corp. Known inputs: Zeta Corp. Unresolved inputs: none.
[A2] Use place_order: buy 50 shares of Zeta Corp at the current market price. Known inputs: Zeta Corp, 50 shares, buy. Unresolved inputs: exact current market price from the stock-info result.
```

이렇게 하면 argument를 아예 버리지 않으면서도, 아직 알 수 없는 id, price, file,
booking number 등을 hallucinate하지 않도록 평가할 수 있다.

`PRECOMPUTABLE` / `DEPENDS_ON_OBSERVATION` 같은 status 필드는 지금 prompt에 넣지
않는다. 이것은 action recovery와 matcher가 안정된 뒤, dependency/DAG 판단을
보는 후속 실험으로 분리한다.

초기에는 few-shot을 넣지 않는 편이 좋다. few-shot을 넣으면 action decomposition
스타일이 예시에 끌려갈 수 있고, “BFCL 기본 schema만으로 가능한가?”라는 질문이
흐려진다. 다만 prompt만으로 function-name usage가 계속 낮으면, BFCL에서 가져온
짧은 in-domain example 1개를 추가하는 ablation을 둘 수 있다.

### 7.2 Matcher 수정 계획

사용자 제안처럼 현재 rule-based matcher는 final matcher가 아니라 **candidate
generator**로 낮추는 것이 좋다. 메인 matching 판단은 LLM-as-judge가 하되,
judge가 볼 후보는 rule-based로 좁힌다.

권장 구조:

```text
generated [A] unit
  -> rule-based candidate generator
  -> top-k gold hop candidates
  -> LLM-as-judge pairwise exact + semantic matching
  -> matched_hop_ids / match_type / judge_rationale 저장
```

LLM judge가 직접 전체 gold graph를 자유롭게 뒤지는 것이 아니다. 먼저 후보를
뽑고, judge는 다음 pair를 비교한다.

```text
generated [A_i]
vs
candidate gold hop h_j
```

예:

```text
generated:
  [A3] Tool #4 | Intent: search log.txt for Error | Known inputs: log.txt, "Error"

candidate gold hop:
  h5: grep({"file_name": "log.txt", "pattern": "Error"})
```

judge는 이 pair가 같은 action intent인지 판단한다.

### 7.3 Rule-based candidate generator

candidate generator는 recall을 높이는 역할만 한다. 이 단계에서는 semantic 판단을
하지 않는다. 즉 “이 문장이 의미상 `cat`이다” 같은 결정은 rule-based가 아니라
LLM-as-judge가 맡는다.

rule-based candidate generator가 해야 하는 일:

```text
1. Tool-ID, exact function name, known input overlap처럼 관찰 가능한 anchor로 후보를 넓게 뽑는다.
2. 후보를 너무 좁게 잘라 정답 hop이 빠지는 것을 막는다.
3. 최종 match 여부, semantic equivalence, argument compatibility는 판단하지 않는다.
```

후보 생성 기준:

```text
1. Tool-ID match
   - Tool-ID 조건이면 Tool #k -> function mapping으로 후보를 뽑는다.

2. exact / normalized function name mention
   - exact-name 또는 natural condition에서 function name이 직접 언급된 경우.

3. known-input argument/entity overlap
   - file name, id, date, location, ticker, user id, order id, literal string 등.
   - generated "Known inputs"와 gold hop arguments를 비교한다.
   - generated "Unresolved inputs"는 exact value mismatch로 벌점 처리하지 않는다.

4. same-tool all-candidates
   - 같은 function이 여러 hop에 반복되면 첫 번째만 뽑지 않고 같은 function 후보를 모두 포함한다.

5. 같은 turn 또는 가까운 turn의 hop 우선
   - 단, 이것은 ranking signal일 뿐 hard filter가 아니다.

6. fallback
   - 후보가 너무 적으면 전체 graph에서 known-input/entity overlap 상위 hop을 추가한다.
```

candidate generator의 원칙:

```text
precision보다 recall을 우선한다.
정답 hop이 후보 안에 들어오지 않으면 LLM judge가 복구할 수 없다.
하지만 semantic alias로 후보를 만들기 시작하면 rule-based 단계가 hidden judge가 되므로,
semantic alias는 기본 candidate generator에서 제외한다.
```

필요하다면 나중에 별도 ablation으로 `semantic_alias_candidate_generator`를 둘 수
있다. 하지만 main 평가에서는 사용하지 않는다.

출력 예:

```json
{
  "unit_id": "u3",
  "action": "Tool #2 | Intent: display the content of project_analysis.txt | Known inputs: project_analysis.txt",
  "candidate_hops": [
    {
      "hop_id": "h4",
      "gold_call": "cat({\"file_name\": \"project_analysis.txt\"})",
      "candidate_reason": ["tool_id: Tool #2", "arg_overlap: project_analysis.txt"]
    }
  ]
}
```

권장 top-k:

```text
기본 top_k = 5
같은 function 반복이 많으면 same-tool candidates는 top_k 밖이라도 모두 유지
```

### 7.4 LLM-as-Judge matcher

LLM judge는 candidate hop마다 다음을 판단한다.

```text
1. Is this generated action intended to perform the same tool/function as the gold hop?
2. Are the known inputs compatible with the gold hop arguments?
3. Is the action too broad or compound?
4. Does the generated action hallucinate an input value that should have been unresolved?
```

judge 출력은 JSON으로 고정한다.

```json
{
  "unit_id": "u3",
  "candidate_hop_id": "h4",
  "match": true,
  "match_type": "exact_intent",
  "confidence": 0.92,
  "reason": "Both actions use cat to read project_analysis.txt."
}
```

`match_type`은 최소한 다음처럼 나눈다.

```text
exact_intent:
  function/tool intent가 맞고 known inputs가 gold hop arguments와 호환됨.

partial_intent:
  function/tool intent는 맞지만 known inputs가 불완전하거나 일부만 맞음.

semantic_intent:
  function name은 없지만 자연어 의도가 gold hop과 맞음.

wrong_intent:
  function/tool intent 또는 핵심 known input이 다름.

hallucinated_argument:
  이전 tool 결과가 필요한 값을 generated action이 임의로 확정함.

compound:
  한 generated action이 여러 gold hop을 섞음.

not_enough_information:
  현재 문장만으로 판단하기 어려움.
```

메인 metric은 `exact_intent + semantic_intent`를 match로 볼지, 또는
`exact_intent`만 match로 볼지 둘 다 보고 분리한다.

```text
strict_judge_recall:
  exact_intent만 match.

semantic_judge_recall:
  exact_intent + semantic_intent를 match.

partial_recall:
  partial_intent까지 포함한 upper-bound.
```

이렇게 하면 “LLaDA가 function name을 정확히 말했는가”와 “tool-call format은
못 맞춰도 action intent는 맞았는가”를 분리할 수 있다.

최종 match 선택:

```text
For each generated [A_i]:
  1. judge 결과 중 match=true인 후보를 모은다.
  2. exact_intent > semantic_intent > partial_intent 순서로 우선한다.
  3. 같은 type이면 confidence가 높은 후보를 고른다.
  4. 그래도 같으면 argument/entity overlap이 높은 후보를 고른다.
  5. primary_hop_id는 하나만 저장한다.
  6. match=true 후보가 여러 개면 matched_hop_ids에 모두 저장하고 is_compound=true로 표시한다.
```

중요한 점:

```text
judge는 pairwise 비교를 한다.
final selection은 별도 deterministic resolver가 한다.
```

### 7.5 Compound 처리

최종 평가의 기본 단위는 **한 `[A]` = 한 gold hop**으로 둔다. 즉 주 성공 metric에서는
하나의 generated action이 하나의 intended tool/action hop에 대응되어야 한다.

다만 실제 output에서는 한 `[A]`가 여러 hop을 섞을 수 있다. 이 경우 matcher는
그 사실을 버리지 말고 기록하되, 성공으로 섞지 않는다.

```text
coverage 관점:
  여러 gold hop을 언급했으므로 upper-bound recall에는 포함 가능.

decomposition 관점:
  한 action unit이 여러 subtask를 섞었으므로 compound failure.
```

따라서 metric은 분리한다.

```text
strict_single_action_recall:
  exact_intent이면서 non-compound인 [A]만 성공.

semantic_single_action_recall:
  exact_intent 또는 semantic_intent이면서 non-compound인 [A]만 성공.

recall_including_compound:
  compound까지 포함한 coverage upper-bound.

compound_action_rate:
  여러 function/hop을 섞은 [A] 비율.

compound_matched_hop_count:
  compound [A]가 회수한 gold hop 수.
```

따라서 “한 `[A]`가 여러 hop에 match될 수 있는가?”에 대한 답은 다음과 같다.

```text
기록상으로는 가능하다.
하지만 주 평가에서는 성공으로 보지 않는다.
주 평가에서는 한 [A]가 하나의 hop에 대응되어야 한다.
multi-hop [A]는 compound/decomposition failure이며, coverage upper-bound로만 따로 본다.
```

### 7.6 저장 파일 제안

기존 output은 유지하고 judge 결과를 별도 파일로 둔다.

```text
outputs/<run>/
  raw_generations.jsonl
  think_units.jsonl
  matched_units.jsonl              # 기존 rule-based 결과
  judge_candidates.jsonl            # rule-based candidate generator 출력
  judge_matches.jsonl               # LLM judge 결과
  judge_metrics.json                # judge 기반 metric
  summary.md
```

기존 코드를 크게 바꾸지 않으려면 `run_discovery.py` 안에 바로 넣기보다,
기존 output을 읽어서 judge matching을 수행하는 후처리 스크립트로 시작하는 것이
좋다.

```text
src/judge_match_outputs.py
```

이렇게 하면 현재 generation 코드를 건드리지 않고, matcher만 반복 개선할 수 있다.

## 8. 다음 실험 우선순위

현재 결과와 matcher 한계를 고려하면, 다음 순서가 적절하다.

```text
1. Tool-ID A-only를 추가한다.
   목적: exact function-name copying 부담을 줄이고 action intent recovery를 먼저 본다.

2. Exact-name A-only를 control / upper-bound로 유지한다.
   목적: exact function name anchor를 주면 회수율이 얼마나 올라가는지 본다.

3. rule-based matcher를 high-recall candidate generator로 바꾼다.
   목적: Tool-ID, exact tool mention, known-input overlap으로 top-k hop 후보를 뽑음.

4. LLM-as-judge pairwise matcher와 deterministic resolver를 추가한다.
   목적: generated [A]와 candidate hop을 비교해 exact/semantic/partial intent를 판단함.

5. compound 포함 recall과 single-action-only recall을 분리한다.
   목적: coverage와 decomposition 품질을 분리.

6. Natural TA 조건을 추가한다.
   목적: hop-aligned [T]/[A] span을 만들고, denoising dynamics 분석에 쓸 수 있는지 본다.

7. dependency/precomputability 판단은 후속 실험으로 분리한다.
   목적: action recovery가 안정된 뒤 DAG 구조 판단으로 확장함.

8. turn-prefix planning setting을 추가한다.
   목적: online deployment realism을 확인하는 follow-up으로 사용한다.

9. recall/matching이 안정된 뒤 confidence/ranking 분석을 본다.
   목적: denoising dynamics와 dependency label의 관계 분석.
```

이 순서를 따르는 이유는 간단하다. 현재 상태에서는 `[T]` confidence나
dependency label ranking을 바로 해석하기 어렵다. 먼저 action coverage와
matching 신뢰도를 안정화해야, denoising dynamics 분석이 연구 질문에 제대로
연결된다.
