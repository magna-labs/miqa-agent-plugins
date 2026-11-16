# Lint rules

Each rule has a severity, how to detect it, the fix, and the basis. **Code** means read in the
platform's evaluation code. **Docs** means stated in the Miqa documentation. **Seen** means found in
real Test Blocks but not confirmed in code. Treat a **Seen** rule as a suggestion.

The assertions have this shape: optional top-level `_variables`, then one group per check type, each
with a `checks` list. Shared `_variables` belong at the top, next to the groups.

## Known keys

The vocabulary's field list is not exhaustive and allows extra keys, so it cannot decide whether a
key is wrong. Use this seed list. A key that is not in it, and is not close to one that is, is not an
error: say you could not confirm it.

- Group: `report`, `checks`.
- Check: `name`, `check_type`, `failtype`, `id`, `tags`, `expected_result`, `export_name`, `evidence`,
  `description`, `visualization`, `stat`, `static`, `relationship`, `query`, `detail_display_stat`,
  `versions`, `file_rules`, `file_pattern`, `exclude_pattern`, `filetype`, `single_file`, `min_count`,
  `max_file_size`, `delimiter`, `comment_character`, `add_headers`, `key_columns`, `configuration`,
  `allow_missing_files`, `min_similarity_score`, `comparison_mode`, `replicate_anchor_ds`,
  `baseline_override`, `test_override`, `baseline_file_rules`, `rules`, `unified_diff`,
  `hide_viz_for_passing`, `processor_key`, `postprocessed_file_pattern`, `item_type`.
- Tables and charts: `table_config`, `chart_config`, `aggregate_table_config`,
  `aggregate_chart_config`, `multi_file_table_config`, `multi_file_chart_config`.
- Aggregates: `named_aggregate_stats`, `named_aggregate_results`, `is_aggregate`, `aggregate_check`,
  `aggregate_check_only`, `group_aggregate_check`, `pass_aggregate_check`,
  `group_pass_aggregate_check`.
- Multi-file: `multi_file`, `multi_file_query`, `multi_file_detail_display_stat`.
- Reuse: `_variables`, `_extends`, `_precompute`, `_precompute_multi_file`.
- Control: `_ds_ids`, `_skip_ds_ids`, `_wfv_ids`, `_skip_wfv_ids`, `_ds_tags`, `_skip_ds_tags`, `_skip`,
  `_force_pass`, `_force_fail`, `_force_errors`, `_force_messages`, `_show_logs`, `_show_ds_info`,
  `_skip_failed_executions`, `_run_if`, `_error_mode`, `_run_in_background`,
  `_parallel_dataset_workers`, `_parallel_dataset_mode`.
- Table entry: `title`, `table_values`, `headers`, `max_row_count`, `downloadable`, `download_only`,
  `column_config`, `union_headers`, `first_columns`, `conditional`, `only_on_failure`, `always_show`.

## S. Errors, certain from the text

**S1. Ignored key (error or likely mistake).**
Detect: a key on a check or a table entry that is within edit distance 2 of a key in the seed list
above but is not that key. Examples: `delimeter`, `expected_result:` with a trailing colon, `export`
where `export_name` or `evidence` was meant. A key far from every known key is not an error. Fix:
rename it. Basis: Code. Settings are read with
`.get`, so an unknown key is never read and nothing reports it.

**S2. `_variables` inside a check-type group (error).**
Detect: a `_variables` key next to `checks`, not at the top of the assertions and not inside a check.
Fix: move it to the top level. Basis: Code. Only the top level and each check are read.

**S3. Aggregate tables with no aggregate stats (error).**
Detect: a check has `aggregate_table_config` or `aggregate_chart_config` and no
`named_aggregate_stats` (or, on compare-style check types, `named_aggregate_results`). Fix: add the
stats the tables read. Basis: Code. The tables are only built when the stats exist, and nothing
reports their absence.

