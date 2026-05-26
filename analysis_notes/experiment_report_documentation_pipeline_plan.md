# 실험 문서화와 보고서화 파이프라인 계획

날짜: 2026-05-16

## 1. 배경

`analysis_notes/260512_bfcl_reproduce_v2.html`은 비교적 빠르게 만들 수 있었다. 이유는 원본 Markdown이 단순한 raw note가 아니라 이미 보고서형 서사를 갖고 있었기 때문이다.

그 문서는 다음 구조가 자연스럽게 잡혀 있었다.

```text
문제 배경
-> 이상 현상
-> 가능한 원인 후보
-> 후보 제거 과정
-> 핵심 원인 발견
-> 비교 run 정의
-> raw output 비교
-> 결과표
-> 현재 해석
-> 시사점
```

하지만 모든 실험에 이 구조를 그대로 적용할 수는 없다. `think_parallel_v1`, `think_parallel_v2`처럼 실험 자체가 복잡하고, 분석 grain이 episode / turn / plan unit / token trace로 나뉘는 경우에는 단일 원인 추적 서사가 오히려 과도한 단순화를 만들 수 있다.

따라서 앞으로의 문서화 원칙은 다음으로 둔다.

> 본문은 technical spine을 가진 narrative로 쓰고, appendix는 reproducibility and audit trail로 제한한다.

즉 중요한 기술 내용을 appendix로 밀어내지 않는다. 결과 해석에 필요한 기술적 선택은 본문에 압축해서 넣고, 원문 확인이나 재현에 필요한 세부만 appendix로 보낸다.

짧게 말하면 다음 기준이다.

```text
Main text should be sufficient for judgment.
Appendix should be sufficient for verification.
```

## 2. 현재 합의한 문서화 원칙

### 2.1 본문에 남겨야 하는 기술

다음 detail은 본문에 있어야 한다. 이 정보가 빠지면 독자가 결과를 잘못 해석할 수 있다.

| 범주 | 본문에 남기는 이유 | 예 |
|---|---|---|
| 실험 scope | 결과가 무엇을 의미하는지 결정 | v1은 dependency/parallelism이 아니라 action recovery diagnostic |
| 데이터와 leakage 경계 | 평가 공정성과 해석을 결정 | v2는 previous turn gold context를 쓰지만 current-turn gold/DAG는 prompt에서 제외 |
| 핵심 prompt intervention | 실험 조건 그 자체 | v1 `exact_name_a`, v2 explicit `$id` vs flat placeholder |
| metric denominator와 caveat | 숫자의 의미를 결정 | `strict_single_action_recall`은 exact function-name validity가 아님 |
| confidence의 의미 | 과해석을 막음 | confidence는 정답 확률이 아니라 commit-time selected-token probability |
| 대표 failure mode | 결과의 원인을 설명 | under-generation, function-name drift, schema-invalid argument |

### 2.2 Appendix로 보내는 기술

다음 detail은 중요하지만 본문 흐름을 무겁게 만든다. 재현과 감사 목적의 appendix에 둔다.

| 범주 | appendix로 보내는 이유 | 예 |
|---|---|---|
| full prompt 전문 | 본문에는 핵심 rule만 필요 | 전체 system/user prompt |
| raw schema / field table | 원문 확인용 | `token_confidence.jsonl` 전체 field 설명 |
| 전체 artifact path | 재현용 | run output 파일 목록, absolute path |
| parser internals | 디버깅용 | fallback parse mode, detailed regex behavior |
| full judge rubric | 감사용 | q1-q4 enum 전체 |
| full ranking table | 결과 보조 | sample별 전체 ranking, tool별 전체 recall |
| raw generated/gold dumps | case audit용 | 모든 대표 사례의 긴 raw output |

### 2.3 판단 기준

어떤 technical detail을 본문에 둘지 appendix에 둘지 헷갈리면 다음 질문을 사용한다.

```text
이 detail이 결과 해석을 바꾸는가?
비교 조건을 이해하는 데 필요한가?
leakage, metric denominator, evaluator 차이처럼 validity를 좌우하는가?
놀라운 결과나 failure mode를 설명하는가?
skeptical reader가 claim을 보자마자 물어볼 내용인가?
```

