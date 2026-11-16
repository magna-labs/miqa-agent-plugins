# Conversion patterns and rules

Read this first. Search the docs only for a helper, key or check type that is not covered here.
Source: the docs page "Aggregate expression-based tests", section "Converting a per-sample table to
an aggregate table", and the platform's table code. If this file and the live docs disagree, trust
the docs and say so.

## Mapping

| Per-sample stat holds | Aggregate `table_values` | Result |
| --- | --- | --- |
| One summary object per sample (counts, IDs) | `data.<name>.explode()` | One row per sample, `key` first |
| The same, with explicit column order | `data.<name>.to_key_value_list()` plus `headers` | One row per sample |
| A list of rows per sample | `data.<name>.explode()` | One row per item, sample key added as `key` (last column) |
| A list of rows per sample, joined into one list | `data.<name>.to_key_value_list().map('value').flatten()` plus `headers` | One row per item, no sample key |
| A preview of each file's rows (`data.rows.preview()`) | `data.<name>.explode()` | First rows of every file in one table |
| A filtered list of rows | `data.<name>.explode().filter_expr("<condition>")` | Matching rows across samples |
| A single value per sample (string or number) | `data.<name>.explode(value_field='<column>')` | `key` plus the named column |
| Two or more stats side by side | `Join(data.a.explode(value_field='a'), data.b.explode(value_field='b'), on='key')` | One row per sample, columns from each |
| A dict literal or one-item list built from scalars | the same expression, reading `data.<name>` | A small summary table |

## Behavior that surprises people

- Do not name a stat `rows`, or any other built-in property of `data`. `data.rows` then returns the list of the stat's values and `data.rows.explode()` fails. When a per-sample table reads `data.rows...`, give the stat a different name such as `merged` or `variants`.
- `aggregate_table_config` is only read when the check has `named_aggregate_stats`. Without it the
  tables are ignored and nothing reports an error. Compare-style check types (for example
  `json_mdo_compare`) take `named_aggregate_results`, and accept `named_aggregate_stats` as an alias.
- `is_aggregate` is not needed to get aggregate tables.
- Aggregate tables appear under the first dataset's results only.
- `explode()` on a map of row lists skips samples whose list is empty, so those samples do not
  appear. It adds the sample key as `key`, replacing any column already called `key`.
  `explode(key_field='<name>')` names that column. `column_config` can rename it too.
- `merge_rows()` also flattens a map of row lists, but labels rows with a `group` column unless
  `group_field` is given. Prefer `explode()`.
- `to_key_value_list()` on a map of objects merges each object's fields into its row and keeps the
  key. On a map of lists it gives `key` and `value`, where `value` is the list.
- `headers` may name a column by its original or its renamed name.
- `download_only` on a table implies `downloadable`. `max_row_count` limits only what is displayed;
  the full table is stored when `downloadable` or `download_only` is set.
- A check with aggregate tables and a median or mean `aggregate_check` cannot be split across
  datasets. Tables beside a query-type `aggregate_check`, or none, can.
- `multi_file_table_config` (read with `multi_file_query`) is separate from
  `aggregate_table_config`. Do not convert it unless asked.

## Names that exist where

- Inside a per-sample table or a named stat of a single-sided check (for example
  `tabular_mdo_eval`, `file_collection`): `data`, `stats`, `results`.
- Inside a named stat of a paired check: `data_baseline`, `data_test`, `baseline_execution_stats`,
  `test_execution_stats`, `ds_info`.
- Inside an aggregate table: `data.<named stat>` only. `data`, `stats` and `results` are the same
  object there.

## Practice in existing Test Blocks

- Some keep the per-sample table beside the aggregate one with `download_only: true`. Offer that as
  an option when converting, but recommend removing the per-sample table. Removing it is faster: a
  `download_only` table is still evaluated and stored for every sample, and only the on-screen table
  is skipped.
- Shared aggregate tables are often stored once in `_variables` and pulled in with `_extends`.
- A one-row summary is often written as a one-item list, for example
  `[<match>.ppa_summary(method="wilson").add_column('TP', <match>.tp())]`.

## Does not fit

Leave the table unchanged and say why when it needs more than one sample's data at once (a `Join`
or `Match` across samples, a total across all samples, or anything an `aggregate_check` reads).
