# think_parallel_v2 generation summary

## Run

- category: `multi_turn_base`
- mode: `llmcompiler_explicit_dag`
- n_episodes: `20`
- n_turn_generations: `70`
- episode_filter: `prepared`
- dry_run: `False`
- output_dir: `/home/ilju/research/DiffuAgent/think_parallel_v2/outputs/smoke_explicit`

## Parse

- total_generations: `70`
- parsed_generations: `70`
- format_parse_rate: `1.000`
- total_units: `154`
- mean_units_per_generation: `2.20`

## Quality Diagnostics

- `valid_tool_name_units` checks provided tool names only; it is not gold correctness.
- valid_tool_name_units: `125`
- invalid_tool_name_units: `29`
- schema_checked_generations: `70`
- schema_valid_units: `80`
- duplicate_action_generations: `5`
- over_generated_vs_gold_generations: `27`
- dependency_edge_count: `13`
- flat_reference_violation_generations: `0`
- flat_reference_violation_count: `0`

Gold graph matching and denoising analyses are post-hoc steps.
