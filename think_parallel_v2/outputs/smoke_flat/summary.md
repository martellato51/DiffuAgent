# think_parallel_v2 generation summary

## Run

- category: `multi_turn_base`
- mode: `llmcompiler_flat_plan`
- n_episodes: `9`
- n_turn_generations: `33`
- episode_filter: `prepared`
- dry_run: `False`
- output_dir: `/data/home/martellato41/research/DiffuAgent/think_parallel_v2/outputs/smoke_flat`

## Parse

- total_generations: `33`
- parsed_generations: `33`
- format_parse_rate: `1.000`
- total_units: `70`
- mean_units_per_generation: `2.12`

## Quality Diagnostics

- `valid_tool_name_units` checks provided tool names only; it is not gold correctness.
- valid_tool_name_units: `44`
- invalid_tool_name_units: `26`
- schema_checked_generations: `33`
- schema_valid_units: `30`
- duplicate_action_generations: `3`
- over_generated_vs_gold_generations: `11`
- dependency_edge_count: `0`
- flat_reference_violation_generations: `0`
- flat_reference_violation_count: `0`

Gold graph matching and denoising analyses are post-hoc steps.