**S4. Aggregate stats on a check type that does not take them (error).**
Detect: `named_aggregate_stats` on a type outside this list: `file_collection`, `execution_stats`,
`postproc_results`, `file_structure`, `postproc_file_structure`, `json_mdo_eval`,
`postproc_json_mdo_eval`, `tabular_mdo_eval`, `postproc_tabular_mdo_eval`,
`paired_tabular_mdo_eval`, `postproc_paired_tabular_mdo_eval`, `paired_file_structure`,
`postproc_paired_file_structure`, `paired_json_mdo_eval`, `postproc_paired_json_mdo_eval`,
`paired_postproc_results`, `postproc_compare`, `paired_file_collection`, `paired_execution_stats`.
The compare-style types `compare_file_structure`, `json_mdo_compare`, `tabular_mdo_compare` and their
`postproc_` versions take `named_aggregate_results`, and accept `named_aggregate_stats` as an alias.
`file_collection_compare` and `execution_stats_compare` take neither. Basis: Code. The platform raises
an error naming the supported types. The list may change, so confirm against the vocabulary.

**S5. Undefined or unused variable (error, or suggestion).**
Detect: `{{NAME}}` with no definition at the top level or in the check (error). A `_variables` entry,
`_precompute` entry or named stat that nothing reads (suggestion). Also `_extends` naming a bundle
that does not exist (error). A bundle is a variable whose value is an object of check fields, defined
in `_variables` and pulled in with `"_extends": ["NAME"]`. Count a use inside another variable as a
use. Fix: define it, or delete it. Basis: Code and Docs. Variables resolve
by text substitution before anything runs.

**S6. Stat named like a built-in (error).**
Detect: a `named_aggregate_stats` name that is a built-in property of the data object. `rows` is
confirmed: `data.rows` then returns the list of the stat's values and calling `explode()` on it
fails. Fix: rename the stat (for example `merged`). Basis: Code, run on a sample. Other names may
collide, so for anything unfamiliar, say you could not confirm it.

**S7. Operator the comparison does not know (error).**
Detect: `relationship` other than `gt`, `lt`, `ge`, `le`, `eq`, `neq` (or `>`, `<`, `>=`, `<=`,
`==`, `!=`). Common cases: `ne`, and `within_range` or `outside_range` on `file_counts`. Some older
check types (result-based and percent checks) also accept `outside_range`, so confirm the check type
in the vocabulary before flagging it there. Fix: use `neq`, or a supported operator. Basis: Code.
The comparison used by `file_counts` and the eval types raises an error for any other value.

**S8. Chart requested with nothing to draw (likely mistake).**
Detect: `visualization: "chart"` and no `chart_config` or `aggregate_chart_config`. Basis: Seen.

## P. Pass and fail

For each check, work out in words when it fails. Then compare with `name` and `expected_result`.

**P1. A number with no threshold (likely mistake).**
Detect: `stat` is a number (a count, a ratio, a mean) and the check has no `relationship` and
`static`, while the name or `expected_result` implies a limit ("at least", "no more than",
"within", "%"). Effect: with the defaults (`eq`, `static: false`) a number fails only when it is
exactly 0, so the check almost never fails. Fix: make `stat` a true or false expression, or set
both `relationship` and `static`. Basis: Code and Docs. If you cannot tell whether `stat` is a
number, run the check and read its type, or say it is unknown.

**P2. Direction of `relationship` (likely mistake).**
Detect: compare the operator with the wording. `relationship` is the condition under which the
check **fails**. "At least 97%" is `lt` 0.97. "At most 5" is `gt` 5. "Under 12 hours" is `ge` 12.
Watch the boundary: "at least" with `le` fails at the limit, and "under" with `gt` passes at it.
`eq` and `neq` are easy to reverse. The `aggregate_check` and `pass_aggregate_check` use the same
rule. Exception: in `file_counts`, `relationship` is the **pass** condition, so "at least 1" is
`ge` 1. Fix: restate when the check fails in plain words, and ask whether that matches the name.
Basis: Code and Docs. Always a suggestion, because intent comes from free text.

