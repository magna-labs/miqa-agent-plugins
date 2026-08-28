---
name: assertion-translator
description: Translate a Python analysis script or natural-language request into MIQA Output Explorer assertions and a coverage report. Use when a user asks for MIQA assertions, Output Explorer checks, or a translation of analysis code or stated requirements into MIQA tests.
---

# Assertion Translator

Create an assertions blob and `coverage.md`. Show the coverage report to the user before offering
to publish anything.

## Domain

Every use of this skill is bioinformatics test engineering — the output data type varies (VCF, BAM,
FASTQ QC, coverage/metrics TSVs, JSON annotation calls, pipeline logs), but the reviewer's question is
always some form of "did this pipeline rerun still produce correct, consistent output." Default to the
conventions a bioinformatics test engineer would reach for: natural genomic match keys (e.g.
`CHROM`/`POS`/`REF`/`ALT` for variant-shaped data, sample/read IDs elsewhere), QUAL/FILTER/coverage/
depth-aware tolerances instead of blanket equality, precision/recall/F1 framing for call-set
comparisons where the check family actually applies (see the vocab-blurb gating rule below), and log/
error-pattern scanning for pipeline health. Evidence — execution files, columns, explicit request
wording — always overrides these defaults; the domain lens shapes translation choices, not the
columns or values themselves.

## Workflow

1. Require a Python analysis script or a natural-language request. Accept an optional
   column-mapping JSON, execution id, and sample input files.
2. Resolve the MIQA guidance from `$MIQA_DOCS_BASE_URL/<path>`, using
   `references/doc-paths.md`. If `MIQA_DOCS_BASE_URL` is not set, ask the user to set it and stop
   without writing a blob. Never translate the DSL from memory.
3. Call `get_output_explorer_vocabulary()` once and save its payload. Use it for the schema, enum
   values, starter blurbs, and global variable names. If the tool or a vocabulary section is
   unavailable, continue where possible and record the validation that cannot run. Never hardcode
   a documentation URL, share token, or global variable.
4. Read `references/patterns.md`. Before writing `_variables`, `_extends`, `_precompute`, `$name`,
   or `{{ name }}`, also read `references/variables-and-precompute.md`.
5. Normalize the source into reviewer questions, collect evidence, translate every question, and
   write both output files.
6. Validate the blob, show `coverage.md`, and wait for explicit approval before publishing.

## Interpret the source

For each check, identify the reviewer question, data scope, comparison mode, match keys,
computation, output form, explicit outcome, source evidence, and unconfirmed facts. Use this as a
working checklist, not as another artifact or schema.

With a Python script, derive the intent and source lines from its behavior. Keep the result
report-only: never write `relationship`, `static`, `threshold`, or `threshold_type`. If a reviewer
might gate on a stat, name it as a threshold candidate in the coverage report.

With a natural-language request, treat the user's statements as semantic evidence. Ask only when a
missing choice changes the check's meaning and execution or samples cannot resolve it. Examples
include an unclear comparison direction, match key, meaning of “match,” or pass condition. Do not
ask for facts that the available evidence can establish. Do not add a separate confirmation step
when the request is complete.

Treat requests to compare, show, report, or plot as report-only unless they state an outcome. Treat
conditions such as “no records are missing,” “values must be equal,” or “fail above 2%” as explicit
outcomes. Translate an explicit outcome with the live vocabulary and schema. Never invent a
column, match key, mapping, baseline direction, or threshold.

## Evidence rules

Use the strongest available source for each fact:

| Fact | Preferred source | Fallback | Without evidence |
| --- | --- | --- | --- |
| File keys and pattern | Execution | Observed or source-named basenames | Derive from the source and mark unconfirmed |
| Columns, delimiter, cast | Execution | Sample files | Mark columns unconfirmed, omit delimiter, and write a cast stub |
| Value mappings | Explicit supplied mapping | Sample files | Write a `map_values` stub and mark value encoding unconfirmed |
| Column rename | Mapping JSON or explicit request | None | Do not invent one |

For an execution, call `inspect_execution_outputs`. Use its file keys, delimiter, cast, and columns.
It reads partial content for at most 20 files and returns no values. Name excluded files in the
coverage report. Use sample files only for facts the execution cannot provide, such as value-level
encoding.

Treat file and column names in a natural-language request as intended names, not proof that they
exist in the data. Confirm them from execution or samples when available, otherwise mark them
unconfirmed.

Write a column mapping as one `rename` transform. Use renamed target columns in every `stat`,
`query`, and `chart_values` expression. Keep the original names only in the rename transform.

Derive `file_rules.pattern` from execution file keys when available. Name the matched files and
mark the pattern confirmed. Reject a pattern that matches no execution file. Without an execution,
derive the pattern from observed or source-named basenames, and mark it unconfirmed. Do not infer
MIQA path nesting from sample files.