하나라도 yes이면 본문에 압축해서 둔다.

다른 표현으로는 **argumentative necessity**가 가장 강한 기준이다.

```text
본문에 둘 것:
  claim을 이해하거나,
  method를 평가하거나,
  result를 해석하거나,
  uncertainty/limitation을 판단하거나,
  evidence에서 conclusion으로 가는 논리를 따라가는 데 필요한 것.

appendix에 둘 것:
  재현하거나,
  구현 선택을 audit하거나,
  extended output을 확인하거나,
  robustness를 검증하거나,
  detailed provenance를 보존하는 데 필요한 것.
```

반대로 다음이면 appendix로 둔다.

```text
같은 내용을 본문에서 이미 요약했다.
정확한 재현이나 원문 확인에만 필요하다.
긴 파일 경로, raw log, config dump, 전체 field table이다.
소수 implementation detail이고 주장을 이해하는 데 필수는 아니다.
```

## 3. 권장 보고서 구조

복잡한 ML/research experiment에는 다음 구조를 기본값으로 둔다.

```text
1. Executive Summary
2. Question and Scope
3. Experimental Design
4. Evaluation Logic
5. Results or Result Placeholder
6. Failure Modes / Case Studies
7. Interpretation Boundaries
8. Reproducibility and Audit Appendix
```

각 section의 목적은 다음과 같다.

### 3.1 Executive Summary

독자가 1분 안에 읽을 수 있는 압축 카드다.

포함할 것:

- 핵심 질문
- 비교 조건 또는 run
- headline result 또는 아직 `TBD`인 상태
- 가장 중요한 caveat
- 현재 해석 한 문장

여기에는 긴 prompt나 parser 설명을 넣지 않는다. 단, 실험 해석을 바꾸는 조건은 한 문장으로 반드시 넣는다.

예:

```text
이 run은 BFCL execution score가 아니라 LLaDA의 hop-level action recovery를 보는 diagnostic이다.
Gold graph는 generation에 들어가지 않고 judge 단계에서만 사용한다.
```

### 3.2 Question and Scope

무엇을 보고 무엇을 보지 않는지 고정한다.

포함할 것:

- 이 실험의 직접 질문
- 이전 실험과 달라진 점
- 현재 실험에서 의도적으로 제외한 것
- online/offline, oracle/non-oracle context 경계

### 3.3 Experimental Design

본문의 technical spine이다. 실험 조건을 이해하는 데 필요한 기술을 짧게 넣는다.

포함할 것:

- dataset / sample slice / turn grain
- model or generation backend
- prompt condition
- current-turn gold가 prompt에 들어가는지 여부
- schema/function docs가 어떻게 들어가는지
- parser/evaluator가 어떤 단위로 동작하는지

넣지 않을 것:

- 전체 파일 경로 목록
- full prompt 전문
- field-by-field output schema

### 3.4 Evaluation Logic

metric과 evaluator를 해석할 수 있게 만드는 section이다.

포함할 것:

- primary metric table
- denominator
- metric이 말하는 것과 말하지 않는 것
- evaluator caveat
- confidence 의미

특히 다음은 본문에 있어야 한다.

```text
candidate coverage가 by construction인지 실제 retrieval 성능인지
strict recall이 executable exactness인지 judge-resolved exactness인지
valid tool name이 gold correctness인지 아닌지
confidence가 correctness probability인지 commit-time token probability인지
```

### 3.5 Results or Result Placeholder

결과가 이미 있으면 primary result를 넣는다. 결과가 아직 없으면 `TBD` table을 두되, 각 table의 source와 계산식을 같이 둔다.

좋은 result placeholder는 단순히 빈칸이 아니라 다음을 포함한다.

| 항목 | 설명 |
|---|---|
| source artifact | 어떤 파일에서 계산하는지 |
| row grain | run / episode / turn / unit / token 중 무엇인지 |
| numerator / denominator | metric 계산식 |
| display format | percent, count, mean 등 |
| interpretation sentence | 값이 높거나 낮을 때 어떻게 해석할지 |

