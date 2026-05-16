# think_parallel_v1 judge summary

## Run

- total_generations: `50`
- parsed_generations: `50`
- total_units: `148`
- total_gold_hops: `293`

## Metrics

| metric | value |
|---|---:|
| `format_parse_rate` | 1.000 |
| `candidate_gold_coverage` | 0.676 |
| `strict_single_action_recall` | 0.184 |
| `semantic_single_action_recall` | 0.215 |
| `partial_or_better_recall` | 0.256 |
| `recall_including_compound` | 0.314 |
| `compound_action_rate` | 0.088 |
| `hallucinated_argument_rate` | 0.189 |
| `unmatched_action_rate` | 0.392 |
| `duplicate_action_rate` | 0.014 |

Interpretation:

- `strict_single_action_recall`: exact match and one generated action maps to one gold hop.
- `semantic_single_action_recall`: exact or semantic match, still one generated action per gold hop.
- `recall_including_compound`: coverage upper bound; compound actions are included.