Treat the vocabulary's starter blurbs (`get_output_explorer_vocabulary`'s `blurbs`) as a signal for
which check-type families are actually usable in this deployment, not just naming ideas. Result-based
types (`accuracy`, `concordance`, `overlap_count`, `result_field_check`) need Parsed Results
configured on the pipeline, and `postproc_*` types need a built-in postprocessor — both are
deployment-side facts this skill cannot otherwise check. If no blurb hints at either family, do not
research or use it, even when the request's own wording says "concordance," "accuracy," or similar —
treat that wording as intent and translate it onto the closest raw-file/tabular equivalent instead
(e.g. `paired_tabular_mdo_eval`/`tabular_mdo_eval`), noting the substitution in `coverage.md`.

## Translation rules

Create one check per question that a reviewer asks about the outputs. Combine helper functions,
loops, and column operations when they answer one question.

Apply these MIQA rules even when the source has a different structure:

- Translate a comparison of two files into one `file_rules.pattern` that matches both files, with
  `"versions": [-1]`. Compare `data_baseline` with `data_test`.
- Translate a sequence comparison with a DSL comparator, such as
  `compare_by('<field>', 'alignment_ratio')`. Do not drop it.
- Translate a plot into `chart_config` with the live vocabulary's matching `chart_type`. Do not
  drop it.

For `compare_by`, `compare_fields`, or `compare_all_fields`, make `stat` Boolean. End the
comparison with `.summary().is_match_within_threshold`; do not return the comparison object,
`.results()`, or `.summary()` from `stat`. If detail, table, or chart expressions reuse the full
comparison, bind it once in `_precompute` and keep the Boolean expression in `stat`.

For a natural-language request, write outcome fields only when the request states a pass or fail
condition. Preserve its meaning without making the condition stricter or weaker. When no condition
is stated, write the computed result only.

## Coverage report

Before marking a behavior `dropped`, check the analyzer and chart paths in
`references/doc-paths.md` and the mappings in `references/patterns.md`.

Use exactly this compact format:

```markdown
# Coverage

**Status:** `READY|NOT READY`

| Source | Output Explorer check | Status | Note |
| --- | --- | --- | --- |
| `<script line or request statement>` | `<reviewer question or check name>` | `translated|approximated|dropped` | `<material limit, or blank>` |

## Notes

- Evidence: files `<confirmed|unconfirmed>`; columns `<confirmed|unconfirmed>`; excluded `<files>`
- Gate: `<explicit condition|report-only>`; candidates `<stats>`
- Assumptions: `<stubs, unchecked mappings, or semantic assumptions>`
- Validation: `<PASS|SKIPPED: reason>`
```

Write one table row per source behavior or requested question. Use `READY` only when validation has
no `FAIL`, no semantic choice blocks translation, and any supplied execution confirms a matching
pattern. Use one line per note. Omit absent note parts and whole note lines instead of writing
`none`. Never add an introduction, conclusion, rationale section, or repeated explanation. Do not
omit a source behavior, material limit, threshold candidate, assumption, excluded file, or
`SKIPPED` result.

## Validation

Run via `uvx`, resolving `miqatools` transitively through the exact `miqa-mcp` version this plugin
already pins in `../../.mcp.json` (its `args` entry `miqa-mcp@<version>`) — this guarantees a
`miqatools` build with the `outputexplorer` module, matching what the running server itself uses,
without any local `pip install` and with no separate version to keep in sync by hand. Read that
version from `.mcp.json` at run time, then:

```
uvx --prerelease=allow --from 'miqa-mcp==<version from .mcp.json>' python -m miqatools.outputexplorer.validation BLOB.json --vocab VOCAB.json
```

If `uvx` is unavailable, fall back to a local `python -m miqatools.outputexplorer.validation` and
record `SKIPPED: <reason>` in the coverage report if neither path runs.

Require valid JSON, draft-07 schema conformance, live enum values, valid Jinja syntax, and references
that resolve against local variables or vocabulary global variables. The command does not validate
columns or semantic fidelity.

Fix every `FAIL` before calling the blob ready. Copy every `SKIPPED` finding into the coverage
report. Record column confirmation separately.

## Publish gate

Always write the blob and `coverage.md` after translation, even when the blob is not ready. Show
the coverage report before offering to publish.

Preview first:

```
publish_adhoc_assertions(assertions, name, description, execution_id=None, apply=False)
```

Use the script filename or a concise request-derived name. Include the source, date, and coverage
report in the description. Publish with `apply=True` only after explicit user approval. If the tool
is unavailable, tell the user to paste the blob into Output Explorer's JSON tab.

Never create or change a Test Block, Test Chain, or any MIQA resource other than this saved ad-hoc
record.

## References

- `references/patterns.md`: structural rules, granularity rules, and worked examples
- `references/variables-and-precompute.md`: variable, extension, and precompute resolution
- `references/doc-paths.md`: paths for targeted MIQA guidance
