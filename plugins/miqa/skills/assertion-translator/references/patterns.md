# Translation patterns

Use these examples for translation shape. Confirm exact calls, argument order, and comparator names
against the applicable path in `doc-paths.md`.

## Top-level group keys must be the check_type

Every check-level JSON fragment elsewhere in this file omits the outer wrapper for brevity — don't
let that omission imply group keys are arbitrary. They are not. Every full worked example across the
docs (`paired-tabular-mdo-eval.md`, `execution-stats-compare.md`, `paired-execution-stats.md`,
`assertion-type-tabular_json_eval.md`, `file-based-test-parameters.md`, `assertion-type-concordance.md`)
uses the check's own `check_type` string as the group key:

```json
{
  "paired_tabular_mdo_eval": {
    "report": true,
    "checks": [ { "check_type": "paired_tabular_mdo_eval", "...": "..." } ]
  }
}
```

Never invent a semantic group name (`starter_checks`, `vcf_validation`, etc.) as a top-level key —
the live schema's `patternProperties` regex is permissive enough to accept any name, so schema
validation alone will not catch this mistake. Put every check of the same `check_type` in that one
group's `checks` array, even when they answer unrelated reviewer questions — do not split one
check_type across multiple invented groups.

## Common gotchas

* Repeated `file_rules`/`delimiter`/`comment_character`/`configuration` across checks in one group →
  bind once in `_variables`, pull in with `_extends` (see `variables-and-precompute.md`). Config
  nesting for the same parsing fields can differ by check_type (e.g. `add_headers` sits under
  `configuration`/`baseline_configuration` for `paired_tabular_mdo_eval` but top-level for
  `tabular_mdo_eval`) — confirm each check_type's own doc page before reusing one bundle across types.
* `compare_all_fields` is called directly on `data_baseline.rows`, never chained after `.match()` —
  `match(...).compare_all_fields()` raises `AttributeError` (`match()`'s result only has
  `.compare_fields()`/`.compare_by()`).
* `concordance` needs the pipeline's **Parsed Results** configured (structured result rows already in
  Miqa) — it appears in vocabulary starter blurbs but isn't a drop-in substitute for a raw-file check
  type like `paired_tabular_mdo_eval`/`tabular_mdo_eval`. Confirm before using it.

## Natural-language requests

Separate requested meaning from data evidence:

| Request | Translation | Outcome |
| --- | --- | --- |
| “Compare row counts between baseline and test files.” | One comparative count stat | Report-only |
| “Fail when the mismatch rate exceeds 2%.” | One mismatch stat and the requested gate | Explicit failure above 2% |
| “Plot temperature by timestamp for both versions.” | One comparison with a chart | Report-only |
| “Check that the files match.” | Ask what match means and how files pair | Blocked until clarified |

A request can establish intent, including an exact gate or mapping. It does not prove that a file,
column, or value exists. Use execution or sample evidence for those facts.

## Group by reviewer question

For a probe comparison, group many helper functions and loop operations into four checks:

| Question | Source evidence | Translation |
| --- | --- | --- |
| Do shared probe fields agree? | `build_data_dict`, seven field pairs | One matched-record field comparison |
| Do probe physics values agree? | Physics extraction and five `plot_data` calls | One comparison with five charts |
| How many records overlap? | Count, common, and unique helpers | One overlap summary |
| Do sequences match? | Per-variant alignment loop | One vectorized sequence comparison |

Group by stable review intent, not by function, loop, column, or plot count.

## Pair two input files

Two script arguments become one baseline and test pair:

```json
{
  "check_type": "paired_tabular_mdo_eval",
  "versions": [-1],
  "file_rules": {"pattern": ".*(maestro_final_ranking\\.txt|probe_design\\.csv)$"}
}
```

Treat a script-derived pattern as unconfirmed. Replace it with execution file keys when available.
Confirm which execution side is `data_baseline` and which is `data_test`. Argument names such as
`rd` and `prod` do not define that direction.

## Rename columns once

Copy the full mapping into one transform:

```json
{
  "configuration": {
    "transforms": [{
      "type": "rename",
      "columns": {"chrom": "chromosome", "variant_id": "id", "probe_tm": "tm"}
    }]
  }
}
```

Use the target names in all later expressions. Do not replace column tokens inside expression
strings.

## Vectorize sequence comparison

Replace a Python loop that aligns one sequence pair at a time with one row comparison:

```json
{
  "stat": "data_baseline.rows.match(data_test.rows, on=['id']).compare_by('sequence', using='alignment_ratio').summary().is_match_within_threshold"
}
```

## Attach plots to their check

Map each plot to a `chart_config` entry on the check that computes its data:

```json
{
  "title": "dg: baseline vs test",
  "chart_type": "scatter",
  "chart_values": "data_baseline.rows.match(data_test.rows, on=['id']).compare_by('dg').results().to_xy_pairs('value1','value2')"
}
```

Attach the five physics plots to one physics comparison. Confirm the value-chain shape
for the selected chart type before using it.

## Report without gating

When the source computes alignment but defines no pass or fail condition, write only the stat. Add
the possible gate to `coverage.md`:

```
- Threshold candidate: sequence alignment ratio. The source computes identity but does not gate on
  it. A reviewer must select any threshold.
```
