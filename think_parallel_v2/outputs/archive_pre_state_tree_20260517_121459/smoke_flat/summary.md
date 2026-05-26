# think_parallel_v2 generation summary

## Run

- category: `multi_turn_base`
- mode: `llmcompiler_flat_plan`
- n_episodes: `20`
- n_turn_generations: `70`
- episode_filter: `prepared`
- dry_run: `False`
- output_dir: `/home/ilju/research/DiffuAgent/think_parallel_v2/outputs/smoke_flat`

## Parse

- total_generations: `70`
- parsed_generations: `70`
- format_parse_rate: `1.000`
- total_units: `139`
- mean_units_per_generation: `1.99`

## Quality Diagnostics

- `valid_tool_name_units` checks provided tool names only; it is not gold correctness.
- valid_tool_name_units: `114`
- invalid_tool_name_units: `25`
- schema_checked_generations: `70`
- schema_valid_units: `78`
- duplicate_action_generations: `3`
- over_generated_vs_gold_generations: `19`
- dependency_edge_count: `1`
- flat_reference_violation_generations: `1`
- flat_reference_violation_count: `1`

Gold graph matching and denoising analyses are post-hoc steps.
