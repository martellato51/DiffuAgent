# BFCL v3 LLaDA2.1-mini Score Analysis

Date: 2026-05-13 UTC

## Scope

분석 대상은 아래 score root에서 `llada21_v3`로 시작하는 3개 run이다.

```text
/home/ilju/research/DiffuAgent/unified_envs/gorilla_bfcl_v3/berkeley-function-call-leaderboard/score
```

| Run | Meaning |
|---|---|
| `llada21_v3_baseline_st_20260513_164710` | baseline prompt serialization, legacy AST decoder |
| `llada21_v3_json_st_20260513_181201` | JSON prompt serialization, legacy AST decoder |
| `llada21_v3_json_st_20260513_181201_v4_decoder` | same raw output as `181201`, re-evaluated with v4 decoder |

분석 category는 single-turn 10개 subset이다.

```text
simple,multiple,parallel,parallel_multiple,java,javascript,
live_simple,live_multiple,live_parallel,live_parallel_multiple
```

아래의 main score는 각 `BFCL_v3_<category>_score.json` 첫 줄의
`correct_count`와 `total_count`를 직접 합산한 값이다. BFCL의
`data_overall.csv` 값은 별도 leaderboard summary 포맷이라서 함께 적되,
10개 subset 직접 합산과는 구분해서 본다.

## Summary

| Run | Direct Score | Non-Live | Live | Macro Avg. | CSV Overall |
|---|---:|---:|---:|---:|---:|
| `baseline_164710` | 80 / 440, 18.18% | 60 / 300, 20.00% | 20 / 140, 14.29% | 17.28% | 4.02% |
| `json_181201` | 18 / 440, 4.09% | 12 / 300, 4.00% | 6 / 140, 4.29% | 3.60% | 0.81% |
| `json_181201_v4_decoder` | 18 / 440, 4.09% | 12 / 300, 4.00% | 6 / 140, 4.29% | 3.60% | 0.81% |

결론부터 보면 현재 best는 `baseline_164710`이다. JSON prompt serialization은
baseline보다 직접 합산 기준으로 `62/440`, 즉 14.09 percentage point 낮다.
같은 JSON raw output을 v4 decoder로 재채점해도 점수 변화는 없었다.

## Category Scores

### `llada21_v3_baseline_st_20260513_164710`

| Category | Correct / Total | Accuracy |
|---|---:|---:|
| simple | 37 / 50 | 74.00% |
| multiple | 1 / 50 | 2.00% |
| parallel | 7 / 50 | 14.00% |
| parallel_multiple | 0 / 50 | 0.00% |
| java | 9 / 50 | 18.00% |
| javascript | 6 / 50 | 12.00% |
| live_simple | 17 / 50 | 34.00% |
| live_multiple | 0 / 50 | 0.00% |
| live_parallel | 3 / 16 | 18.75% |
| live_parallel_multiple | 0 / 24 | 0.00% |

### `llada21_v3_json_st_20260513_181201`

| Category | Correct / Total | Accuracy |
|---|---:|---:|
| simple | 10 / 50 | 20.00% |
| multiple | 0 / 50 | 0.00% |
| parallel | 1 / 50 | 2.00% |
| parallel_multiple | 0 / 50 | 0.00% |
| java | 0 / 50 | 0.00% |
| javascript | 1 / 50 | 2.00% |
| live_simple | 6 / 50 | 12.00% |
| live_multiple | 0 / 50 | 0.00% |
| live_parallel | 0 / 16 | 0.00% |
| live_parallel_multiple | 0 / 24 | 0.00% |

### `llada21_v3_json_st_20260513_181201_v4_decoder`

| Category | Correct / Total | Accuracy |
|---|---:|---:|
| simple | 10 / 50 | 20.00% |
| multiple | 0 / 50 | 0.00% |
| parallel | 1 / 50 | 2.00% |
| parallel_multiple | 0 / 50 | 0.00% |
| java | 0 / 50 | 0.00% |
| javascript | 1 / 50 | 2.00% |
| live_simple | 6 / 50 | 12.00% |
| live_multiple | 0 / 50 | 0.00% |
| live_parallel | 0 / 16 | 0.00% |
| live_parallel_multiple | 0 / 24 | 0.00% |

## Failure Pattern

실패 패턴은 score JSON 첫 줄 summary 이후의 failed case들을 기준으로 집계했다.

### Error Types

| Run | Main Failure Types |
|---|---|
| `baseline_164710` | `ast_decoder:decoder_failed` 329, `ast_decoder:decoder_wrong_output_format` 16, `simple_function_checker:wrong_func_name` 5, `type_error:simple` 4 |
| `json_181201` | `ast_decoder:decoder_failed` 411, `ast_decoder:decoder_wrong_output_format` 9, `simple_function_checker:wrong_func_name` 1, `type_error:simple` 1 |
| `json_181201_v4_decoder` | `ast_decoder:decoder_failed` 410, `ast_decoder:decoder_wrong_output_format` 9, `simple_function_checker:wrong_func_name` 1, `simple_function_checker:wrong_count` 1, `type_error:simple` 1 |

### Raw Output Shape in Failed Cases

| Run | Natural/code-like | JSON object | Call-like text | JSON array/list | Fenced JSON/code |
|---|---:|---:|---:|---:|---:|
| `baseline_164710` | 229 | 76 | 23 | 21 | 11 |
| `json_181201` | 282 | 109 | 12 | 6 | 13 |
| `json_181201_v4_decoder` | 282 | 109 | 12 | 6 | 13 |

baseline도 실패 대부분이 parser/decoder 단계에서 깨진다. 그래도 JSON run보다
call-like text와 JSON array/list 형태가 더 많고, 이 차이가 `simple`과
일부 live/non-live category 점수 차이로 이어진 것으로 보인다.

## Interpretation

현재 3개 score만 보면 LLaDA2.1-mini v3 single-turn은 baseline prompt
serialization이 가장 낫다. `simple`은 74%까지 나오므로 모델과 wrapper가
완전히 실패하는 상태는 아니다. 하지만 `multiple`, `parallel_multiple`,
`live_multiple`, `live_parallel_multiple`은 거의 0점이라 여러 호출을
안정적인 BFCL call list 형태로 내는 능력 또는 prompting이 병목이다.

JSON prompt serialization은 기대와 반대로 성능을 떨어뜨렸다. 실패 출력에
JSON object가 많지만 BFCL v3 AST decoder가 기대하는 call syntax와 맞지 않아
대부분 `ast_decoder`에서 떨어진다. 또한 같은 raw output을 v4 decoder로
재채점해도 `18/440` 그대로였으므로, 이 실험에서는 decoder 교체만으로는
해결되지 않았다.

## Next Steps

1. 후속 LLaDA2.1 v3 single-turn 실험의 기본 비교 기준은 `baseline_164710`으로 둔다.
2. baseline raw output을 v4 decoder로도 재채점해 decoder 효과가 있는지 따로 확인한다.
3. `multiple`과 `parallel_multiple` 실패 샘플을 먼저 본다. 단일 호출보다 다중 호출 format이 핵심 병목으로 보인다.
4. JSON object를 BFCL call syntax로 바꾸는 postprocessor는 가능하지만, 적용 시 별도 run으로 분리해 기록한다.

