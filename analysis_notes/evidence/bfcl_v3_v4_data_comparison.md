# BFCL v3 vs v4 Data Comparison

Date: 2026-05-12

## Purpose

This note checks whether the BFCL v3 and v4 single-turn data differ only by category/schema naming, or whether the actual task contents also changed.

Compared roots:

```text
v3: /home/ilju/research/bfcl_v3_ea13468/berkeley-function-call-leaderboard/bfcl_eval/data
v4: /home/ilju/research/DiffuAgent/unified_envs/gorilla/berkeley-function-call-leaderboard/bfcl_eval/data
```

## Category Mapping

The comparison uses these v3-to-v4 category mappings:

```text
v3 simple      <-> v4 simple_python
v3 java        <-> v4 simple_java
v3 javascript  <-> v4 simple_javascript

same category name:
multiple
parallel
parallel_multiple
live_simple
live_multiple
live_parallel
live_parallel_multiple
```

For the renamed categories, ids were canonicalized before comparison:

```text
v4 simple_python_0       -> v3 simple_0
v4 simple_java_0         -> v3 java_0
v4 simple_javascript_0   -> v3 javascript_0
```

## Code Used

### Main Data Comparison

This script compares `question`, `function`, and the full entry excluding `id`.

```python
import json
from pathlib import Path

root3 = Path("/home/ilju/research/bfcl_v3_ea13468/berkeley-function-call-leaderboard/bfcl_eval/data")
root4 = Path("/home/ilju/research/DiffuAgent/unified_envs/gorilla/berkeley-function-call-leaderboard/bfcl_eval/data")

pairs = {
    "simple": "simple_python",
    "java": "simple_java",
    "javascript": "simple_javascript",
    "multiple": "multiple",
    "parallel": "parallel",
    "parallel_multiple": "parallel_multiple",
    "live_simple": "live_simple",
    "live_multiple": "live_multiple",
    "live_parallel": "live_parallel",
    "live_parallel_multiple": "live_parallel_multiple",
}

def load(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]

def canon_id(id_, cat3, cat4, direction):
    if direction == "v3to4":
        if cat3 == "simple":
            return id_.replace("simple_", "simple_python_", 1)
        if cat3 == "java":
            return id_.replace("java_", "simple_java_", 1)
        if cat3 == "javascript":
            return id_.replace("javascript_", "simple_javascript_", 1)
    if direction == "v4to3":
        if cat4 == "simple_python":
            return id_.replace("simple_python_", "simple_", 1)
        if cat4 == "simple_java":
            return id_.replace("simple_java_", "java_", 1)
        if cat4 == "simple_javascript":
            return id_.replace("simple_javascript_", "javascript_", 1)
    return id_

def strip_id(entry):
    copied = json.loads(json.dumps(entry, sort_keys=True))
    copied.pop("id", None)
    return copied

for cat3, cat4 in pairs.items():
    f3 = root3 / f"BFCL_v3_{cat3}.json"
    f4 = root4 / f"BFCL_v4_{cat4}.json"
    if not f3.exists() or not f4.exists():
        print(cat3, "missing")
        continue

    v3_rows = load(f3)
    v4_rows = load(f4)
    v4_by_v3_id = {
        canon_id(row["id"], cat3, cat4, "v4to3"): row
        for row in v4_rows
    }

    common = []
    same_question = 0
    same_function = 0
    same_entry_excluding_id = 0
    samples = []

    for row3 in v3_rows:
        row4 = v4_by_v3_id.get(row3["id"])
        if row4 is None:
            continue

        common.append(row3["id"])
        question_equal = row3.get("question") == row4.get("question")
        function_equal = row3.get("function") == row4.get("function")
        entry_equal = strip_id(row3) == strip_id(row4)

        same_question += question_equal
        same_function += function_equal
        same_entry_excluding_id += entry_equal

        if (not question_equal or not function_equal) and len(samples) < 3:
            samples.append((row3["id"], question_equal, function_equal, row3, row4))

    total = len(common)
    print()
    print(f"{cat3:24s} <-> {cat4:24s} v3_n={len(v3_rows)} v4_n={len(v4_rows)} common={total}")
    print(f"  same question: {same_question}/{total} ({same_question / total * 100 if total else 0:.1f}%)")
    print(f"  same function schema: {same_function}/{total} ({same_function / total * 100 if total else 0:.1f}%)")
    print(f"  same entry excluding id: {same_entry_excluding_id}/{total} ({same_entry_excluding_id / total * 100 if total else 0:.1f}%)")

    for sample_id, question_equal, function_equal, row3, row4 in samples:
        print("  sample", sample_id, "qeq=", question_equal, "feq=", function_equal)
        if not question_equal:
            print("    q3=", row3.get("question"))
            print("    q4=", row4.get("question"))
        if not function_equal:
            print("    f3=", row3.get("function"))
            print("    f4=", row4.get("function"))
```

