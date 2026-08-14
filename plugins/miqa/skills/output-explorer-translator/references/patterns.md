# Translation patterns

Use these examples for translation shape. Confirm exact calls, argument order, and comparator names
against the applicable path in `doc-paths.md`.

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
