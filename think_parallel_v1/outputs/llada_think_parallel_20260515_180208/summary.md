# think_parallel_v1 judge summary

## Run

- total_generations: `50`
- parsed_generations: `50`
- total_units: `172`
- total_gold_hops: `293`

## Metrics

| metric | value |
|---|---:|
| `format_parse_rate` | 1.000 |
| `candidate_gold_coverage` | 1.000 |
| `strict_single_action_recall` | 0.218 |
| `semantic_single_action_recall` | 0.246 |
| `partial_or_better_recall` | 0.334 |
| `recall_including_compound` | 0.413 |
| `compound_action_rate` | 0.099 |
| `hallucinated_argument_rate` | 0.198 |
| `unmatched_action_rate` | 0.326 |
| `duplicate_action_rate` | 0.012 |

Interpretation:

- `strict_single_action_recall`: exact match and one generated action maps to one gold hop.
- `semantic_single_action_recall`: exact or semantic match, still one generated action per gold hop.
- `recall_including_compound`: coverage upper bound; compound actions are included.