### Possible Answer Comparison

This script compares `possible_answer/BFCL_v*_*.json`, again ignoring only the id rename.

```python
import json
from pathlib import Path

root3 = Path("/home/ilju/research/bfcl_v3_ea13468/berkeley-function-call-leaderboard/bfcl_eval/data")
root4 = Path("/home/ilju/research/DiffuAgent/unified_envs/gorilla/berkeley-function-call-leaderboard/bfcl_eval/data")

pairs = {
    "simple": "simple_python",
    "java": "simple_java",
    "javascript": "simple_javascript",
    "multiple": "multiple",
    "parallel": "parallel",
    "parallel_multiple": "parallel_multiple",
    "live_simple": "live_simple",
    "live_multiple": "live_multiple",
    "live_parallel": "live_parallel",
    "live_parallel_multiple": "live_parallel_multiple",
}

def load(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]

def canon_v4_to_v3(id_, cat4):
    if cat4 == "simple_python":
        return id_.replace("simple_python_", "simple_", 1)
    if cat4 == "simple_java":
        return id_.replace("simple_java_", "java_", 1)
    if cat4 == "simple_javascript":
        return id_.replace("simple_javascript_", "javascript_", 1)
    return id_

def strip_id(entry):
    copied = json.loads(json.dumps(entry, sort_keys=True))
    copied.pop("id", None)
    return copied

for cat3, cat4 in pairs.items():
    p3 = root3 / "possible_answer" / f"BFCL_v3_{cat3}.json"
    p4 = root4 / "possible_answer" / f"BFCL_v4_{cat4}.json"
    if not p3.exists() or not p4.exists():
        print(cat3, "missing possible_answer")
        continue

    v3_rows = load(p3)
    v4_rows = load(p4)
    v4_by_v3_id = {canon_v4_to_v3(row["id"], cat4): row for row in v4_rows}

    common = 0
    same = 0
    samples = []
    for row3 in v3_rows:
        row4 = v4_by_v3_id.get(row3["id"])
        if row4 is None:
            continue
        common += 1
        equal = strip_id(row3) == strip_id(row4)
        same += equal
        if not equal and len(samples) < 2:
            samples.append((row3["id"], row3, row4))

    print(f"{cat3:24s} PA v3_n={len(v3_rows)} v4_n={len(v4_rows)} common={common} same={same}/{common} ({same / common * 100 if common else 0:.1f}%)")
    for sample_id, row3, row4 in samples:
        print("  sample", sample_id)
        print("    v3", row3)
        print("    v4", row4)
```

## Result: Main Data