### 3.6 Failure Modes / Case Studies

복잡한 실험에서는 단일 원인보다 failure mode taxonomy가 더 적절할 때가 많다.

대표 case는 다음 mini-template으로 통일한다.

```text
Case:
Gold required:
Model generated:
Failure type:
Metric impact:
Design implication:
```

2-4개만 본문에 둔다. 전체 raw dump는 appendix로 보낸다.

### 3.7 Interpretation Boundaries

보고서의 과해석을 막는 안전장치다.

포함할 것:

- 이 결과가 말하는 것
- 말하지 않는 것
- 비교가 apples-to-apples가 아닌 부분
- 남은 confound
- 결과가 바뀔 수 있는 조건

### 3.8 Reproducibility and Audit Appendix

appendix 이름은 `Technical Appendix`보다 `Reproducibility and Audit Appendix`를 권장한다. 이렇게 해야 appendix가 “모든 기술 내용을 밀어 넣는 곳”이 아니라, 원문 확인과 재현을 위한 곳으로 제한된다.

포함할 것:

- full prompt
- full output schema
- run artifact path
- full config
- full metric tables
- raw examples
- evaluator rubric
- extra comparison tables

## 4. v1에 적용하는 절충안

`think_parallel_v1`은 결과가 이미 있으므로 보고서형 HTML로 만들기 쉽다. 다만 지금 문서는 기술 설명과 결과 설명이 모두 본문에 길게 들어와 있어, HTML에서는 조금 무거울 수 있다.

### 4.1 v1 본문에 유지할 것

- v1은 action recovery diagnostic이고 dependency/parallelism 본 실험이 아니라는 scope
- BFCL v3 `multi_turn_base` 50 samples
- offline full-trajectory planning
- `exact_name_a` mode
- diagnostic override와 `Inputs:` 필드의 의도
- all-hop candidate design
- pairwise judge와 recall denominator
- strict recall과 exact function-name validity의 분리
- parse success, under-generation, recall, hallucinated argument, invalid function-name rate
- 핵심 failure modes
- interpretation caveats

### 4.2 v1 appendix로 보낼 것

- 전체 artifact path
- function doc source file 전체 표
- full prompt 전문
- parser field table
- q1-q4 judge enum 전체
- token confidence field table
- sample별 전체 ranking
- tool별 전체 recall table
- v0 비교 전체 표
- full generated/gold/judge case dump

### 4.3 v1 권장 본문 구조

```text
1. Question and Scope
2. Experimental Setup
3. Evaluation Logic and Caveats
4. Results
5. Failure Mode Analysis
6. Relation to v0
7. Takeaways
8. Reproducibility and Audit Appendix
```

## 5. v2에 적용하는 절충안

`think_parallel_v2`는 현재 결과 보고서라기보다 report scaffold다. 따라서 지금은 full narrative보다, 나중에 결과를 채울 때 오해 없이 계산할 수 있는 구조가 중요하다.

### 5.1 v2 본문에 유지할 것

- v2는 current-turn LLMCompiler-style planning diagnostic이라는 scope
- full episode를 유지하지만 generation은 turn 단위라는 설계
- previous turns는 oracle gold calls/observations
- current-turn gold calls/DAG는 prompt에 들어가지 않는다는 leakage boundary
- `smoke_pre_split`, `smoke_explicit`, `smoke_flat` 세 조건
- explicit `$id` reference와 flat placeholder의 의미 차이
- minimal sufficient actions first, then maximize parallelizability objective
- `format_parse_rate`, valid tool name, schema validity, generated-gold delta, dependency edge, flat reference violation의 정의
- confidence는 commit-time selected-token probability라는 점
- `smoke_flat` output이 아직 없다는 status
- 2-3개의 illustrative case

### 5.2 v2 appendix로 보낼 것

- full parser schema
- output file inventory
- full `token_confidence.jsonl` field table
- full prompt contract bullet list
- condition별 긴 checklist
- result table template 전체
- extra raw generations
- dataset census

### 5.3 v2에 추가하면 좋은 report-production scaffold