**P3. A check that cannot fail (likely mistake).**
Detect: a `stat` that can only be true (for example a bare `.preview()`, `.summary()` or
`.group_apply()`), or a placeholder `stat` with `static: 0` and `lt`, on a check with no
`aggregate_check_only`. Fix: add the condition that matters. Do not flag the placeholder when
`aggregate_check_only` is set. Basis: Docs and Code.

**P4. Comparison on a truncated list (likely mistake).**
Detect: `.preview(n)`, `.head(n)` or `.slice(...)` applied before `.match(...)` or
`.compare_fields(...)`. Effect: only those rows are compared. Basis: Docs (`preview` keeps the first
rows).

**P5. Aggregate gate that is not the only decider (suggestion).**
Detect: `aggregate_check` with no `aggregate_check_only`, and a check-level `stat` that can fail on
its own. A placeholder `stat` (one that cannot fail) is not a decider. Say which of the two can fail
the check. Basis: Code (`aggregate_check_only` ignores the
per-dataset results).

**P6. Passes on no data, or errors instead of failing (likely mistake).**
Detect: indexing or accessors that assume something is there: `[0]`, `.first`, `.single`, `.max_by`
or a mean over a filtered list that can be empty. Effect: an empty result may pass without checking
anything, or raise an error. Fix: test for presence first, or make the empty case an explicit
failure. Basis: Seen. Always a suggestion unless the empty case is clearly possible.

**P7. Checks one row when the name says all (suggestion).**
Detect: `name` or `expected_result` says "each", "all" or "every", while the `stat` reads only the
first matching row (`.first`, `.slice(0, 1)`, `.head(1)`). Fix: apply the condition to every row
(`assert_all`). Basis: Seen.

## N. Names in the wrong place

**N1. Baseline and test names in a single-sided check (error).**
Detect: `data_baseline`, `data_test`, `baseline_*` or `test_*` data names in a check type that has
no baseline (`tabular_mdo_eval`, `file_collection`, `file_structure`, `json_mdo_eval` and their
`postproc_` versions). In a paired or compare check, flag `data` where the author clearly meant
one side (suggestion). Basis: Code. Baseline and test data are only present when the check has both
sides.

**N2. Wrong namespace inside an aggregate table (error).**
Detect: an `aggregate_table_config` `table_values` that reads `data_baseline`, `data_test` or
`data.rows` rather than `data.<named stat>`. Inside aggregate tables only the named stats are in
scope. Per-sample names belong inside `named_aggregate_stats`. Basis: Code.

**N3. A name reused with a different meaning (likely mistake).**
Detect: the same variable or stat name defined with different expressions in different checks
(for example `BASE` meaning the baseline rows in one and the test rows in another). Basis: Seen.
Also: a check's own `_variables` can still be present when later checks run, because the platform
updates one shared set in place. Set a variable in every check that depends on it. Basis: Code.

## R. Reuse and performance

For each performance finding, say whether it is **measured** or **assumed**.

**R1. Same expression written several times (suggestion).**
Detect: an expression of about 60 characters or more that is used three or more times in a check
or across the block. Count a `{{VAR}}` use as one occurrence of the expression it holds, because the
text is substituted. Raise it as a cost problem only when the expression involves `Match`, `Join`,
`group_by`, `merge_rows`, `explode` or a large file. For a short, cheap filter on a small file it is
a maintenance note at most, so skip it. Fix: for per-dataset values, move it to `_precompute` (or
`_precompute_multi_file`) so it runs once. `_variables` is text substitution, so it only saves
typing: the expression is still evaluated at every place it is used. Basis: Code and Docs.

**R2. Long literal list repeated (suggestion).**
Detect: the same list or dict literal of ten items or more inlined in two or more places. Fix: put it
in `_variables`. Basis: Seen.