| v3 category | v4 category | v3 n | v4 n | common | same question | same function schema | same entry excluding id |
|---|---|---:|---:|---:|---:|---:|---:|
| simple | simple_python | 400 | 400 | 400 | 400/400, 100.0% | 400/400, 100.0% | 400/400, 100.0% |
| java | simple_java | 100 | 100 | 100 | 100/100, 100.0% | 100/100, 100.0% | 100/100, 100.0% |
| javascript | simple_javascript | 50 | 50 | 50 | 50/50, 100.0% | 50/50, 100.0% | 50/50, 100.0% |
| multiple | multiple | 200 | 200 | 200 | 200/200, 100.0% | 200/200, 100.0% | 200/200, 100.0% |
| parallel | parallel | 200 | 200 | 200 | 198/200, 99.0% | 200/200, 100.0% | 198/200, 99.0% |
| parallel_multiple | parallel_multiple | 200 | 200 | 200 | 200/200, 100.0% | 200/200, 100.0% | 200/200, 100.0% |
| live_simple | live_simple | 258 | 258 | 258 | 256/258, 99.2% | 258/258, 100.0% | 256/258, 99.2% |
| live_multiple | live_multiple | 1053 | 1053 | 1053 | 1052/1053, 99.9% | 1053/1053, 100.0% | 1052/1053, 99.9% |
| live_parallel | live_parallel | 16 | 16 | 16 | 16/16, 100.0% | 16/16, 100.0% | 16/16, 100.0% |
| live_parallel_multiple | live_parallel_multiple | 24 | 24 | 24 | 24/24, 100.0% | 24/24, 100.0% | 24/24, 100.0% |

Key observation:

```text
Function schema is identical for every matched id in all compared categories.
Actual question text differs only in a small number of ids.
```

## Result: Possible Answer

| v3 category | v4 category | v3 n | v4 n | common | same possible answer |
|---|---|---:|---:|---:|---:|
| simple | simple_python | 400 | 400 | 400 | 399/400, 99.8% |
| java | simple_java | 100 | 100 | 100 | 100/100, 100.0% |
| javascript | simple_javascript | 50 | 50 | 50 | 49/50, 98.0% |
| multiple | multiple | 200 | 200 | 200 | 200/200, 100.0% |
| parallel | parallel | 200 | 200 | 200 | 198/200, 99.0% |
| parallel_multiple | parallel_multiple | 200 | 200 | 200 | 200/200, 100.0% |
| live_simple | live_simple | 258 | 258 | 258 | 255/258, 98.8% |
| live_multiple | live_multiple | 1053 | 1053 | 1053 | 1053/1053, 100.0% |
| live_parallel | live_parallel | 16 | 16 | 16 | 15/16, 93.8% |
| live_parallel_multiple | live_parallel_multiple | 24 | 24 | 24 | 24/24, 100.0% |

## Exception Cases

### Main Data: Question Text Differences

#### `parallel_84`

Function schema is identical, but the user question differs.

v3:

```json
[[{"role": "user", "content": "\"A car starts from rest and accelerates uniformly over a time of 5.2 seconds for a distance of 110 m. Determine the acceleration of the car. Then, another car with an initial velocity of 15 m/s accelerates at a rate of 3.5 m/s^2 for a time of 7 seconds. What is the displacement of the second car? Now, consider a third car that starts with an initial velocity of 20 m/s and accelerates at a rate of 2 m/s^2 for a time of 10 seconds. What is the displacement of the third car? Finally, a fourth car with an initial velocity of 25 m/s travels for a time of 8 seconds without any acceleration. What is the displacement of the fourth car?\""}]]
```

v4:

```json
[[{"role": "user", "content": "\"A car starts with an initial velocity of 15 m/s accelerates at a rate of 3.5 m/s^2 for a time of 7 seconds. What is the displacement of this car? Now, consider a second car that starts with an initial velocity of 20 m/s and accelerates at a rate of 2 m/s^2 for a time of 10 seconds. What is the displacement of the second car? Finally, a third car with an initial velocity of 25 m/s travels for a time of 8 seconds without any acceleration. What is the displacement of the third car?\""}]]
```

#### `parallel_170`

Function schema is identical, but the user question differs.

v3:

```json
[[{"role": "user", "content": "\"Can you help me calculate the compound interest for my savings? I initially invested $5000 as the principal amount. The bank offers an annual interest rate of 2.5% (or 0.025 in decimal form). I plan to keep my money in the bank for 10 years. Also, the interest is compounded quarterly, so it's compounded 4 times in a year. Can you calculate the compound interest for the first 2 years, then for the next 3 years and finally for the remaining 5 years?\""}]]
```

v4:

```json
[[{"role": "user", "content": "\"Can you help me calculate the compound interest for my savings? I initially invested $5000 as the principal amount. The bank offers an annual interest rate of 2.5%. I plan to keep my money in the bank for 10 years. Also, the interest is compounded quarterly, so it's compounded 4 times in a year. Can you calculate the compound interest I would get for the first 2 years, first 3 years and first 5 years?\""}]]
```

#### `live_simple_137-90-0`

Function schema is identical, but the user question differs.

v3:

```json
[[{"role": "user", "content": "Reschedule event 'Alice-One-one-One' to November 1, 2023 at 10pm CEST"}]]
```

v4:

```json
[[{"role": "user", "content": "Reschedule event 'Alice-One-one-One' to November 1, 2023 at 8pm London time"}]]
```

#### `live_simple_138-91-0`

Function schema is identical, but the user question differs.

v3:

```json
[[{"role": "user", "content": "Reschedule event 'Bob-123' to November 1, 2023 at 6pm CEST"}]]
```

v4:

```json
[[{"role": "user", "content": "Reschedule event 'Bob-123' to November 1, 2023 at 4pm London time"}]]
```

#### `live_multiple_44-17-0`

Function schema is identical, but the user question differs.

v3:

```json
[[{"role": "user", "content": "Can you provide an overview of my business checking account at U.S. Bank for the statement period from October 1, 2019, to October 31, 2019? The account number is 1-523-1713-5704, and it's under the name SILVER BUSINESS CHECKING. The beginning balance was $5,532.01, and the ending balance was $6,737.37. There were other deposits totaling $7,132.76 and withdrawals amounting to $5,927.40. Could you also include a summary of transactions for this period?"}]]
```

v4:

```json
[[{"role": "user", "content": "Can you provide an overview of my business checking account at U.S. Bank for the statement period from October 1, 2019, to October 31, 2019? The account number is 1-523-1713-5704, and it's under the name SILVER BUSINESS CHECKING. The beginning balance was $5,532.01, and the ending balance was $6,737.37. There were other deposits totaling $7,132.76 and withdrawals amounting to $5,927.40."}]]
```

### Possible Answer Differences

#### `simple_363`

v3:

```json
{"id": "simple_363", "ground_truth": [{"find_closest": {"location": ["Boston", "Boston, MA"], "cuisine": ["Sushi", "sushi"], "amenities": [["Patio"]]}}]}
```

v4:

```json
{"id": "simple_python_363", "ground_truth": [{"restaurant_search.find_closest": {"location": ["Boston", "Boston, MA"], "cuisine": ["Sushi", "sushi"], "amenities": [["Patio"]]}}]}
```

#### `javascript_41`

v3:

```json
{"id": "javascript_41", "ground_truth": [{"queue": {"worker": ["myWorkerFunction"], "concurrency": [5.0], "payload": ["", 0.0]}}]}
```

v4:

```json
{"id": "simple_javascript_41", "ground_truth": [{"queue_1": {"worker": ["myWorkerFunction"], "concurrency": [5.0], "payload": ["", 0.0]}}]}
```

#### `parallel_155`

v3:

```json
{"id": "parallel_155", "ground_truth": [{"run_linear_regression": {"predictors": [["Age", "Income", "Education"]], "target": ["Spending Score"], "standardize": [false]}}, {"run_linear_regression": {"predictors": [["Age", "Income", "Education"]], "target": ["Spending Score"], "standardize": [true, false]}}]}
```

v4:

```json
{"id": "parallel_155", "ground_truth": [{"run_linear_regression": {"predictors": [["Age", "Income", "Education"]], "target": ["Spending Score"], "standardize": [false]}}, {"run_linear_regression": {"predictors": [["Age", "Income", "Education"]], "target": ["Spending Score"], "standardize": [true]}}]}
```

#### `parallel_158`

v3:

```json
{"id": "parallel_158", "ground_truth": [{"random.normalvariate": {"mu": [5], "sigma": [2]}}, {"random.normalvariate": {"mu": [10], "sigma": [3]}}]}
```

v4:

```json
{"id": "parallel_158", "ground_truth": [{"random.normalvariate": {"mu": [5], "sigma": [2]}}, {"random.normalvariate": {"mu": [5], "sigma": [2]}}, {"random.normalvariate": {"mu": [10], "sigma": [3]}}, {"random.normalvariate": {"mu": [10], "sigma": [3]}}]}
```