v2에는 다음 section이 특히 유용하다.

```text
Run Status Matrix
Artifact Map
Metric Formula Table
Figure Plan
Narrative Template
```

각각의 목적:

| section | 목적 |
|---|---|
| Run Status Matrix | 어떤 condition이 prompt/generation/parse/confidence까지 완료됐는지 표시 |
| Artifact Map | 어떤 파일에서 어떤 table/figure를 계산할지 고정 |
| Metric Formula Table | TBD 결과 표를 채울 때 계산식과 denominator를 고정 |
| Figure Plan | HTML에서 만들 chart와 caption을 미리 정함 |
| Narrative Template | 결과가 들어왔을 때 executive summary와 interpretation을 빠르게 작성 |

## 6. 문서화 파이프라인 스킬화 구상

현재 반복되는 작업은 다음 pipeline으로 정리할 수 있다.

```text
실험 코드 + 실험 결과 + Codex 대화내용
-> evidence map
-> experiment README
-> results digest
-> report-oriented markdown
-> HTML/report
```

이 흐름은 Codex skill로 만들 수 있다. skill의 목적은 “실험 내용을 대신 결론내리는 것”이 아니라, 각 단계의 산출물이 목적에 맞는 문서 구조를 갖도록 돕는 것이다.

### 6.1 Stage 1: Ingest / Evidence Map

입력:

- code files
- output artifacts
- metrics JSON/JSONL
- logs
- conversation summary

출력:

- `evidence_map.md`
- artifact map
- run status matrix
- available metrics list
- missing evidence list
- provenance summary

목적:

```text
무엇이 실제로 존재하는지 먼저 고정한다.
존재하지 않는 결과를 보고서에 쓰지 않게 한다.
각 major claim이 어떤 code/config/result/conversation note에 근거하는지 추적 가능하게 한다.
```

### 6.2 Stage 2: Reconstruct / Experiment README

입력:

- evidence inventory
- experiment intent
- prompt/code inspection

출력:

- `experiment_readme.md`
- 설계 문서 또는 README

포함할 것:

- research question
- comparison arms
- prompt design
- data / leakage boundary
- setup and run matrix, if the document is reproducibility-facing
- metric definitions
- confidence meaning
- illustrative examples
- result placeholders

목적:

```text
미래의 나나 다른 agent가 실험을 오해하지 않도록 한다.
실험이 어떻게 구성됐는지, 어떤 결과가 아직 없는지, 어떤 caveat가 핵심인지 고정한다.
```

### 6.3 Stage 3: Analyze / Results Digest

입력:

- evidence map
- experiment README
- metrics and output artifacts

출력:

- `results_digest.md`

포함할 것:

- primary metrics
- metric deltas
- failed or excluded runs
- baseline/comparison caveats
- notable cases
- uncertainty and missing evidence

목적:

```text
결과를 먼저 neutral하게 정리한다.
아직 report narrative로 과하게 포장하지 않는다.
best run, representative run, failed run, excluded run을 구분한다.
```

### 6.4 Stage 4: Report / Report-Oriented Markdown

입력:

- README / experiment note
- results digest
- filled metrics
- selected case studies

출력:

- `report.md`
- HTML/report로 변환하기 쉬운 Markdown

포함할 것:

- executive summary
- key findings
- compact methods
- primary result tables
- failure mode summary
- interpretation boundaries
- reproducibility appendix

목적:

```text
보고서 독자가 읽는 narrative와 technical accountability를 동시에 만족한다.
```

### 6.5 Stage 5: Polish / Export

입력:

- report-oriented markdown
- figures/tables

출력:

- HTML report
- paper section
- internal update
- blog-style summary
- slides outline

포함할 것:

- title/date/status
- TOC
- result cards
- contrast blocks
- charts
- case study cards
- caveat box

목적:

```text
읽기 쉬운 공유용 산출물로 만든다.
```

### 6.6 Quality Gates

각 stage마다 다음 gate를 통과해야 한다.