**R3. Per-sample tables repeated across checks (suggestion).**
Detect: the same `table_config` entry in five or more checks, or a per-sample table beside many
samples where the reader would prefer one table. Fix: one `aggregate_table_config`, and remove the
per-sample tables. Removing them is faster than `download_only`, which still evaluates and stores the
full table for every sample and skips only the on-screen table. Offer `download_only` only if the user
wants the per-sample downloads. Basis: Seen. See the `table-config-to-aggregate`
skill for the conversion.

**R4. Aggregate tables that are not downloadable (suggestion, low priority).**
Detect: an `aggregate_table_config` entry without `downloadable: true` or `download_only: true`. The
house convention is that aggregate tables are always downloadable. Mention a short one-row-per-sample
table only as a low-priority note.
Basis: Docs (the full table is stored when either is set; `max_row_count` only limits what is
shown).

**R5. Limits larger than the check needs (suggestion).**
Detect: a very large `max_row_count`, or a `max_file_size` far above what the check reads (for
example a check that reads one row or a preview, with a limit in the hundreds of megabytes or more).
Fix: lower it, or use `download_only` for the full table. Basis: Docs and Seen. Needs file sizes to
be sure, so label it **assumed** without them.

**R6. Many checks reading the same large file (suggestion).**
Detect: five or more checks in the block, in any group, whose `file_rules` match the same file. Fix: combine related conditions
into one check with several tables. Basis: Seen. Whether each check re-reads the file is not
confirmed, so say it may repeat the work.

**R7. Cannot run in parallel by dataset (suggestion).**
Detect: a check with aggregate tables or charts together with a median or mean `aggregate_check`
(any type except `query`), or with `group_aggregate_check`, `pass_aggregate_check` or
`group_pass_aggregate_check`. These cannot be split across datasets. Matters only if parallel dataset
workers are in use (`_parallel_dataset_workers`, `_run_in_background` or the deployment setting).
Basis: Code.

**R8. The same table evaluated many times (suggestion).**
Detect: four or more aggregate tables in one check that each repeat the same large `Match` or
`Join` text from a variable. Two or three tables are not worth raising.
Each table evaluates its own copy. Fix: reduce the number of tables, or build the shared part into a
named stat. Basis: Code (text substitution).

**R9. Duplicate checks or blocks (suggestion).**
Detect: two checks identical apart from names, or whole check groups identical apart from a numeric
identifier. Fix: share one definition with `_extends`. Basis: Seen.

## H. Hygiene

**H1. Leftover placeholder (likely mistake).** A name such as "Your Check Name", or an unchanged
example `id`. Basis: Seen.

**H2. Hard-coded values that go stale (suggestion).** A count (`== 76`), a universe size, a dataset
ID or a sample ID inside a `stat`, `name` or `description`. Fix: a variable, with a comment on what
it counts. Do not flag a list that is the expected data itself, such as the reference values a check
compares against. If such a list is repeated, use R2. Basis: Seen.

**H3. Two checks with the same `export_name` (likely mistake).** The text alone shows it, and exports
can collide. Fix: give each check its own. Basis: Seen.

**H3b. Copied text that no longer matches (suggestion).** A title that states a number the filter
does not use, or a label from the previous check (a check about one score labelled with the other).
Compare each title, label and filter together. Basis: Seen.

**H4. Stray separator in a field list (likely mistake).** A `;` or other punctuation inside a list of
field names that merges two names into one. Basis: Seen.

**H5. Missing `export_name` (suggestion, low priority).** Some checks in a group have an
`export_name` and others do not. Treat an empty string as unset, and mention it only when other
checks in the group are named. An empty `detail_display_stat` is the same kind of leftover. Basis:
Seen.

**H6. A lookup list that does not match the values it is matched against (likely mistake).**
Detect: a priority or sort list whose entries use different spelling, separators or case from the
keys the expression generates (for example one underscore in the list and two in the generated keys).
Effect: those rows never match and sort last or are dropped. Fix: align the spelling, and say the key
format you could not confirm. Basis: Seen.

**H7. A description written into `name` (suggestion, low priority).** A very long `name` that reads
as a requirement or procedure. Fix: keep `name` short and move the text to `description` or
`expected_result`. Basis: Seen.