#### `live_simple_137-90-0`

v3:

```json
{"id": "live_simple_137-90-0", "ground_truth": [{"reschedule": {"identifier": ["Alice-One-one-One"], "dateOrTime": ["2023-11-01T22:00:00"], "timezone": ["Europe/London"]}}]}
```

v4:

```json
{"id": "live_simple_137-90-0", "ground_truth": [{"reschedule": {"identifier": ["Alice-One-one-One"], "dateOrTime": ["2023-11-01T20:00:00"], "timezone": ["Europe/London"]}}]}
```

#### `live_simple_138-91-0`

v3:

```json
{"id": "live_simple_138-91-0", "ground_truth": [{"reschedule": {"identifier": ["Bob-123"], "dateOrTime": ["2023-11-01T18:00:00"], "timezone": ["Europe/London"]}}]}
```

v4:

```json
{"id": "live_simple_138-91-0", "ground_truth": [{"reschedule": {"identifier": ["Bob-123"], "dateOrTime": ["2023-11-01T16:00:00"], "timezone": ["Europe/London"]}}]}
```

#### `live_parallel_9-5-0`

v3:

```json
{"id": "live_parallel_9-5-0", "ground_truth": [{"get_aws_pricing": {"memory": [2], "cpu": ["single"], "region": ["", "us-east-1"], "operating_system0": ["", "Linux"]}}, {"get_aws_pricing": {"memory": [4], "cpu": ["single"], "region": ["", "us-east-1"], "operating_system0": ["", "Linux"]}}]}
```

v4:

```json
{"id": "live_parallel_9-5-0", "ground_truth": [{"get_aws_pricing": {"memory": [2], "cpu": ["single"], "region": ["", "us-east-1"], "operating_system": ["", "Linux"]}}, {"get_aws_pricing": {"memory": [4], "cpu": ["single"], "region": ["", "us-east-1"], "operating_system": ["", "Linux"]}}]}
```

## Interpretation

The compared v3/v4 datasets are mostly identical after category/id canonicalization.

The strongest finding is:

```text
Function schema is 100% identical for all matched ids in the compared single-turn categories.
```

Therefore, a large LLaDA score difference between v3 and v4 is unlikely to be explained by broad schema changes in the dataset.

Actual data content changes do exist, but they are sparse:

```text
parallel:        2/200 question differences, 2/200 possible-answer differences
live_simple:     2/258 question differences, 3/258 possible-answer differences
live_multiple:   1/1053 question difference, 0 possible-answer differences
live_parallel:   0/16 question differences, 1/16 possible-answer difference
simple:          0/400 question differences, 1/400 possible-answer difference
javascript:      0/50 question differences, 1/50 possible-answer difference
```

This means v3/v4 score differences should be investigated primarily in runtime and prompting conditions:

```text
1. LLaDA generation precision/runtime, especially float64 vs float32 confidence softmax.
2. Prompt stack and handler path differences.
3. Output format distribution: func(arg=value) vs func({"arg": value}).
4. A small number of id-level data/ground-truth exceptions.
```

## Follow-Up Findings From Later Runs

After the initial data comparison, several candidate explanations were tested or ruled down.

### Candidate: Fast-dLLM float32 vs float64

Fast-dLLM's LLaDA confidence softmax had been changed from `float64` to `float32` in:

```text
/home/ilju/research/Fast-dLLM/v1/llada/generate.py
/home/ilju/research/Fast-dLLM/v1/llada/app.py
```

Those changes were reverted so that Fast-dLLM had no local diff. A new v3 single-turn run was then executed:

```text
log:    /home/ilju/research/logs/run_bfcl_llada_singleturn_20260512_131601.log
result: /home/ilju/research/bfcl_v3_ea13468/berkeley-function-call-leaderboard/result/llada_st_20260512_041601
score:  /home/ilju/research/bfcl_v3_ea13468/berkeley-function-call-leaderboard/score/llada_st_20260512_041601
```

