---
name: table-config-to-aggregate
description: Use when the user wants per-sample `table_config` tables turned into cross-sample (aggregate) tables, or the reverse, e.g. "convert these table_configs to aggregate", "show one table across all samples instead of one per sample", "add aggregate_table_config to this test block", or pastes assertions JSON whose checks have `table_config` and asks for a combined view (via a connected Miqa MCP server). Reads the checks, adds `named_aggregate_stats` and `aggregate_table_config` that reproduce each per-sample table across all samples, proves the result on a real run, and hands back the edited JSON. Works in both directions (per-sample to aggregate by default) and says so plainly when a table does not fit the pattern. Never saves or publishes a Test Block unless the user explicitly asks at the end.
metadata:
  summary: Convert table_config entries to aggregate_table_config tables, or back.
  version: 0.3.0
---

# Per-sample table_config to aggregate_table_config

A `table_config` table is evaluated once per file or file pair, so a reviewer opens one sample at a
time. An `aggregate_table_config` table is evaluated once, after every sample has run, and shows all
samples together. This skill rewrites the first into the second without changing what the check
decides.

It calls `get_output_explorer_vocabulary`, `docs_searchDocumentation` / `docs_getPage`,
`api_get_test_blocks`, `api_get_test_block_version` and `api_run_adhoc_assertions` on whichever Miqa
MCP server is connected (tool names follow `mcp__<server-name>__<tool>`). It only reads and runs
ad-hoc assertions. It never calls `update_*`, `create_*` or `publish_*` tools unless the user asks
for that at the end.

## Direction

Default to **per-sample to aggregate**. Go the other way only when the user asks for it ("split this
aggregate table per sample", "go back to table_config", "make this per file"). If it is unclear, ask
once.

A table converts only when it fits the pattern. If it does not, leave it unchanged, say which table
it is and why, and move on to the next. Do not force a conversion or approximate it.

- **Per-sample to aggregate** fits when the per-sample `table_values` reads one file's `data` and
  nothing else.
- **Aggregate to per-sample** fits when the aggregate `table_values` is a plain rollup of a named
  stat: `data.<name>.explode()`, `.to_key_value_list()`, or `.map('value').flatten()`, optionally
  with `filter_custom`. The named stat is then the per-sample expression.
- **Neither direction fits** when the table needs more than one sample's data at once: a `Join` or
  `Match` across samples, values computed from other samples, a ratio against a cross-sample total,
  or anything that an `aggregate_check` depends on. Say that the table is cross-sample by nature.

## Procedure

1. **Get the assertions.** Use pasted JSON as it is. For a named Test Block, resolve it with
   `api_get_test_blocks(q=<name>)` (show id and name pairs if more than one matches; do not guess),
   then read the current version with `api_get_test_block_version`. If the JSON does not parse, say
   what is wrong before going on.

2. **Ground the vocabulary and the patterns.** Read `references/patterns.md` and `references/examples.md` in this skill's folder,
   and call `get_output_explorer_vocabulary()` once, at the same time. The reference holds the
   conversion table and the behavior that surprises people, so a docs search is not needed when
   every helper and key you need is in it. Search the docs ("aggregate expression-based stats
   across files") only for something the reference does not cover, such as an unfamiliar helper or
   check type. If a check type is not listed as supporting `named_aggregate_stats`, say so and leave
   that check alone.

3. **Find the checks to convert.** Going to aggregate, a check qualifies when it has `table_config`
   and no `aggregate_table_config`. Going back, it qualifies when it has `aggregate_table_config`.
   List the qualifying checks, with name and `check_type`, and skip the rest. If nothing qualifies,
   say that and stop. Going to aggregate, the check must end up with `named_aggregate_stats`, because
   `aggregate_table_config` is ignored without it.

4. **Convert each table, one check at a time.** The steps below go to aggregate; the paragraph after
   them covers going back. For every `table_config` entry:
   1. Name the per-sample value it reads: the expression in `table_values`, plus any
      `_precompute_multi_file` or `_variables` it depends on.
   2. Return that value from `named_aggregate_stats` under a short name. Reuse existing variables
      instead of repeating their logic.
   3. Pick the `aggregate_table_config` `table_values` that matches what the value is:

      Use the mapping table in `references/patterns.md`. In short: a summary object or a list of
      rows or a preview becomes `data.<name>.explode()`, a single value becomes
      `explode(value_field='<column>')`, and two or more stats side by side become a `Join(...,
      on='key')`.

   4. Copy `title`, `headers`, `column_config` and `max_row_count` across. Rename `key` to the sample
      column with `column_config` or `explode(key_field='<name>')`, because `explode()` puts the
      sample key there. Always set
      `downloadable: true` on the aggregate table.
   5. Remove the original per-sample `table_config` entry. The aggregate table replaces it, and one
      table per sample is the clutter this skill exists to get rid of. If the user wants to keep
      the per-sample detail, set `download_only: true` on that entry instead of deleting it. If a
      `table_config` is left in place for any other reason, say why in the report.

   **Going back (aggregate to per-sample):** for each `aggregate_table_config` entry that fits the
   pattern, take the expression behind the named stat it reads and make it the `table_values` of a
   `table_config` entry, reading `data` instead of `data.<name>`. Copy `title` (without "(all
   samples)"), `headers`, `column_config` (dropping the rename of `key`) and `max_row_count`. Remove
   the aggregate entry, and drop a `named_aggregate_stats` name once nothing reads it. Check
   that the result needs no sample key, since a per-sample table has none. Tell the user about any
   aggregate table that was kept because it did not fit.

   Do not change `stat`, `query`, `failtype` or anything else that decides pass or fail. If a
   conversion would need one of those changed, stop and ask.

5. **Prove it before reporting it.** Ask the user for an execution or a handful of samples to try it
   on, unless one is already in the conversation. Run the edited check with
   `api_run_adhoc_assertions`. Confirm that the converted table renders. For an aggregate table,
   check that its row count equals the sum of the per-sample tables it replaced. A sample with no
   rows adds none, so it will not appear: that is expected for a table of row lists, but name the
   samples that are missing, in case the user wants them shown. For a per-sample table, check that
   it shows the same rows the aggregate table showed for that sample. If an expression fails, fix it
   and rerun. Do not hand back an untried expression as if it worked. If no
   run is possible, say the conversion is untested.

6. **Report.** Give the edited JSON, then a short list: which checks were converted, which were
   left unchanged because they did not fit, and why, what was run, and what is still unconfirmed. Offer to save it as a new
   Test Block version, but do not do it unless the user says yes.

## Things to watch

- `to_key_value_list().map('value').flatten()` drops the sample key. Make sure each row carries an
  identifying column, or use `explode()` when the key matters.
- An aggregate table can be large. Keep `max_row_count` sensible and use `download_only` for the
  full list when a short one is shown.
- `named_aggregate_stats` is not supported by every check type. See the reference, and the docs if
  the check type is not covered there.
- Aggregate tables appear under the first dataset's results only. Tell the user where to look.
- Existing Test Blocks often keep the per-sample table as `download_only`. If the check already does
  that, leave it as it is.