| gate | 질문 |
|---|---|
| provenance gate | major claim이 code, config, log, result table, plot, 또는 명시적 user note에 연결되는가? |
| reproducibility gate | README 계열 문서에 data assumptions, run matrix, artifact 위치, 재현 조건이 충분한가? |
| result integrity gate | best run, representative run, failed run, excluded run을 구분했는가? |
| comparison gate | baseline/prior run 이름과 metric directionality가 명확한가? |
| uncertainty gate | missing seeds, small sample, evaluator weakness, noise source를 썼는가? |
| no invention gate | 확인되지 않은 내용은 `TODO` 또는 `Not found`로 남겼는가? |
| audience gate | 내부 연구용, paper용, blog용, executive용 중 문체와 깊이가 맞는가? |
| persona review gate | 서로 다른 reader persona가 claim, 설계, metric, narrative를 독립적으로 검토했는가? |

특히 `no invention gate`가 중요하다. Codex가 plausible한 내용을 채우면 문서가 매끈해져도 연구 기록으로는 위험해진다.

### 6.7 Stage 6: Persona Review / Subagent Quality Review

보고서 초안이 만들어진 뒤에는 별도의 quality review pass를 둔다. 이 단계의 목적은 문장을 polish하는 것이 아니라, 문서가 서로 다른 독자에게 어떻게 읽히는지 확인하고 claim strength, 실험 설계, metric validity, evidence-to-claim alignment를 점검하는 것이다.

이 단계는 특히 report-oriented Markdown 이후, HTML/report로 export하기 전에 수행한다. 결과가 새로 추가되거나 주요 claim이 바뀌었을 때도 다시 수행한다.

권장 방식은 2-4개의 subagent를 서로 다른 persona로 호출하고, 각 subagent가 같은 문서를 독립적으로 읽게 하는 것이다. 각 persona는 다음처럼 역할을 좁힌다.

| persona | 주요 질문 | 산출물 |
|---|---|---|
| 처음 보는 교수 독자 | 프로젝트 맥락을 모르는 독자가 research question, contribution, limitation을 2분 안에 이해할 수 있는가? | first-read summary, confusion points, missing scaffolding |
| 실험설계자 / methodologist | 비교 조건, leakage boundary, denominator, control, reproducibility가 공정하고 명확한가? | design risks, metric validity concerns, missing controls |
| skeptical reviewer | evidence보다 강한 claim, baseline ambiguity, evaluator weakness, anecdotal case overuse가 있는가? | overclaim risks, reviewer objections, required evidence |
| implementation auditor | code/config/artifact/metric이 문서의 claim과 일치하는가? | provenance gaps, artifact mismatch, calculation check |
| report editor | 본문 흐름, figure/table caption, case study 배치가 독자의 판단을 돕는가? | narrative edits, section ordering suggestions |

모든 문서에 모든 persona가 필요한 것은 아니다. 빠른 내부 업데이트는 “처음 보는 교수 독자 + skeptical reviewer” 정도로 충분하다. 논문 section, 외부 공유 HTML, 복잡한 비교 실험은 “처음 보는 교수 독자 + 실험설계자 + skeptical reviewer + implementation auditor” 조합을 기본값으로 둔다.

subagent 요청은 다음 template을 사용한다.

```text
Read this experiment report as [persona].

Focus on:
- claim clarity
- evidence-to-claim alignment
- metric denominator and caveats
- leakage / baseline / evaluator validity
- reader confusion points

Do not rewrite the whole report.
Return:
1. Three-sentence reconstruction of the report's claim
2. Main confusion points
3. Validity or overclaim risks
4. Missing evidence or missing explanation
5. Concrete section-level edit suggestions
```

review 결과를 통합할 때는 다수결로 고치지 않는다. 다음 원칙을 적용한다.

```text
반드시 반영:
  artifact mismatch, metric denominator 오류, leakage boundary 누락, evidence보다 강한 claim.

선택적으로 반영:
  문체 선호, section 순서, case study 개수, figure caption 표현.

반영하지 않을 수 있음:
  persona의 목적과 맞지 않는 과도한 요구, 현재 stage에서 의도적으로 비워둔 결과 요구.
```

최종 문서에는 review pass 자체를 길게 남길 필요는 없다. 다만 내부 작업 기록에는 다음을 남긴다.