Result:

```text
Accuracy did not change.
Raw model outputs did not change for any of the 440 matched single-turn subset entries.
Only latency changed.
```

Therefore, for this subset/run, `float32` vs `float64` Fast-dLLM confidence softmax is not the observed cause of the v3/v4 score gap.

### Candidate: v3 Shim Query/Cleanup Path

The v3 compatibility handler was adjusted to more closely match v4-style query/cleanup behavior:

```text
/home/ilju/research/bfcl_v3_ea13468/berkeley-function-call-leaderboard/bfcl_eval/model_handler/api_inference/diffuagent/handlers_backbone.py
```

The adjusted run was:

```text
result: /home/ilju/research/bfcl_v3_ea13468/berkeley-function-call-leaderboard/result/llada_st_20260512_035704
score:  /home/ilju/research/bfcl_v3_ea13468/berkeley-function-call-leaderboard/score/llada_st_20260512_035704
```

Result:

```text
Accuracy did not change.
Raw model outputs did not change relative to the earlier v3 run.
```

Therefore, the v3 shim's query/cleanup path is unlikely to be the main cause of the observed v3/v4 difference.

### Remaining Strong Hypothesis: Function-Doc Serialization In The Prompt

The remaining strong difference is how each checkout serializes the same function docs into the system prompt.

v3 inserts the post-processed Python object directly into the prompt via string formatting:

```text
Here is a list of functions in JSON format that you can invoke.
[{'name': 'validateUserInput', 'description': '...', 'parameters': {'type': 'dict', ...}}]
```

Despite the wording "JSON format", this is Python `repr`-style text:

```text
single quotes
Python dict/list literal syntax
compact one-line object representation
```

v4 uses `json.dumps(functions, indent=4)` through its prompt-stack utilities:

```json
[
    {
        "name": "validateUserInput",
        "description": "...",
        "parameters": {
            "type": "dict"
        }
    }
]
```

This is valid, pretty-printed JSON:

```text
double quotes
JSON object syntax
multi-line indentation
clearer separation between function documentation and required output call syntax
```

This matters because the v3 prompt repeatedly exposes the model to Python dict literal patterns like:

```python
{'parameters': {'type': 'dict', ...}}
```

The v3 LLaDA raw outputs then frequently imitate that shape in arguments:

```python
function({'arg': value})
```

BFCL's AST decoder expects keyword-argument style:

```python
function(arg=value)
```

and does not unpack a positional dict/object argument into named parameters. This causes many decoded calls to become:

```python
{"function": {}}
```

which then produces `Missing required parameter` errors.

### Raw Output Pattern Evidence

Across the matched 440 single-turn subset entries:

| Pattern | v3 | v4 |
|---|---:|---:|
| `func({"arg": ...})` / positional dict style | 232/440 | 65/440 |
| `func(arg=...)` / keyword style | 186/440 | 334/440 |

Category-level examples:

| Category | v3 dict-style | v4 dict-style | v3 keyword-style | v4 keyword-style |
|---|---:|---:|---:|---:|
| simple | 30/50 | 0/50 | 22/50 | 50/50 |
| javascript | 30/50 | 3/50 | 17/50 | 45/50 |
| parallel | 42/50 | 17/50 | 6/50 | 28/50 |
| live_simple | 36/50 | 13/50 | 9/50 | 37/50 |
| live_parallel | 16/16 | 1/16 | 0/16 | 15/16 |

### Current Interpretation

The v3/v4 score gap is now most plausibly explained by prompt serialization, not by dataset schema, decoder differences, or Fast-dLLM precision.

More specifically:

```text
The same function schema is shown to LLaDA in different textual forms.
v3 shows Python repr-style dict/list text.
v4 shows valid pretty JSON.
LLaDA appears to imitate v3's dict literal shape in generated function arguments.
BFCL's decoder cannot interpret that positional dict as named parameters.
The resulting decoded output loses arguments and fails with Missing required parameter.
```

The next verification experiment should change only v3's function-doc serialization to match v4's `json.dumps(function_docs, indent=4)` behavior and then re-run the same single-turn subset.
