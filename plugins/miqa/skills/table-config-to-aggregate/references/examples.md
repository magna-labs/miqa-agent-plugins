# Worked examples

Each example was run through the platform's expression engine on a small VCF, so the expressions
behave as shown. Use them as shapes to copy, not as text to paste: rename stats, titles and
columns to fit the check you are converting.

## 1. Per-sample table to aggregate table

Before:

```json
{
  "tabular_mdo_eval": {
    "report": true,
    "checks": [
      {
        "name": "Each sample has at least one PASS call",
        "check_type": "tabular_mdo_eval",
        "failtype": "fail",
        "file_rules": {
          "pattern": ".*\\.vcf$"
        },
        "stat": "data.rows.filter_custom(lambda row: row.FILTER == 'PASS').count > 0",
        "table_config": [
          {
            "title": "PASS calls",
            "table_values": "data.rows.filter_custom(lambda row: row.FILTER == 'PASS')",
            "headers": [
              "CHROM",
              "POS",
              "REF",
              "ALT"
            ],
            "max_row_count": 100
          }
        ]
      }
    ]
  }
}
```

After. The per-sample table is kept as `download_only`; delete it if the user does not want it:

```json
{
  "tabular_mdo_eval": {
    "report": true,
    "checks": [
      {
        "name": "Each sample has at least one PASS call",
        "check_type": "tabular_mdo_eval",
        "failtype": "fail",
        "file_rules": {
          "pattern": ".*\\.vcf$"
        },
        "stat": "data.rows.filter_custom(lambda row: row.FILTER == 'PASS').count > 0",
        "table_config": [
          {
            "title": "PASS calls",
            "table_values": "data.rows.filter_custom(lambda row: row.FILTER == 'PASS')",
            "headers": [
              "CHROM",
              "POS",
              "REF",
              "ALT"
            ],
            "max_row_count": 100,
            "download_only": true
          }
        ],
        "named_aggregate_stats": {
          "pass_calls": "data.rows.filter_custom(lambda row: row.FILTER == 'PASS')"
        },
        "aggregate_table_config": [
          {
            "title": "PASS calls (all samples)",
            "table_values": "data.pass_calls.explode(key_field='sample')",
            "headers": [
              "sample",
              "CHROM",
              "POS",
              "REF",
              "ALT"
            ],
            "downloadable": true,
            "max_row_count": 1000
          }
        ]
      }
    ]
  }
}
```

- The aggregate table reads `data.<stat>` and uses `explode(key_field='sample')` for the sample column.
- Samples with no rows add none. Tell the user which samples are missing from the table.

## 2. A table shared by several checks

Define the table once in top-level `_variables` and pull it in with `_extends`. Set the variable
that differs (here `LABEL`) in every check, because a check's variables can still be present when
later checks run. Each check keeps its own `named_aggregate_stats` with the stat name the shared
table reads.

```json
{
  "_variables": {
    "CALL_TABLE": {
      "aggregate_table_config": [
        {
          "title": "{{LABEL}} (all samples)",
          "table_values": "data.calls.explode(key_field='sample')",
          "headers": [
            "sample",
            "CHROM",
            "POS",
            "REF",
            "ALT"
          ],
          "downloadable": true,
          "max_row_count": 1000
        }
      ]
    }
  },
  "tabular_mdo_eval": {
    "report": true,
    "checks": [
      {
        "name": "Each sample has PASS calls",
        "check_type": "tabular_mdo_eval",
        "failtype": "fail",
        "file_rules": {
          "pattern": ".*\\.vcf$"
        },
        "_variables": {
          "LABEL": "PASS calls"
        },
        "_extends": [
          "CALL_TABLE"
        ],
        "stat": "data.rows.filter_custom(lambda row: row.FILTER == 'PASS').count > 0",
        "named_aggregate_stats": {
          "calls": "data.rows.filter_custom(lambda row: row.FILTER == 'PASS')"
        }
      },
      {
        "name": "Each sample has A to G calls",
        "check_type": "tabular_mdo_eval",
        "failtype": "warn",
        "file_rules": {
          "pattern": ".*\\.vcf$"
        },
        "_variables": {
          "LABEL": "A to G calls"
        },
        "_extends": [
          "CALL_TABLE"
        ],
        "stat": "data.rows.filter_custom(lambda row: row.REF == 'A' and row.ALT == 'G').count > 0",
        "named_aggregate_stats": {
          "calls": "data.rows.filter_custom(lambda row: row.REF == 'A' and row.ALT == 'G')"
        }
      }
    ]
  }
}
```

## 3. An aggregate gate

`relationship` is the condition under which the check **fails**, so "at least 3" is `lt` with
`static: 3`. At an average of exactly 3: `lt` passes, `le` fails, `gt` passes, `ge` fails. With
`aggregate_check_only`, the check-level `stat` does not decide the result. `file_counts` is the one
exception: there `relationship` is the pass condition.

```json
{
  "tabular_mdo_eval": {
    "report": true,
    "checks": [
      {
        "name": "Average calls per sample is at least 3",
        "check_type": "tabular_mdo_eval",
        "failtype": "fail",
        "file_rules": {
          "pattern": ".*\\.vcf$"
        },
        "stat": "data.rows.count > 0",
        "named_aggregate_stats": {
          "call_count": "data.rows.count"
        },
        "aggregate_check_only": true,
        "aggregate_check": {
          "type": "query",
          "label": "Mean calls per sample",
          "query": "data.call_count.explode(value_field='value').map('value').mean",
          "relationship": "lt",
          "static": 3
        },
        "aggregate_table_config": [
          {
            "title": "Calls per sample",
            "table_values": "data.call_count.explode(value_field='calls')",
            "downloadable": true
          }
        ]
      }
    ]
  }
}
```

This skill never changes a gate. Convert tables only, and report a gate it would have needed to touch.
