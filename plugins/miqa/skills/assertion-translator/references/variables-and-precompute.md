# Variables and precompute

This behavior comes from `resolve_check_with_variables` and
`update_context_with_precomputed_values` in `p41/facet/methods/methods_test_automation.py`.

## Keep the phases separate

| Mechanism | Time | Effect |
| --- | --- | --- |
| `_variables` and `_extends` | Before evaluation | Rewrite the check JSON |
| `_precompute` | During evaluation | Evaluate expressions and add their results to the runtime context |

## Substitute variables

Use `$name` as a standalone string value. It replaces the whole value and can produce any JSON
type:

```json
"file_rules": "$file_settings"
```

Do not embed `$name` in other text or use a dotted name. If the name is missing, the literal string
remains unchanged.

Use Jinja for interpolation inside a string:

```json
"stat": "data_test.rows.count >= {{ min_rows }}"
```

A string can contain multiple Jinja references. If rendering fails or a name is missing, the
original string remains unchanged. Pre-emission validation must catch both unresolved forms.

## Resolve scope in order

1. Start with the ambient variable scope supplied by the caller.
2. Overlay the check's `_variables`; local entries win.
3. Resolve that merged scope against itself for at most eight passes, stopping early when no value
   changes. This supports reference chains. A cycle can remain after the final pass.
4. Resolve the check recursively through nested dictionaries and lists.
5. Resolve each `_extends` name from the same merged scope. Each value must be a dictionary. Merge
   bundles in list order, then merge the check over them. Later bundles win over earlier bundles,
   and check keys win over all bundles. Merge dictionary collisions recursively. Replace lists and
   scalar values as complete values.
6. During evaluation, process `_precompute` entries in insertion order and add each result to the
   same context before processing the next entry.

## Bind reusable runtime values

Later precompute entries can use earlier results:

```json
{
  "_precompute": {
    "matched": "data_baseline.rows.match(data_test.rows, on=['id'])",
    "matched_count": "matched.results().count"
  }
}
```

The check's `stat`, `query`, `table_config`, and `chart_config` expressions can use every bound
name, as they use `data_baseline` and `data_test`.

The caller's `is_multi` argument selects `_precompute_multi_file` instead of `_precompute`.
`is_multi` is not a check field. A check can define both blocks, but a run reads only one.

## Check for source changes

Re-read both source functions when this behavior is unexpected. This reference becomes stale when
either implementation changes.
