# think_parallel_v2 generation summary

## Run

- category: `multi_turn_base`
- mode: `llmcompiler_explicit_dag`
- n_episodes: `9`
- n_turn_generations: `33`
- episode_filter: `prepared`
- dry_run: `False`
- output_dir: `/home/ilju/research/DiffuAgent/think_parallel_v2/outputs/smoke_pre_split`

## Parse

- total_generations: `33`
- parsed_generations: `33`
- format_parse_rate: `1.000`
- total_units: `86`
- mean_units_per_generation: `2.61`

## Quality Diagnostics

- `valid_tool_name_units` checks provided tool names only; it is not gold correctness.
- valid_tool_name_units: `62`
- invalid_tool_name_units: `24`
- schema_checked_generations: `33`
- schema_valid_units: `34`
- duplicate_action_generations: `0`
- over_generated_vs_gold_generations: `19`
- dependency_edge_count: `10`
- flat_reference_violation_generations: `0`
- flat_reference_violation_count: `0`

Gold graph matching and denoising analyses are post-hoc steps.