```text
Persona review performed:
- first-time professor reader: done / skipped
- experiment designer: done / skipped
- skeptical reviewer: done / skipped
- implementation auditor: done / skipped

Major changes from review:
- ...

Known unresolved review concerns:
- ...
```

## 7. Skill 설계 초안

스킬 이름 후보:

```text
experiment-report-pipeline
```

trigger description 초안:

```text
Use when turning ML/research experiment code, results, logs, or Codex conversation history into structured experiment notes, README documentation, report-oriented Markdown, or HTML-ready report plans. Helps separate main-body technical spine from reproducibility/audit appendix, define metric formulas, artifact maps, result placeholders, and case-study templates.
```

필수 workflow:

```text
1. Ground in artifacts
2. Identify document stage: evidence_map, README, results_digest, report, or export
3. Build or update artifact map and run status matrix
4. Decide main body vs appendix using argumentative-necessity criteria
5. Define metrics with source, grain, numerator, denominator, and display format
6. Separate illustrative examples from final results
7. Mark unknowns as TODO / Not found instead of inventing
8. Produce stage-appropriate Markdown
9. Run persona review pass when the target is report-md, HTML, paper text, or external-facing documentation
10. Validate with quality gates
```

스킬에 포함할 reference 파일 후보:

| file | 내용 |
|---|---|
| `references/stages.md` | Evidence inventory, README, report-md, HTML 단계별 목적 |
| `references/main-vs-appendix.md` | 본문과 appendix 분리 기준 |
| `references/templates.md` | summary, artifact map, metric table, case study template |
| `references/claim-language.md` | cautious claim, negative result, limitation 표현 |
| `references/review-checklist.md` | reproducibility, overclaiming, no-invention 점검 |
| `references/persona-review-prompts.md` | 교수 독자, 실험설계자, skeptical reviewer, implementation auditor용 subagent prompt |

SKILL.md에는 짧은 workflow만 두고, 상세 template은 references로 분리하는 것이 좋다.

초기에는 script를 넣지 않는 편이 좋다. artifact format이 안정되기 전에는 workflow와 checklist 중심 skill이 더 유연하다. 반복적으로 같은 JSONL/CSV/WandB/MLflow 추출을 하게 되면 그때 deterministic script를 추가한다.

## 8. 결과가 나온 뒤 한 번에 정리하는 것이 나은가?

대체로 그렇다. 다만 “한 번에 정리”가 잘 되려면 지금처럼 결과 전 문서화가 필요하다.

권장 방식:

```text
결과 전:
  scope, prompt, metric, artifact map, placeholder, caveat를 문서화한다.

결과 직후:
  metrics를 채우고, notable cases를 고르고, failure mode를 확정한다.

보고서 작성 시:
  결과와 해석을 한 번에 정리한다.
```

즉 결과가 나오기 전에는 결론을 쓰지 않는다. 대신 결과가 들어갈 그릇을 정확히 만든다. 결과가 나온 뒤에는 metric table, failure mode, interpretation을 한 번에 정리하는 것이 가장 효율적이다.

## 9. 체크리스트

문서를 만들거나 수정할 때 마지막에 다음을 확인한다.

```text
[ ] 이 문서의 stage가 명확한가? README인가, report-md인가, HTML plan인가?
[ ] 실제 존재하는 artifact와 아직 없는 artifact를 구분했는가?
[ ] current gold / graph / observation의 prompt 포함 여부를 명시했는가?
[ ] primary metric의 denominator를 썼는가?
[ ] confidence가 무엇을 의미하는지 썼는가?
[ ] illustrative example과 final result를 분리했는가?
[ ] 중요한 technical caveat가 appendix로 밀려나지 않았는가?
[ ] appendix는 reproducibility/audit 목적에 한정되어 있는가?
[ ] 결과가 비어 있다면 TBD table의 source와 formula가 있는가?
[ ] 외부 공유 또는 report-md라면 persona review pass를 수행했는가?
[ ] persona review에서 나온 artifact mismatch, metric 오류, overclaim 위험을 처리했는가?
```
